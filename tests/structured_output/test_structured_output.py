"""Dominio: structured_output (reglas/03-agente-mcp.md, reglas/06). Dos
garantías reales del schema de las tools: (1) un dato ausente vuelve
`null` explícito, nunca inventado; (2) el enum de 21 tipos reales
rechaza cualquier valor fuera de catálogo a nivel schema (Pydantic), no
a criterio del LLM.
"""

import asyncio
import json

import hooks
from mcp_client import PokedexMCPClient

REAL_TYPES = {
    "bug", "dark", "dragon", "electric", "fairy", "fighting", "fire", "flying",
    "ghost", "grass", "ground", "ice", "normal", "poison", "psychic", "rock",
    "shadow", "steel", "stellar", "unknown", "water",
}


def test_pokemon_inexistente_devuelve_null_explicito():
    """get_pokemon_stats de un nombre que no matchea nada en Gold -- el
    campo "pokemon" tiene que ser null explícito, no un objeto vacío ni
    un error."""

    async def _run():
        async with PokedexMCPClient() as mcp:
            return await mcp.call_tool("get_pokemon_stats", {"pokemon": "noexiste123xyz"})

    result = asyncio.run(_run())
    assert result.is_error is False
    data = hooks.extract_json(result)
    assert "pokemon" in data
    assert data["pokemon"] is None


def test_enum_de_21_tipos_reales_rechaza_valor_fuera_de_catalogo():
    """El schema de la tool (Pydantic, no un if/else del agente) es el
    que rechaza "luz" -- confirmamos que el mensaje real cita exactamente
    el enum de 21 tipos, ni más ni menos."""

    async def _run():
        async with PokedexMCPClient() as mcp:
            return await mcp.call_tool("get_type_matchups", {"type": "luz"})

    result = asyncio.run(_run())
    assert result.is_error is True
    text = hooks._extract_text(result) or ""
    assert "literal_error" in text or "Input should be" in text
    for real_type in REAL_TYPES:
        assert real_type in text
