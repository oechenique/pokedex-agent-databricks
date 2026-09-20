"""Coordinador multi-agente 'Profesor Oak' (Fase 6, reglas/03-agente-mcp.md
-- "Escalado a multi-agente"). Delegación goal-oriented (objetivo + criterio
de calidad, nunca una receta paso a paso) a los 3 subagentes aislados de
subagents.py. El contexto entre subagentes pasa EXPLÍCITO por este
coordinador -- nunca un subagente llama a otro, nunca memoria compartida
automática.

Dos llamadas propias a la Messages API: una (forzada con tool_choice sobre
"delegate_plan") para decidir a quién delegar qué, otra para sintetizar la
respuesta final del Profesor Oak a partir de los resultados reales del
equipo -- nunca agrega un dato que el equipo no haya traído.
"""

import json
from dataclasses import dataclass, field

import anthropic

import config
import system_prompt
from subagents import SubagentResult, run_subagent

PLAN_MAX_TOKENS = 1024
SYNTHESIS_MAX_TOKENS = 1536

COORDINATOR_IDENTITY = (
    "Sos el Profesor Oak coordinando un equipo de especialistas: Pokemon "
    "Researcher (stats/tipos), Battle Analyst (matchups/comparaciones) y "
    "Data Librarian (lore). No investigás vos mismo -- decidís a quién del "
    "equipo delegarle cada parte del pedido, con un objetivo claro y un "
    "criterio de calidad para cada uno. No repitas subagentes que no hagan "
    "falta para lo que pidió el usuario."
)

DELEGATE_PLAN_TOOL = {
    "name": "delegate_plan",
    "description": "Arma el plan de delegación a los subagentes del equipo, en el orden en que deben correr.",
    "input_schema": {
        "type": "object",
        "properties": {
            "delegations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "subagent": {
                            "type": "string",
                            "enum": ["pokemon_researcher", "battle_analyst", "data_librarian"],
                        },
                        "goal": {
                            "type": "string",
                            "description": "Objetivo en lenguaje natural para este subagente -- nunca una receta paso a paso ni un nombre de tool.",
                        },
                        "quality_criteria": {
                            "type": "string",
                            "description": "Qué hace aceptable el resultado de este subagente.",
                        },
                    },
                    "required": ["subagent", "goal", "quality_criteria"],
                },
            }
        },
        "required": ["delegations"],
    },
}

# Heurística de auto-detección (mismo criterio que tool_choice.py: keywords,
# no NLU real) -- dispara modo multi-agente si el pedido pide un análisis
# multi-faceta, no una pregunta puntual que ya resuelve el agente single.
_MULTI_AGENT_KEYWORDS = (
    "análisis completo",
    "analisis completo",
    "informe completo",
    "todo sobre",
)


def should_use_multi_agent(user_message: str) -> bool:
    lowered = user_message.lower()
    return any(kw in lowered for kw in _MULTI_AGENT_KEYWORDS)


@dataclass
class MultiAgentResult:
    reply: str
    render: dict
    trace: list[SubagentResult] = field(default_factory=list)


def _plan_delegation(client: anthropic.Anthropic, model: str, user_message: str) -> list[dict]:
    response = client.messages.create(
        model=model,
        max_tokens=PLAN_MAX_TOKENS,
        system=COORDINATOR_IDENTITY,
        tools=[DELEGATE_PLAN_TOOL],
        tool_choice={"type": "tool", "name": "delegate_plan"},
        messages=[{"role": "user", "content": user_message}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "delegate_plan":
            return block.input.get("delegations", [])
    return []


def _context_block(trace: list[SubagentResult]) -> str:
    if not trace:
        return ""
    return "\n".join(f"- {r.role}: {r.summary}" for r in trace)


async def run_multi_agent(user_message: str, mcp, all_tools: list[dict]) -> MultiAgentResult:
    client = anthropic.Anthropic()
    model = config.ANTHROPIC_MODEL

    delegations = _plan_delegation(client, model, user_message)

    trace: list[SubagentResult] = []
    for d in delegations:
        subagent = d.get("subagent")
        if subagent not in ("pokemon_researcher", "battle_analyst", "data_librarian"):
            continue
        # Contexto EXPLÍCITO del coordinador: lo que ya trajeron los
        # subagentes anteriores, nunca un subagente llamando a otro.
        context = _context_block(trace)
        result = await run_subagent(
            role=subagent,
            goal=d["goal"],
            quality_criteria=d["quality_criteria"],
            context_from_others=context or None,
            mcp=mcp,
            all_tools=all_tools,
            client=client,
            model=model,
        )
        trace.append(result)

    if not trace:
        return MultiAgentResult(
            reply="No pude armar un plan de equipo para esa pregunta -- probá reformularla.",
            render={"kind": "text"},
        )

    findings = "\n\n".join(
        f"### {r.role}\n"
        f"Objetivo: {r.goal}\n"
        f"Resultado: {r.summary}\n"
        f"Datos crudos: {json.dumps(r.structured_data, ensure_ascii=False)}"
        for r in trace
    )
    synthesis_prompt = (
        f"Pregunta original del usuario: {user_message}\n\n"
        f"Resultados de tu equipo (Pokemon Researcher / Battle Analyst / Data Librarian):\n{findings}\n\n"
        "Redactá la respuesta final para el usuario en tu propia voz. Citá los "
        "datos reales que trajo el equipo -- nunca agregues un dato que no "
        "esté en los resultados de arriba, y si algún subagente no pudo "
        "conseguir su parte, decilo explícito."
    )
    final = client.messages.create(
        model=model,
        max_tokens=SYNTHESIS_MAX_TOKENS,
        system=system_prompt.build_system_blocks(),
        messages=[{"role": "user", "content": synthesis_prompt}],
    )
    reply = "\n".join(b.text for b in final.content if b.type == "text")

    render: dict = {"kind": "text"}
    for r in trace:
        if r.role == "pokemon_researcher" and r.structured_data.get("pokemon"):
            render = {"kind": "pokemon", "pokemon": r.structured_data["pokemon"]}
            break

    return MultiAgentResult(reply=reply, render=render, trace=trace)
