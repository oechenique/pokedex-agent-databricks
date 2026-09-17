# 03 — Agente + MCP Server

## Personalidad vs. reglas operativas (Axioma 4 en carne propia)
Separar SIEMPRE en el system prompt:
```
IDENTITY  → "Sos el Profesor Oak, investigador de datos Pokémon..."
RULES     → restricciones operativas (nunca fabricar stats, distinguir
            resultado calculado de dato de fuente, si una tool falla
            reportarlo, nunca tratar isError:true como dato válido)
```
La personalidad hace que el proyecto sea divertido y compartible. Las reglas son las que el examen evalúa. No se mezclan en el mismo párrafo.

## Tools del MCP server (granulares, no una tool gigante)
```
get_pokemon_stats(pokemon: string, generation: integer | null)
search_pokemon(query: string, type: enum | null, generation: integer | null)
compare_pokemon(pokemon_a: string, pokemon_b: string)
get_type_matchups(type: enum)
get_card_info(pokemon: string)
```
Cada una con schema estricto: qué es requerido, qué es opcional, enums para `type` (fuego/agua/planta/... — nunca texto libre), y **null explícito** si el dato no existe (ej. `get_card_info` de un pokemon sin carta TCG devuelve `card: null`, no inventa una).

## tool_choice — dónde forzamos qué
- Cuando el usuario pide explícitamente comparar stats → `tool_choice: {"type":"tool","name":"compare_pokemon"}` forzado en esa llamada, para practicar el patrón de forzar una tool específica.
- Cuando la pregunta es ambigua pero factual (podría ser stats o carta) → `tool_choice: "any"` — obliga a usar alguna tool, nunca a que "invente" en prosa.
- Charla de personalidad/lore general (sin pedido de dato factual) → `tool_choice: "auto"`.

## Hooks (enforcement real, no solo logging)
- **`PreToolUse`**: valida el nombre del pokemon contra la lista canónica de Gold y el tipo de generación (int válido) ANTES de que la tool se ejecute. Si `generation = "banana"`, se bloquea ahí, no llega a pegarle a la tool.
- **`PostToolUse`**: inspecciona el `tool_result`. Si viene `isError: true`, marca explícitamente que el agente NO debe tratar ese resultado como dato válido para responder — tiene que reportar el fallo, no inventar sobre un resultado roto.

## Imagen en la respuesta estructurada
Cada tool que devuelve un pokemon incluye `image_url` (de PokeAPI official-artwork) como parte del JSON — no un campo aparte que el front tenga que buscar por su cuenta:
```json
{"name": "Charizard", "types": ["fire","flying"], "stats": {...}, "image_url": "https://..."}
```

## Escalado a multi-agente (fase 6, no antes)
Recién cuando single-agent + tools + hooks + structured output funcionan sólidos:
```
Coordinador ("Profesor Oak")
    ├── Pokemon Researcher   (stats/tipos vía PokeAPI-Gold)
    ├── Battle Analyst        (matchups/cálculos de batalla)
    └── Data Librarian        (lore/TCG)
```
Contexto entre subagentes: pasa explícito por el coordinador (referencia a las tablas Gold + resumen estructurado), nunca "los subagentes se llaman entre sí" ni memoria compartida automática — mismo patrón del Dominio 1 del examen.
