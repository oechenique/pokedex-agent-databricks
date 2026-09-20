"""Subagentes del coordinador Profesor Oak (Fase 6, reglas/03-agente-mcp.md
-- "Escalado a multi-agente"). Cada subagente es su propia llamada aislada a
la Messages API: mensajes propios, system prompt propio, subset de tools
propio. Nunca comparten memoria ni se llaman entre sí -- el contexto entre
subagentes pasa EXPLÍCITO por el coordinador (orchestrator.py), nunca
subagente-a-subagente. Es justo el patrón que más se pregunta mal en el
Dominio 1 del examen CCA-F.

Mismos hooks reales que el agente single (hooks.py) -- el aislamiento no es
solo "otro system prompt", cada subagente pasa por el mismo PreToolUse/
PostToolUse que ya bloquea nombres inválidos y marca isError explícito.
"""

import json
from dataclasses import dataclass, field
from typing import Optional

import anthropic

import hooks

MAX_TOKENS = 2048

# Cada subagente ve SOLO estas tools -- aislamiento real, no de nombre.
SUBAGENT_TOOLS = {
    "pokemon_researcher": {"get_pokemon_stats", "search_pokemon"},
    "battle_analyst": {"compare_pokemon", "get_type_matchups"},
    # única fuente de lore hoy es get_pokemon_stats -- get_card_info (TCG)
    # no existe todavía en mcp_server (reglas/07: pokemontcg.io pendiente).
    "data_librarian": {"get_pokemon_stats"},
}

SUBAGENT_IDENTITY = {
    "pokemon_researcher": (
        "Sos Pokemon Researcher, especialista en fichas técnicas del equipo "
        "del Profesor Oak. Tu único trabajo es conseguir datos crudos y "
        "reales de stats/tipos/generación desde gold.* -- nunca calculás "
        "matchups ni redactás lore, eso es trabajo de otro especialista del "
        "equipo."
    ),
    "battle_analyst": (
        "Sos Battle Analyst, especialista en combate del equipo del "
        "Profesor Oak. Tu trabajo es consultar efectividad de tipos y "
        "comparaciones de stats -- nunca inventás un matchup, siempre lo "
        "consultás con la tool real."
    ),
    "data_librarian": (
        "Sos Data Librarian, especialista en lore (y a futuro cartas TCG) "
        "del equipo del Profesor Oak. Tu trabajo es redactar el lore/"
        "historia real de un pokemon a partir de datos ya provistos o "
        "consultados -- nunca inventás lore que no esté en la fuente."
    ),
}

SUBAGENT_RULES = """\
Reglas -- no se negocian con tu especialidad de arriba:
1. Nunca inventes un dato que no venga de una tool real o del contexto que
   te pasó el coordinador.
2. Investigá SOLO el/los pokemon nombrados explícitamente en tu objetivo --
   nunca explores formas evolutivas, mega-evoluciones, Gigamax ni especies
   relacionadas salvo que el objetivo las pida por nombre. Un objetivo sobre
   "Charizard" es sobre Charizard, no sobre Charmander/Charmeleon/Mega
   Charizard X o Y.
3. Si una tool falla o el dato no existe, decilo explícito en tu resultado
   -- no lo rellenes ni lo completes.
4. Tu resultado es un insumo para el coordinador, no una respuesta directa
   al usuario final -- sé conciso y concreto, sin saludos ni cierre de
   charla."""


@dataclass
class SubagentResult:
    role: str
    goal: str
    quality_criteria: str
    summary: str  # síntesis en prosa del subagente, para el coordinador
    structured_data: dict = field(default_factory=dict)  # último tool_result JSON real, crudo
    tool_calls: list[str] = field(default_factory=list)  # nombres de tools usadas, para trazabilidad


async def run_subagent(
    role: str,
    goal: str,
    quality_criteria: str,
    context_from_others: Optional[str],
    mcp,
    all_tools: list[dict],
    client: anthropic.Anthropic,
    model: str,
) -> SubagentResult:
    allowed_names = SUBAGENT_TOOLS[role]
    tools = [t for t in all_tools if t["name"] in allowed_names]

    system = [
        {"type": "text", "text": SUBAGENT_IDENTITY[role]},
        {"type": "text", "text": SUBAGENT_RULES},
    ]

    task = f"Objetivo: {goal}\nCriterio de calidad: {quality_criteria}"
    if context_from_others:
        task += (
            "\n\nContexto ya recolectado por el resto del equipo (usalo, no "
            f"lo vuelvas a pedir si ya alcanza):\n{context_from_others}"
        )

    messages: list[dict] = [{"role": "user", "content": task}]
    tool_calls: list[str] = []
    structured_data: dict = {}

    response = client.messages.create(
        model=model, max_tokens=MAX_TOKENS, system=system, tools=tools, messages=messages
    )

    while response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            tool_calls.append(block.name)

            ctx = hooks.HookContext(call_tool=mcp.call_tool)
            try:
                await hooks.pre_tool_use(block.name, block.input, ctx)
            except hooks.ToolBlocked as exc:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"[PreToolUse bloqueó la llamada] {exc}",
                        "is_error": True,
                    }
                )
                continue

            result = await mcp.call_tool(block.name, block.input)
            outcome = hooks.post_tool_use(block.name, result)
            if not outcome["ok"]:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"[PostToolUse: isError=true, no es un dato válido] {outcome['error']}",
                        "is_error": True,
                    }
                )
                continue

            # Primer resultado, no el último -- un subagente puede hacer
            # varias llamadas exploratorias (bug real visto en pruebas:
            # Pokemon Researcher exploraba formas evolutivas y el ÚLTIMO
            # tool_result, de un pokemon distinto al pedido, pisaba el
            # primero). El primer resultado es el que responde directo al
            # objetivo; lo de después es contexto adicional del subagente.
            if not structured_data:
                structured_data = outcome["data"]
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(outcome["data"], ensure_ascii=False),
                }
            )

        messages.append({"role": "user", "content": tool_results})
        response = client.messages.create(
            model=model, max_tokens=MAX_TOKENS, system=system, tools=tools, messages=messages
        )

    summary = "\n".join(b.text for b in response.content if b.type == "text")
    return SubagentResult(
        role=role,
        goal=goal,
        quality_criteria=quality_criteria,
        summary=summary,
        structured_data=structured_data,
        tool_calls=tool_calls,
    )
