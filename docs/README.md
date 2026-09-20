# docs/

## Notebooks del pipeline (`docs/notebooks/`)

Export HTML nativo de Databricks (`databricks jobs export-run`, no
`File → Export` manual pero el mismo mecanismo) de la corrida real más
reciente del job `pokedex-pipeline` con las 8 tasks en `SUCCESS`
(`run_id 431610569545728`) -- código + markdown + **outputs reales**
de esa ejecución, tal cual quedaron en Databricks. No son una copia ni
un resumen: al abrir cada archivo (necesita conexión a internet, carga
el mismo JS de render que usa Databricks) se ve exactamente lo que
corrió.

Orden real del pipeline (Bronze → Silver → DQ → Gold, `terraform/jobs.tf`):

| # | Notebook exportado | Qué hace |
|---|---|---|
| 1 | [`bronze_pokemon_api.html`](notebooks/bronze_pokemon_api.html) | Ingesta cruda de `/pokemon` (PokeAPI) a `bronze.pokemon_api_raw`, sin transformar. |
| 2 | [`bronze_species.html`](notebooks/bronze_species.html) | Ingesta cruda de `/pokemon-species` a `bronze.pokemon_species_raw` -- flavor text, tasa de captura, cadena de evolución. |
| 3 | [`bronze_types.html`](notebooks/bronze_types.html) | Ingesta cruda de `/type` a `bronze.pokemon_types_raw` -- fuente de los matchups de tipo que se calculan en Gold. |
| 4 | [`bronze_abilities.html`](notebooks/bronze_abilities.html) | Ingesta cruda de `/ability` a `bronze.pokemon_abilities_raw`. |
| 5 | [`bronze_moves.html`](notebooks/bronze_moves.html) | Ingesta cruda de `/move` a `bronze.pokemon_moves_raw` -- el endpoint más grande de los cinco (~900+ recursos). |
| 6 | [`silver_transform.html`](notebooks/silver_transform.html) | Aplana el JSON crudo de Bronze en 5 tablas Silver tipadas y deduplicadas (`pokemon`, `pokemon_stats`, `pokemon_types`, `pokemon_abilities`, `pokemon_moves`). |
| 7 | [`dq_check.html`](notebooks/dq_check.html) | Data Quality gate -- si un check falla, levanta una excepción real y frena el pipeline; Gold nunca se actualiza con datos sucios. |
| 8 | [`gold_aggregate.html`](notebooks/gold_aggregate.html) | Calcula `pokemon_profile`, `pokemon_battle_stats`, `pokemon_type_matchups` y `pokemon_generation_summary` -- la única capa que las tools del agente consultan. Solo corre si `dq_check` terminó OK. |

Las 5 tasks Bronze corren en paralelo dentro del job; el orden de la
tabla es el de lectura del pipeline (fuente → transformación → gate →
resultado final), no el de ejecución estricta task por task.
