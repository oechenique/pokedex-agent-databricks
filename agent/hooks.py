"""Hooks PreToolUse / PostToolUse (reglas/03-agente-mcp.md) -- enforcement
real sobre las 4 tools de pokedex-mcp-server, no logging decorativo.

PreToolUse corre ANTES de pegarle a la tool real y puede bloquear la
llamada por completo (ToolBlocked): valida que `generation` sea un entero
válido y que cualquier nombre de pokemon exista de verdad en Gold. La
validación de existencia usa la propia tool `get_pokemon_stats` como
oráculo -- match exacto contra Gold, nunca una lista canónica hardcodeada
ni cacheada en el agente.

PostToolUse corre DESPUÉS de una llamada real (haya pasado el PreToolUse o
no) e inspecciona el `CallToolResult` del protocolo MCP: si `isError` es
true, el resultado se marca explícito como inválido -- el agente no puede
tratarlo como dato (RULES #4 en `system_prompt.py`).
"""

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

POKEMON_NAME_FIELDS = ("pokemon", "pokemon_a", "pokemon_b")

CallTool = Callable[[str, dict], Awaitable[Any]]


class ToolBlocked(Exception):
    """El PreToolUse bloqueó la llamada antes de que le pegue a la tool real."""


@dataclass
class HookContext:
    call_tool: CallTool


async def pre_tool_use(tool_name: str, tool_input: dict, ctx: HookContext) -> None:
    """Levanta ToolBlocked si algo no pasa la validación. No devuelve nada
    si está todo bien -- silencio es luz verde."""
    generation = tool_input.get("generation")
    if generation is not None and not _is_valid_generation(generation):
        raise ToolBlocked(
            f"generation={generation!r} no es un entero válido (1-9) -- "
            f"{tool_name} bloqueada antes de ejecutarse."
        )

    for field in POKEMON_NAME_FIELDS:
        name = tool_input.get(field)
        if not name:
            continue
        if not await _pokemon_exists(name, ctx):
            raise ToolBlocked(
                f"'{name}' no matchea ningún pokemon en la capa Gold -- "
                f"{tool_name} bloqueada antes de ejecutarse."
            )


def post_tool_use(tool_name: str, result: Any) -> dict:
    """Devuelve {"ok": True, "data": ...} o {"ok": False, "error": ...}.
    `ok: False` es la señal de que el agente nunca debe usar esto como dato."""
    if result.is_error:
        return {
            "ok": False,
            "error": _extract_text(result) or f"{tool_name} devolvió isError=true sin detalle.",
        }
    return {"ok": True, "data": extract_json(result)}


def extract_json(result: Any) -> Any:
    """La Statement Execution API detrás de las tools no expone output
    schema, así que `structuredContent` viene vacío -- el dato real está
    serializado como texto en `content[0]`. Se prueba structured_content
    primero por si esto cambia en el futuro."""
    if result.structured_content is not None:
        return result.structured_content
    text = _extract_text(result)
    return json.loads(text) if text else None


def _extract_text(result: Any) -> Optional[str]:
    for block in result.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return None


def _is_valid_generation(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return 1 <= value <= 9
    if isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            return False
        return 1 <= parsed <= 9
    return False


async def _pokemon_exists(name: str, ctx: HookContext) -> bool:
    result = await ctx.call_tool("get_pokemon_stats", {"pokemon": name})
    if result.is_error:
        # La tool de validación misma falló (ej. warehouse caído) -- no es
        # un "no existe", es un fallo de infraestructura. Se deja pasar la
        # llamada real, que va a fallar de la misma forma y lo va a
        # reportar por PostToolUse.
        return True
    data = extract_json(result) or {}
    return data.get("pokemon") is not None
