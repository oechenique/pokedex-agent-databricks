"""Dominio: tool_choice (reglas/03-agente-mcp.md, reglas/06-ccaf-mapa-y-
convenciones.md). Prueba la heurística real de agent/tool_choice.py --
la misma que decide el tool_choice de cada turno en producción -- y
confirma en vivo, contra el agente + pokedex-mcp-server reales, que el
forzado explícito realmente hace que Claude llame la tool correcta.
"""

import asyncio

import tool_choice
from agent import Agent
from mcp_client import PokedexMCPClient


def test_pedido_explicito_de_comparar_fuerza_compare_pokemon():
    choice = tool_choice.choose_tool_choice("Comparame a Charizard contra Blastoise")
    assert choice == {"type": "tool", "name": "compare_pokemon"}


def test_vs_tambien_fuerza_compare_pokemon():
    choice = tool_choice.choose_tool_choice("Charizard vs Blastoise, quién gana")
    assert choice == {"type": "tool", "name": "compare_pokemon"}


def test_pregunta_factual_ambigua_usa_any():
    """Ambigua porque podría resolverse con get_pokemon_stats o
    search_pokemon -- "any" obliga a usar ALGUNA tool, nunca prosa
    inventada, sin forzar cuál (reglas/03)."""
    choice = tool_choice.choose_tool_choice("Decime los stats de Pikachu")
    assert choice == {"type": "any"}


def test_charla_de_personalidad_usa_auto():
    choice = tool_choice.choose_tool_choice("¿Por qué te gustan tanto los pokemon, profesor?")
    assert choice == {"type": "auto"}


def test_forzado_compare_pokemon_en_vivo():
    """Confirma en vivo (agente real + pokedex-mcp-server real) que el
    forzado de tool_choice.py realmente se traduce en que Claude llame
    compare_pokemon en la primera ronda -- no solo que la heurística
    devuelva el dict correcto."""

    async def _run() -> list[str]:
        async with PokedexMCPClient() as mcp:
            agent = Agent(mcp)
            await agent.load_tools()
            await agent.send("Comparame a Charizard contra Blastoise")
        first_assistant = next(m for m in agent.messages if m["role"] == "assistant")
        return [b.name for b in first_assistant["content"] if getattr(b, "type", None) == "tool_use"]

    tool_names = asyncio.run(_run())
    assert "compare_pokemon" in tool_names
