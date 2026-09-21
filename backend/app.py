"""Backend FastAPI del Profesor Oak, corriendo como proceso Python dentro
de la Databricks App híbrida `pokedex-backend` (reglas/04-frontend.md,
reglas/07-estado-actual.md).

Reusa agent/agent.py, hooks.py, tool_choice.py, mcp_client.py, config.py y
system_prompt.py TAL CUAL -- no se reescribe nada de Fase 4 acá. Lo único
que hace este archivo es: (1) agregar agent/ al sys.path para poder
importarlos con sus imports planos (mismo patrón que agent/cli.py), (2)
exponerlos como un endpoint HTTP stateless (el front manda el historial
completo en cada request, como corresponde a la Messages API), y (3) rate
limiting antes de pegarle al agente.

Auth contra pokedex-mcp-server: `mcp_client.py` no necesita
`DATABRICKS_PROFILE` ni `DATABRICKS_CLIENT_ID`/`SECRET` en producción --
usa el service principal propio de esta app, inyectado automáticamente
por la plataforma (mismo patrón de auth app-to-app ya validado en
`oak_app/`). Local sigue resolviendo con el perfil de
`databricks auth login` (`DATABRICKS_PROFILE`).

Arquitectura híbrida Node.js + Python (reglas/07-estado-actual.md,
"Migración Next.js a Databricks App"): esta app corre en el MISMO proceso
Databricks App que `frontend/` (Next.js), lanzados en paralelo por
`concurrently` desde el `package.json` de la raíz del repo (ver `app.yaml`
también en la raíz). Next.js recibe el tráfico público en
`DATABRICKS_APP_PORT`; este server FastAPI escucha en loopback puro
(`127.0.0.1:8001`, ver `__main__` abajo) y nunca es alcanzable desde
afuera -- Next.js le proxea `/api/*` server-side vía `rewrites()` en
`frontend/next.config.ts`. Por eso no hace falta CORS: el browser solo le
habla a Next.js, nunca directo a este proceso.
"""

import sys
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
sys.path.insert(0, str(AGENT_DIR))

from agent import Agent  # noqa: E402
from mcp_client import PokedexMCPClient  # noqa: E402
from orchestrator import run_multi_agent, should_use_multi_agent  # noqa: E402

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from .rate_limit import check_rate_limit  # noqa: E402
from .render import build_render  # noqa: E402
from .serialize import serialize_messages  # noqa: E402

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    # Toggle del front (Fase 6, orchestrator.py) -- se OR-ea con la
    # heurística de should_use_multi_agent, mismo criterio que oak_app: el
    # toggle fuerza el modo, pero una pregunta de análisis completo lo activa
    # sola aunque el toggle esté apagado.
    multi_agent: bool = False


class ChatResponse(BaseModel):
    reply: str
    history: list[dict]
    # Formato por tipo de dato (reglas/04-frontend.md) -- {"kind": "text"} |
    # {"kind": "pokemon", "pokemon": {...}} | {"kind": "compare", "compare": {...}}
    # | {"kind": "matchups", "matchups": {...}}. Derivado de los tool_result
    # reales de este turno, ver render.py -- nunca inventado.
    render: dict
    # Traza del equipo (coordinador + subagentes) cuando el turno corrió en
    # modo multi-agente -- [] en modo single. Un dict por SubagentResult
    # (role/goal/quality_criteria/summary/structured_data/tool_calls), mismo
    # contenido que el expander "Cómo trabajó el equipo" de oak_app.
    trace: list[dict] = []


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    # Con Next.js proxeando server-side (ver docstring del módulo), esta IP
    # es siempre 127.0.0.1 -- el rate limit queda compartido entre todos los
    # usuarios reales, no por-usuario. Suficiente para el placeholder actual
    # (reglas/04-frontend.md); si esto se vuelve un problema real, la key
    # tiene que salir de un header propio (ej. cookie de sesión), no de la IP.
    client_key = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_key):
        raise HTTPException(status_code=429, detail="Demasiadas consultas -- esperá un minuto.")

    history_len = len(body.history)
    multi_agent = body.multi_agent or should_use_multi_agent(body.message)

    async with PokedexMCPClient() as mcp:
        agent = Agent(mcp)
        await agent.load_tools()

        if multi_agent:
            # Coordinador + subagentes (orchestrator.py) -- mismo patrón que
            # oak_app: el historial de la charla sigue el formato de agent.
            # Agent (para que un turno normal después pueda continuarla),
            # pero sin el detalle interno de cada subagente -- eso nunca fue
            # parte de la conversación con el usuario, solo del panel de
            # trazabilidad.
            result = await run_multi_agent(body.message, mcp, agent.tools)
            full_history = list(body.history) + [
                {"role": "user", "content": body.message},
                {"role": "assistant", "content": [{"type": "text", "text": result.reply}]},
            ]
            trace = [
                {
                    "role": r.role,
                    "goal": r.goal,
                    "quality_criteria": r.quality_criteria,
                    "summary": r.summary,
                    "structured_data": r.structured_data,
                    "tool_calls": r.tool_calls,
                }
                for r in result.trace
            ]
            return ChatResponse(reply=result.reply, history=full_history, render=result.render, trace=trace)

        agent.messages = body.history
        reply = await agent.send(body.message)

    full_history = serialize_messages(agent.messages)
    render = build_render(full_history[history_len:])

    return ChatResponse(reply=reply, history=full_history, render=render, trace=[])


if __name__ == "__main__":
    # `python -m backend.app` (no `python backend/app.py`) para que los
    # imports relativos (.rate_limit, .render, .serialize) resuelvan --
    # corrido como script perdería el paquete `backend`.
    #
    # host=127.0.0.1 a propósito, NO 0.0.0.0: DATABRICKS_APP_PORT (el único
    # puerto público de la Databricks App) lo toma Next.js, corriendo en
    # paralelo (ver package.json/app.yaml de la raíz). Este proceso escucha
    # en un puerto fijo de loopback puro -- nunca alcanzable desde afuera del
    # contenedor -- y Next.js le proxea /api/* server-side (rewrites() en
    # frontend/next.config.ts). 8001, no 8000 -- DATABRICKS_APP_PORT resultó
    # ser 8000 en este workspace (hallazgo real en vivo: los dos procesos
    # intentaron bindear el mismo puerto y el backend murió con "address
    # already in use"). Mismo puerto fijo hardcodeado en los dos lados a
    # propósito, no hace falta una env var para esto.
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
