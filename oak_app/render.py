"""Clasifica la respuesta de un turno en el formato que le toca según
reglas/04-frontend.md (pokemon->tarjeta, comparación->tabla, matchups->
badges, resto->texto). Copia literal de backend/render.py -- mismo
contrato, deployado en dos Databricks Apps distintas (Vercel/backend
sigue existiendo pero ya no es el plan activo, ver reglas/07).

Mira los tool_result reales de ESTE turno -- nunca uno bloqueado por un
hook ni con isError, y nunca inventa un formato si no hay datos de
verdad detrás. No toca agent/*.py: opera sobre la lista ya serializada
(dicts planos, ver serialize.py) que devuelve agent.send(), después de
que corrió.
"""

import json
from typing import Any

# Orden de prioridad cuando un turno disparó más de una tool -- compare es
# la más específica/completa, matchups la más genérica.
_PRIORITY = ["compare_pokemon", "get_pokemon_stats", "get_type_matchups"]


def build_render(turn_messages: list[dict]) -> dict[str, Any]:
    tool_name_by_id: dict[str, str] = {}
    tool_data_by_name: dict[str, Any] = {}

    for message in turn_messages:
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                tool_name_by_id[block["id"]] = block["name"]
            elif block.get("type") == "tool_result" and not block.get("is_error"):
                name = tool_name_by_id.get(block.get("tool_use_id"))
                if not name:
                    continue
                raw = block.get("content")
                if not isinstance(raw, str):
                    continue
                try:
                    tool_data_by_name[name] = json.loads(raw)
                except ValueError:
                    continue

    for name in _PRIORITY:
        data = tool_data_by_name.get(name)
        if data is None:
            continue
        if name == "compare_pokemon":
            return {"kind": "compare", "compare": data}
        if name == "get_pokemon_stats" and data.get("pokemon") is not None:
            return {"kind": "pokemon", "pokemon": data["pokemon"]}
        if name == "get_type_matchups":
            return {"kind": "matchups", "matchups": data}

    return {"kind": "text"}
