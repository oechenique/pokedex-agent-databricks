"""Dominio: subagents (reglas/03-agente-mcp.md "Escalado a multi-agente",
reglas/06 -- "lo que más se pregunta mal en el examen, Dominio 1").
Corre el coordinador y los subagentes reales (agent/orchestrator.py,
agent/subagents.py) contra el agente + pokedex-mcp-server ya
desplegados.

Tres garantías puntuales:
1. El contexto entre subagentes pasa EXPLÍCITO por el coordinador (nunca
   un subagente llama a otro, nunca memoria compartida automática).
2. Estructuralmente, ningún subagente tiene una tool para invocar a otro
   subagente ni al coordinador.
3. Regresión del bug real encontrado en 2026-09-20: Pokemon Researcher
   no debe irse de scope a Mega Evoluciones/Gigamax no pedidas.
"""

import asyncio

import anthropic

import config
import subagents
from agent import Agent
from mcp_client import PokedexMCPClient
from orchestrator import run_multi_agent


def test_ningun_subagente_tiene_una_tool_para_llamar_a_otro():
    """Chequeo estructural, no de prosa: el subset de tools de cada
    subagente sale de subagents.SUBAGENT_TOOLS -- si algún día alguien
    agrega una tool tipo "delegate"/"call_subagent" ahí, este test lo
    detecta. Hoy, ninguno de los 3 subsets menciona a otro subagente."""
    for role, tool_names in subagents.SUBAGENT_TOOLS.items():
        for name in tool_names:
            assert "subagent" not in name.lower()
            assert "delegate" not in name.lower()
            assert "coordina" not in name.lower()


def test_contexto_pasa_explicito_del_coordinador_no_entre_subagentes():
    """Corre el equipo completo para un pedido real de análisis
    multi-faceta y confirma que Battle Analyst recibió, tal cual armado
    por el coordinador, un bloque que cita a Pokemon Researcher -- el
    ÚNICO canal por el que le pudo haber llegado esa info es
    orchestrator._context_block(), nunca una llamada directa entre
    subagentes (subagents.run_subagent no recibe ninguna referencia a
    otro subagente, solo un string de contexto)."""

    async def _run():
        async with PokedexMCPClient() as mcp:
            agent = Agent(mcp)
            await agent.load_tools()
            return await run_multi_agent(
                "Hacé un análisis completo de Charizard: stats, matchups y lore",
                mcp,
                agent.tools,
            )

    result = asyncio.run(_run())

    assert len(result.trace) >= 2
    roles_en_orden = [r.role for r in result.trace]
    assert roles_en_orden[0] == "pokemon_researcher"  # primero, sin contexto previo

    first = result.trace[0]
    assert first.context_received is None  # nada corrió antes, no hay nada que pasarle

    later_with_context = [r for r in result.trace[1:] if r.context_received]
    assert later_with_context, "ningún subagente posterior recibió contexto del coordinador"
    for r in later_with_context:
        # El contexto que recibió es exactamente el que arma
        # orchestrator._context_block(): "- <role>: <summary>" de los
        # subagentes que ya corrieron -- tiene que citarlos por nombre.
        assert any(prev.role in r.context_received for prev in result.trace[: roles_en_orden.index(r.role)])


def test_researcher_no_se_va_de_scope_a_mega_evoluciones():
    """Regresión del bug real de 2026-09-20: con un objetivo acotado a
    "Charizard", el PRIMER resultado estructurado tiene que ser de
    charizard -- no de una mega-evolución ni de una especie relacionada
    que el subagente haya explorado por su cuenta."""

    async def _run():
        async with PokedexMCPClient() as mcp:
            agent = Agent(mcp)
            await agent.load_tools()
            client = anthropic.Anthropic()
            return await subagents.run_subagent(
                role="pokemon_researcher",
                goal="Conseguí el perfil técnico de Charizard: tipos, stats base y generación.",
                quality_criteria="Datos reales de Gold, exactos, sin inventar nada.",
                context_from_others=None,
                mcp=mcp,
                all_tools=agent.tools,
                client=client,
                model=config.ANTHROPIC_MODEL,
            )

    result = asyncio.run(_run())
    pokemon = result.structured_data.get("pokemon")
    assert pokemon is not None
    assert pokemon["name"] == "charizard"
