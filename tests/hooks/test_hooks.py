"""Dominio: hooks (reglas/03-agente-mcp.md). PreToolUse tiene que bloquear
la llamada ANTES de que le pegue a la tool real -- generation inválida
(chequeo local, sin tool call) y nombre de pokemon inexistente (la
"existence oracle": consulta get_pokemon_stats contra Gold en vivo, sin
lista canónica hardcodeada ni cacheada).
"""

import asyncio

import pytest

import hooks
from mcp_client import PokedexMCPClient


def test_generation_banana_bloqueada_en_pre_tool_use():
    async def _run():
        async with PokedexMCPClient() as mcp:
            ctx = hooks.HookContext(call_tool=mcp.call_tool)
            with pytest.raises(hooks.ToolBlocked):
                await hooks.pre_tool_use(
                    "get_pokemon_stats", {"pokemon": "pikachu", "generation": "banana"}, ctx
                )

    asyncio.run(_run())


def test_pokemon_inexistente_bloqueado_via_existence_oracle():
    """"pikachuzord" no existe en Gold -- el hook lo descubre llamando a
    get_pokemon_stats de verdad contra pokedex-mcp-server (el oráculo es
    la tool real, no una lista de nombres hardcodeada en el repo)."""

    async def _run():
        async with PokedexMCPClient() as mcp:
            ctx = hooks.HookContext(call_tool=mcp.call_tool)
            with pytest.raises(hooks.ToolBlocked):
                await hooks.pre_tool_use("get_pokemon_stats", {"pokemon": "pikachuzord"}, ctx)

    asyncio.run(_run())


def test_pokemon_real_pasa_pre_tool_use_sin_bloquear():
    """Control positivo -- un nombre real no debe disparar ToolBlocked,
    para confirmar que el test de arriba bloquea por inexistencia real y
    no por un bug que bloquee cualquier cosa."""

    async def _run():
        async with PokedexMCPClient() as mcp:
            ctx = hooks.HookContext(call_tool=mcp.call_tool)
            await hooks.pre_tool_use("get_pokemon_stats", {"pokemon": "pikachu"}, ctx)

    asyncio.run(_run())  # no debe levantar ToolBlocked
