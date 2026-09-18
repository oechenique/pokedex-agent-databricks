"""tool_choice por turno (reglas/03-agente-mcp.md) -- heurística
deterministica por palabras clave, a propósito: lo que se practica acá es
el patrón forzado/any/auto de la Messages API, no un clasificador de
intención sofisticado.

Orden de precedencia (el primero que matchea gana):
1. Pedido explícito de comparar -> fuerza compare_pokemon.
2. Pregunta con palabra clave factual (stats/tipo/carta/etc.) pero sin
   pedido de comparación explícito -> "any" (alguna tool, nunca prosa
   inventada).
3. Cualquier otra cosa (charla, lore, opinión) -> "auto".
"""

import re

_COMPARE_PATTERN = re.compile(
    r"compar|\bvs\.?\b|\bversus\b|\bcontra\b|diferenc",
    re.IGNORECASE,
)

_FACTUAL_KEYWORDS = re.compile(
    r"estad[ií]stica|\bstats?\b|\btipo\b|altura|peso|\bficha\b|\bcarta\b|"
    r"generaci[oó]n|efectiv|matchup|debilidad|resistenc|cu[aá]nto (mide|pesa)",
    re.IGNORECASE,
)


def choose_tool_choice(user_message: str) -> dict:
    if _COMPARE_PATTERN.search(user_message):
        return {"type": "tool", "name": "compare_pokemon"}
    if _FACTUAL_KEYWORDS.search(user_message):
        return {"type": "any"}
    return {"type": "auto"}
