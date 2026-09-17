"""Lógica de las 4 tools (reglas/03-agente-mcp.md), separada de la
capa MCP (app.py) para poder probarla directo con Python, sin pasar por
el protocolo. Cada función es pura: recibe params ya validados por el
schema de la tool y devuelve un dict serializable a JSON.

Regla dura: si un pokemon no existe o no matchea la búsqueda, se
devuelve null / lista vacía explícita -- ninguna función acá inventa un
resultado ni completa con un valor plausible.
"""

import json
from typing import Any, Optional

from db import run_query

GOLD_SCHEMA = "gold"


def _parse_types_array(raw: Optional[str]) -> list[str]:
    # gold.pokemon_profile.types es ARRAY<STRING> -- la Statement
    # Execution API serializa arrays como texto JSON en el resultado.
    return json.loads(raw) if raw else []


def _to_int(value: Any) -> Optional[int]:
    return int(value) if value is not None else None


def _to_float(value: Any) -> Optional[float]:
    return float(value) if value is not None else None


def _row_to_pokemon(row: dict) -> dict:
    return {
        "pokemon_id": _to_int(row.get("pokemon_id")),
        "name": row.get("pokemon_name"),
        "generation": _to_int(row.get("generation")),
        "types": _parse_types_array(row.get("types")),
        "height": _to_int(row.get("height")),
        "weight": _to_int(row.get("weight")),
        "image_url": row.get("artwork_url"),
        "lore": row.get("lore"),
        "stats": {
            "hp": _to_int(row.get("hp")),
            "attack": _to_int(row.get("attack")),
            "defense": _to_int(row.get("defense")),
            "special_attack": _to_int(row.get("special_attack")),
            "special_defense": _to_int(row.get("special_defense")),
            "speed": _to_int(row.get("speed")),
        },
        "total_stats": _to_int(row.get("total_stats")),
        "attack_defense_ratio": _to_float(row.get("attack_defense_ratio")),
    }


_POKEMON_PROFILE_COLUMNS = """
    p.pokemon_id, p.pokemon_name, p.generation, p.types, p.height, p.weight,
    p.artwork_url, p.lore,
    b.hp, b.attack, b.defense, b.special_attack, b.special_defense, b.speed,
    b.total_stats, b.attack_defense_ratio
"""


def _find_pokemon(pokemon: str, generation: Optional[int]) -> Optional[dict]:
    where = ["lower(trim(p.pokemon_name)) = lower(trim(:pokemon))"]
    params: dict[str, tuple] = {"pokemon": (pokemon, "STRING")}
    if generation is not None:
        where.append("p.generation = :generation")
        params["generation"] = (generation, "INT")

    sql = f"""
        SELECT {_POKEMON_PROFILE_COLUMNS}
        FROM pokemon_profile p
        JOIN pokemon_battle_stats b ON b.pokemon_id = p.pokemon_id
        WHERE {" AND ".join(where)}
        LIMIT 1
    """
    rows = run_query(sql, schema=GOLD_SCHEMA, parameters=params)
    return _row_to_pokemon(rows[0]) if rows else None


def get_pokemon_stats(pokemon: str, generation: Optional[int] = None) -> dict:
    """get_pokemon_stats(pokemon, generation?) -> {"pokemon": {...} | null}"""
    return {"pokemon": _find_pokemon(pokemon, generation)}


def search_pokemon(query: str, type: Optional[str] = None, generation: Optional[int] = None) -> dict:
    """search_pokemon(query, type?, generation?) -> {"results": [...]}

    Búsqueda por substring (case-insensitive) sobre pokemon_name, con
    filtros opcionales de tipo y generación. Tope de 25 resultados -- es
    una tool de listado liviano, no de ficha completa (para eso está
    get_pokemon_stats).
    """
    where = ["lower(pokemon_name) LIKE lower(:pattern)"]
    params: dict[str, tuple] = {"pattern": (f"%{query}%", "STRING")}
    if type is not None:
        where.append("array_contains(types, :type)")
        params["type"] = (type, "STRING")
    if generation is not None:
        where.append("generation = :generation")
        params["generation"] = (generation, "INT")

    sql = f"""
        SELECT pokemon_id, pokemon_name, generation, types, artwork_url
        FROM pokemon_profile
        WHERE {" AND ".join(where)}
        ORDER BY pokemon_id
        LIMIT 25
    """
    rows = run_query(sql, schema=GOLD_SCHEMA, parameters=params)
    results = [
        {
            "pokemon_id": _to_int(r.get("pokemon_id")),
            "name": r.get("pokemon_name"),
            "generation": _to_int(r.get("generation")),
            "types": _parse_types_array(r.get("types")),
            "image_url": r.get("artwork_url"),
        }
        for r in rows
    ]
    return {"results": results}


def compare_pokemon(pokemon_a: str, pokemon_b: str) -> dict:
    """compare_pokemon(pokemon_a, pokemon_b) -> perfiles + battle_stats de
    ambos, lado a lado. Cada lado es independiente: si uno no existe, el
    otro se devuelve igual (nunca se invalidan entre sí)."""
    return {
        "pokemon_a": _find_pokemon(pokemon_a, None),
        "pokemon_b": _find_pokemon(pokemon_b, None),
    }


def get_type_matchups(type: str) -> dict:
    """get_type_matchups(type) -> efectividad ofensiva (este tipo atacando
    a cada otro) y defensiva (cada otro tipo atacando a este) -- ambas
    direcciones salen de la misma tabla determinista
    gold.pokemon_type_matchups, ninguna se infiere."""
    offensive_rows = run_query(
        """
        SELECT defending_type, damage_multiplier, effectiveness
        FROM pokemon_type_matchups
        WHERE attacking_type = :type
        ORDER BY defending_type
        """,
        schema=GOLD_SCHEMA,
        parameters={"type": (type, "STRING")},
    )
    defensive_rows = run_query(
        """
        SELECT attacking_type, damage_multiplier, effectiveness
        FROM pokemon_type_matchups
        WHERE defending_type = :type
        ORDER BY attacking_type
        """,
        schema=GOLD_SCHEMA,
        parameters={"type": (type, "STRING")},
    )

    return {
        "type": type,
        "offensive": [
            {
                "defending_type": r.get("defending_type"),
                "damage_multiplier": _to_float(r.get("damage_multiplier")),
                "effectiveness": r.get("effectiveness"),
            }
            for r in offensive_rows
        ],
        "defensive": [
            {
                "attacking_type": r.get("attacking_type"),
                "damage_multiplier": _to_float(r.get("damage_multiplier")),
                "effectiveness": r.get("effectiveness"),
            }
            for r in defensive_rows
        ],
    }
