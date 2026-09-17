"""Databricks App entrypoint -- MCP server puro sobre gold.* de Unity
Catalog (reglas/03-agente-mcp.md). Sin Dockerfile: Databricks Apps corre
esto directo con `app.yaml` + `requirements.txt`.

Sin hooks ni tool_choice acá -- eso es Fase 4 (capa agente), esta fase es
solo las 4 tools sobre Gold. get_card_info queda afuera: no ingerimos
pokemontcg.io todavía.
"""

import os
from typing import Literal, Optional

from mcp.server.mcpserver import MCPServer

import tools

# Los 21 tipos reales de gold.pokemon_type_matchups (incluye "unknown" y
# "shadow", que PokeAPI usa para casos especiales) -- nunca texto libre.
PokemonType = Literal[
    "bug",
    "dark",
    "dragon",
    "electric",
    "fairy",
    "fighting",
    "fire",
    "flying",
    "ghost",
    "grass",
    "ground",
    "ice",
    "normal",
    "poison",
    "psychic",
    "rock",
    "shadow",
    "steel",
    "stellar",
    "unknown",
    "water",
]

mcp = MCPServer(
    name="pokedex-mcp-server",
    instructions=(
        "Tools de solo lectura sobre la capa Gold del catalogo Unity "
        "Catalog 'pokedex'. Todo dato ya viene calculado y validado por "
        "el pipeline Medallion (Bronze -> Silver -> DQ gate -> Gold) -- "
        "estas tools nunca inventan un resultado: si un pokemon no "
        "existe devuelven null, si una busqueda no matchea nada "
        "devuelven una lista vacia."
    ),
)


@mcp.tool()
def get_pokemon_stats(pokemon: str, generation: Optional[int] = None) -> dict:
    """Ficha completa de un pokemon: stats + tipos + sprite/artwork + lore,
    desde gold.pokemon_profile + gold.pokemon_battle_stats.

    Args:
        pokemon: nombre exacto del pokemon (case-insensitive), ej. "pikachu".
        generation: si se pasa, solo matchea si ese pokemon pertenece a esa
            generación (1-9); si no coincide, devuelve pokemon: null.
    """
    return tools.get_pokemon_stats(pokemon, generation)


@mcp.tool()
def search_pokemon(
    query: str,
    type: Optional[PokemonType] = None,
    generation: Optional[int] = None,
) -> dict:
    """Busca pokemon por substring de nombre (case-insensitive), con
    filtros opcionales de tipo y generación. Devuelve hasta 25 resultados
    livianos (id/nombre/generación/tipos/imagen) -- para la ficha completa
    de un pokemon puntual está get_pokemon_stats.

    Args:
        query: substring del nombre a buscar.
        type: filtra por tipo exacto, uno de los 21 tipos reales.
        generation: filtra por generación (1-9).
    """
    return tools.search_pokemon(query, type, generation)


@mcp.tool()
def compare_pokemon(pokemon_a: str, pokemon_b: str) -> dict:
    """Compara dos pokemon lado a lado: perfil + battle_stats de cada uno,
    cada lado independiente (si uno no existe, el otro se devuelve igual).

    Args:
        pokemon_a: nombre exacto del primer pokemon.
        pokemon_b: nombre exacto del segundo pokemon.
    """
    return tools.compare_pokemon(pokemon_a, pokemon_b)


@mcp.tool()
def get_type_matchups(type: PokemonType) -> dict:
    """Efectividad de daño de un tipo -- ofensiva (este tipo atacando a
    cada otro) y defensiva (cada otro tipo atacando a este) -- desde
    gold.pokemon_type_matchups, calculado con reglas deterministas del
    propio PokeAPI, nunca inferido por un LLM.

    Args:
        type: uno de los 21 tipos reales de PokeAPI.
    """
    return tools.get_type_matchups(type)


if __name__ == "__main__":
    port = int(os.environ.get("DATABRICKS_APP_PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
