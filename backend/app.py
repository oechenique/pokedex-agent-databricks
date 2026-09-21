"""Backend serverless del Profesor Oak en Vercel (reglas/04-frontend.md,
reglas/07-estado-actual.md Fase 5).

Reusa agent/agent.py, hooks.py, tool_choice.py, mcp_client.py, config.py y
system_prompt.py TAL CUAL -- no se reescribe nada de Fase 4 acá. Lo único
que hace este archivo es: (1) agregar agent/ al sys.path para poder
importarlos con sus imports planos (mismo patrón que agent/cli.py), (2)
exponerlos como un endpoint HTTP stateless (el front manda el historial
completo en cada request, como corresponde a la Messages API), y (3) rate
limiting antes de pegarle al agente.

Auth contra pokedex-mcp-server: mcp_client.py arma el `Config(profile=...,
host=...)` con las mismas variables de siempre -- localmente resuelve con
el perfil de `databricks auth login` (DATABRICKS_PROFILE). En Vercel no hay
sesión interactiva posible, así que ahí DATABRICKS_PROFILE queda sin setear
y hace falta DATABRICKS_CLIENT_ID/DATABRICKS_CLIENT_SECRET (service
principal M2M) como env vars -- el `Config` de databricks-sdk los detecta
solo, sin tocar una línea de mcp_client.py. Ese service principal todavía
no existe (ver reglas/07-estado-actual.md); hace falta antes del deploy
real a Vercel.

Segundo intento de frontend real (reglas/07-estado-actual.md): este
mismo archivo, sin cambios de lógica, corre TAMBIÉN como Databricks App
(bloque `if __name__ == "__main__":` al final, aditivo -- Vercel sigue
importando `app` vía ASGI y nunca lo ejecuta). Corriendo como Databricks
App, `mcp_client.py` no necesita `DATABRICKS_PROFILE` ni
`DATABRICKS_CLIENT_ID`/`SECRET` -- usa el service principal propio de
ESTA app, inyectado automáticamente por la plataforma, mismo patrón de
auth app-to-app ya validado en `oak_app/`.
"""

import os
import sys
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
sys.path.insert(0, str(AGENT_DIR))

from agent import Agent  # noqa: E402
from mcp_client import PokedexMCPClient  # noqa: E402

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from .rate_limit import check_rate_limit  # noqa: E402
from .render import build_render  # noqa: E402
from .serialize import serialize_messages  # noqa: E402

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    history: list[dict]
    # Formato por tipo de dato (reglas/04-frontend.md) -- {"kind": "text"} |
    # {"kind": "pokemon", "pokemon": {...}} | {"kind": "compare", "compare": {...}}
    # | {"kind": "matchups", "matchups": {...}}. Derivado de los tool_result
    # reales de este turno, ver render.py -- nunca inventado.
    render: dict


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    client_key = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_key):
        raise HTTPException(status_code=429, detail="Demasiadas consultas -- esperá un minuto.")

    history_len = len(body.history)

    async with PokedexMCPClient() as mcp:
        agent = Agent(mcp)
        await agent.load_tools()
        agent.messages = body.history
        reply = await agent.send(body.message)

    full_history = serialize_messages(agent.messages)
    render = build_render(full_history[history_len:])

    return ChatResponse(reply=reply, history=full_history, render=render)


if __name__ == "__main__":
    # Databricks App (reglas/07-estado-actual.md -- segundo intento de
    # frontend real, esqueleto de validación): Vercel importa `app`
    # directo vía el entrypoint ASGI y nunca corre este bloque, así que
    # esto es aditivo, no rompe nada del deploy actual. `python -m
    # backend.app` (no `python backend/app.py`) para que los imports
    # relativos (.rate_limit, .render, .serialize) resuelvan -- corrido
    # como script perdería el paquete `backend`. DATABRICKS_APP_PORT lo
    # inyecta la plataforma, mismo patrón que mcp_server/app.py.
    import uvicorn

    port = int(os.environ.get("DATABRICKS_APP_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
