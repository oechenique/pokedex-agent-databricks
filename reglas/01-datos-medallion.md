# 01 — Datos y arquitectura Medallion

## Bronze (raw, sin tocar)
Tablas Delta con el JSON crudo tal cual viene de la fuente, sin transformar:
- `pokemon_api_raw` (PokeAPI: pokemon endpoint)
- `pokemon_species_raw` (PokeAPI: species — flavor text, tasa de captura, etc.)
- `pokemon_types_raw`, `pokemon_abilities_raw`, `pokemon_moves_raw`
- `tcg_cards_raw` (pokemontcg.io)
- `wiki_lore_raw` (Bulbapedia/Wikipedia — SOLO texto)

Regla: Bronze nunca se sobreescribe con lógica de negocio. Si hay que reprocesar, se reprocesa desde acá.

## Silver (normalizado y limpio)
- `pokemon` (id, nombre, altura, peso, sprite_url, artwork_url)
- `pokemon_stats` (hp, attack, defense, special_attack, special_defense, speed — tipados como int, nunca string)
- `pokemon_types` (relación pokemon↔tipo, normalizada, no array embebido)
- `pokemon_abilities`
- `pokemon_moves`
- `tcg_cards` (normalizado: id, pokemon_id resuelto — no nombre de texto libre —, rareza, puntos, precio_mercado nullable)

Transformaciones típicas acá: deduplicación, aplanado de estructuras anidadas del JSON de PokeAPI, resolución de IDs (nombre de carta TCG → `pokemon_id` vía matching, no dejarlo como texto libre suelto), tipado correcto.

## Gold (listo para el agente — la ÚNICA capa que las tools consultan)
- `pokemon_profile` — ficha completa: stats + tipos + sprite/artwork + lore resumido
- `pokemon_battle_stats` — stats de batalla ya calculados (totales, ratios ataque/defensa)
- `pokemon_type_matchups` — tabla de efectividad de tipos (débil/fuerte contra qué), **calculada con reglas deterministas, no que el LLM la infiera**
- `pokemon_generation_summary` — agregados por generación
- `pokemon_card_summary` — mejor carta por pokemon (rareza/puntos), precio si existe

**Regla dura: cualquier cálculo (totales, ratios, matchups) se hace en el pipeline, no en el prompt del agente.** El agente lee el resultado ya calculado — mismo principio que ya usás en el asesor de turismo (los scores se calculan en el pipeline, el LLM solo redacta).

## Data Quality gate (entre Silver y Gold)
Checks mínimos, si fallan **el pipeline se detiene y Gold no se actualiza** (el agente nunca ve datos inválidos):
```
pokemon_id IS NOT NULL
pokemon_name IS NOT NULL
attack >= 0, defense >= 0, hp > 0
generation BETWEEN 1 AND 9
pokemon_name UNIQUE (dentro de su generación/forma)
```

## Nulls — regla del examen aplicada acá
Si un pokemon no tiene carta TCG o no tiene precio de mercado → **null explícito** en `pokemon_card_summary`, nunca inventar un precio ni "estimarlo". El agente, al recibir null, lo dice tal cual ("no hay carta TCG registrada para este Pokémon"), no rellena con un valor plausible.
