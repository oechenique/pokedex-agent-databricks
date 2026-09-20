"""Dominio: tool_errors (reglas/03-agente-mcp.md, escenario 3 de Fase 4;
reglas/07-estado-actual.md documenta el hallazgo de auto-translation).

get_type_matchups tiene un enum estricto de 21 tipos reales -- un valor
fuera de ese enum tiene que producir un isError genuino del protocolo
MCP (no un error inventado), y el agente tiene que reportarlo tal cual,
nunca fabricar un matchup alrededor de un error.
"""

import asyncio

from agent import Agent
from mcp_client import PokedexMCPClient


def test_enum_invalido_produce_iserror_genuino():
    """Llamada directa a la tool real -- confirma que el MCP server
    (Pydantic, enum de 21 tipos) rechaza un valor fuera de catálogo con
    isError real, no un mock de la respuesta."""

    async def _run():
        async with PokedexMCPClient() as mcp:
            return await mcp.call_tool("get_type_matchups", {"type": "luz"})

    result = asyncio.run(_run())
    assert result.is_error is True


def test_agente_reporta_el_fallo_sin_fabricar():
    """Reproduce el hallazgo de Fase 4 (reglas/07): Claude por su cuenta
    mapea "luz" a "fairy" (lore válido) y NUNCA dispara isError -- hay
    que forzar el literal explícito para probar el escenario real."""

    async def _run() -> str:
        async with PokedexMCPClient() as mcp:
            agent = Agent(mcp)
            await agent.load_tools()
            return await agent.send(
                "Llamá a get_type_matchups con type='luz' tal cual, la palabra "
                "literal 'luz' -- no la traduzcas ni la mapees a ningún tipo real."
            )

    reply = asyncio.run(_run())
    lowered = reply.lower()
    # No tiene que fabricar una tabla de matchups de un tipo "luz" inexistente.
    assert "super_effective" not in lowered
    # Tiene que reportar el fallo de alguna forma explícita.
    assert any(kw in lowered for kw in ("error", "no existe", "inválid", "no es un tipo", "rechaz", "fall"))
