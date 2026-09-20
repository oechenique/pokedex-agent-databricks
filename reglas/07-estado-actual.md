# 07 — Estado actual del proyecto

_Última actualización: Fase 5 cerrada (frontend Día/Noche + backend FastAPI real, validado en vivo con datos reales), 2026-09-18._

## Qué está cerrado

**Fase 1 — Terraform + Bronze.** Workspace Azure Databricks (Premium) desde cero, ADLS Gen2, catálogo Unity Catalog `pokedex` con schemas bronze/silver/gold, job de ingesta con 5 tasks en paralelo (`pokemon_api_raw`, `pokemon_species_raw`, `pokemon_types_raw`, `pokemon_abilities_raw`, `pokemon_moves_raw`) tal cual vienen de PokeAPI. Commiteado y pusheado.

**Fase 2 — Silver + Gold + DQ gate.** `silver.py` aplana Bronze en 5 tablas tipadas (`pokemon`, `pokemon_stats`, `pokemon_types`, `pokemon_abilities`, `pokemon_moves`); `generation` se resuelve joineando `species.url` contra `pokemon_species_raw` (nunca `species_id == pokemon_id`, por las formas alternativas). `dq_check.py` valida los 6 checks de `01-datos-medallion.md` y frena el pipeline de verdad si algo falla (probado con un bug real en la primera corrida: `gold_aggregate` se salteó solo). Gold: `pokemon_profile` (con lore, español si existe/inglés si no, una sola entrada), `pokemon_battle_stats`, `pokemon_type_matchups` (derivado del `damage_relations` real de PokeAPI, no hardcodeado), `pokemon_generation_summary`. `pokemon_card_summary` queda afuera (no hay TCG ingerido). Commiteado y pusheado.

**Fase 3 — MCP server sobre Databricks Apps.** 4 tools (`get_pokemon_stats`, `search_pokemon`, `compare_pokemon`, `get_type_matchups`) sobre `gold.*` — `get_card_info` queda afuera por lo mismo que `pokemon_card_summary`. Schema estricto con enum de 21 tipos reales (sacado de una query, no de memoria). Desplegado como Databricks App real (`pokedex-mcp-server`, `RUNNING`), probado de punta a punta contra la app en la nube, no solo local. Commiteado (`b174b2e` + commit de detalle `ec022c6`) y pusheado a `github.com/oechenique/pokedex-agent-databricks`.

### Hallazgo importante: dos audiencias de token distintas
El token que usa Terraform/CLI vía `az login` (Azure AD, recurso fijo "AzureDatabricks") sirve para las REST APIs del workspace (Jobs, SQL Statement Execution) — con eso alcanzó para todo Fase 1 y 2. **Pero no sirve para pegarle a una Databricks App desplegada**: el front door de Apps valida contra el OIDC nativo del propio workspace, que solo se consigue con `databricks auth login` (flujo OAuth por navegador, no headless). Si en alguna fase futura hay que llamar a la app programáticamente (ej. desde el agente en Fase 4), hay que loguearse así primero — no alcanza con la sesión de Azure CLI que ya está activa.

## Fase 4 — Agente + hooks + tool_choice (cerrada)

**Decisión de auth (resuelve el hallazgo de arriba):** el agente NO usa un service principal M2M todavía -- reusa el mismo perfil OAuth de `databricks auth login` (`adb-7405616363788532`) que ya está en `~/.databrickscfg`. `databricks.sdk.core.Config(profile=..., host=<url de la app>).authenticate()` devuelve headers válidos contra el front door de la app (mismo mecanismo que `databricks auth token --host <app-url>` de la CLI). Alcanza para desarrollo/pruebas manuales locales; si en Fase 5 el frontend en Vercel necesita llamar al agente sin una sesión interactiva de por medio, ahí sí hace falta credential M2M -- no antes.

**Arquitectura elegida:** loop manual con la Messages API de `anthropic` (no Claude Agent SDK, no tool runner beta) -- `tool_choice` es un parámetro literal de esa API, y los hooks necesitan un punto de intercepción exacto antes/después de cada tool call que un helper no expone igual de directo. Conexión MCP real (paquete `mcp`, streamable-http) contra `pokedex-mcp-server` ya desplegado, sin mocks.

Código en `agent/`: `system_prompt.py` (IDENTITY/RULES en bloques separados), `hooks.py` (`pre_tool_use` bloquea `generation` no-entero y nombres de pokemon inexistentes -- usando la propia tool `get_pokemon_stats` como oráculo de existencia contra Gold, sin lista canónica hardcodeada; `post_tool_use` marca `isError:true` como dato inválido explícito), `tool_choice.py` (heurística por palabras clave: comparación explícita → fuerza `compare_pokemon`; palabra clave factual → `any`; el resto → `auto`), `mcp_client.py`, `agent.py`, `cli.py` para probar a mano.

Validado en vivo contra la app real, con Claude en el loop (`python agent/cli.py`, o el driver de sesión) -- las 3 conversaciones manuales pedidas:

1. **PreToolUse bloquea nombre inválido.** Pedido explícito de llamar a `get_pokemon_stats(pokemon="Pikachuzord")` sin corregir el nombre. Claude llamó a la tool tal cual; el hook la bloqueó ANTES de pegarle al server (`tool_result` con `is_error=true` y el motivo del bloqueo); Claude nunca inventó una ficha y explicó la diferencia entre "bloqueado" y "null" en su respuesta (RULES #2/#4 del system prompt).
2. **tool_choice forzado a `compare_pokemon`.** "Comparame a Charizard contra Blastoise" -> `tool_choice.choose_tool_choice` calculó `{"type": "tool", "name": "compare_pokemon"}`; Claude llamó esa tool en la primera ronda (y además `get_type_matchups` por su cuenta ya sin forzado, en la segunda ronda) y separó en la respuesta el dato crudo de la tool de su propio cálculo del cruce de tipos.
3. **`isError:true` real, no fabricado.** Se le pidió a Claude llamar a `get_type_matchups(type="luz")` literal, sin traducir. El server (Pydantic, enum de 21 tipos) rechazó el valor con un error real; `post_tool_use` lo marcó inválido; Claude reportó el fallo explícitamente y no inventó matchups alrededor del error.

**Hallazgo del escenario 3 (auto-translation de Claude):** el primer intento de este escenario fue en prosa natural ("¿Cuáles son las debilidades y resistencias del tipo luz?"). No disparó ningún error: Claude mapeó "luz" a `fairy` por su cuenta (razonamiento de lore válido, no un tipo real) y devolvió los matchups de `fairy` sin tocar el enum inválido -- comportamiento correcto, pero inútil para probar `isError`. Hubo que forzar el escenario con una instrucción explícita ("pasá el valor 'luz' tal cual, no lo traduzcas ni lo mapees") para que Claude pasara el literal inválido y el server lo rechazara de verdad. Conclusión para `tool_choice.py`: `"any"` obliga a usar *alguna* tool, pero no obliga a que los argumentos sean literales del usuario -- Claude sigue teniendo margen para "corregir" la entrada antes de llamar, así que un test de `isError` genuino necesita bloquear ese margen a propósito, no alcanza con una pregunta ambigua.

Fase 4 cerrada -- ver commit para el detalle de archivos (`agent/`).

**Hallazgo aparte -- descartado con evidencia (2026-09-19):** se había anotado que `get_pokemon_stats` devolvía `lore` con acentos corrompidos (`Pok�mon` en vez de `Pokémon`), sospechando un mismatch de encoding en Bronze→Silver→Gold. Diagnóstico: `ingestion/pokeapi_client.py` es encoding-safe (PokeAPI responde `charset=utf-8` explícito; `json.dumps(payload)` en Bronze usa `ensure_ascii=True`, o sea ASCII puro hasta que Spark `from_json` lo desescapa) y no cambió desde Fase 1/2. Se verificó en vivo contra `gold.pokemon_profile` (SQL Warehouse serverless, solo lectura, sin re-correr el job): de las 1351 filas con `lore` no nulo, `RLIKE '�'` y `LIKE '%Ã%'` (las dos firmas típicas de corrupción) dieron **0 filas** ambas; el lore de Charizard en hex confirma UTF-8 correcto (`más`, `débil`, `usará` bien codificados). Conclusión: no hay bug en el pipeline ni en los datos ya persistidos -- el `Pok�mon` visto en Fase 4/5 fue casi seguro un artefacto de codepage de la consola de Windows al correr `agent/cli.py` localmente (mismo patrón que el falso positivo de "Pokèmon" en Fase 3), o quedó pisado por un rerun posterior de `gold_aggregate` (hace `overwrite`). No requiere fix de código ni rerun del job.

## Fase 5 — Frontend Día/Noche + backend FastAPI real (cerrada)

**Arquitectura:** dos piezas nuevas, ninguna toca `agent/*.py` de Fase 4.

- `backend/` — FastAPI pensado para Vercel Python runtime (`pyproject.toml` con `[tool.vercel] entrypoint = "backend.app:app"`, Root Directory del proyecto Vercel queda en la raíz del repo para que `agent/` viaje en el mismo bundle sin duplicar código; `vercel.json` excluye `frontend/`, `terraform/`, etc. del bundle). `app.py` importa `agent/agent.py` y `mcp_client.py` tal cual via `sys.path` (mismo patrón que `agent/cli.py`), expone `/api/chat` stateless (el front manda el historial completo cada vez, como pide la Messages API), y aplica rate limit (`rate_limit.py`, placeholder en memoria) antes de tocar el agente. `render.py` es la pieza nueva de lógica real: mira los `tool_result` de ESE turno (nunca uno bloqueado por un hook ni con `isError`) y clasifica la respuesta en `pokemon`/`compare`/`matchups`/`texto` para que el front sepa qué componente renderizar — sin esto, el front solo tenía la prosa de Claude y no podía cumplir reglas/04-frontend.md.
- `frontend/` — Next.js 16 (App Router, TypeScript), sin Tailwind (CSS variables + `next-themes`). Tema Día (Hada/Luz: pastel cálido, dorado) y Noche (Fantasma/Siniestro: violeta profundo, fosforescente), toggle manual + default por `prefers-color-scheme`. Componentes por tipo de dato: `PokemonCard`, `CompareTable`, `TypeMatchupBadges` (badges agrupados por efectividad: Débil/Resiste/Inmune, Fuerte/Poco efectivo/Sin efecto), y `OakText` (markdown vía `react-markdown` + `remark-gfm` — las respuestas reales de Oak vienen con tablas/negrita, sin esto se verían los asteriscos crudos).

**Auth (sigue igual que Fase 4, a propósito):** `mcp_client.py` no se tocó — local sigue resolviendo con el perfil de `databricks auth login`. Producción en Vercel todavía no tiene esto resuelto (ver "Qué falta").

**Validado en vivo, los 2 temas, datos reales (no mockeados):** los 3 formatos de reglas/04-frontend.md corriendo contra el backend real -- ficha de pokemon (Charizard), comparación (Charizard vs. Blastoise, con winner bold por stat) y type matchups (tipo fuego, badges agrupados). El diseño había arrancado con datos mockeados para iterar rápido sobre el tema visual; se reemplazaron por las llamadas reales antes de cerrar la fase.

## Qué falta

- **Service principal M2M + deploy real a Vercel.** `mcp_client.py` funciona hoy con el perfil OAuth interactivo de `databricks auth login`, que no existe en un entorno serverless headless. Hace falta: un service principal de Databricks con OAuth M2M (Terraform, todavía no escrito), setear `DATABRICKS_CLIENT_ID`/`DATABRICKS_CLIENT_SECRET` como env vars de Vercel (`Config` de databricks-sdk los detecta solo, sin tocar código), y recién ahí el deploy de `backend/` y `frontend/` como dos proyectos Vercel separados (ver comentario en `pyproject.toml`/`vercel.json` para el porqué de esa separación).
- **`tests/`** — casos reproducibles mapeados a los dominios del examen CCA-F (`tool_choice/`, `tool_errors/`, `hooks/`, `structured_output/`, `permissions/`, `subagents/`, `claude_code/`), todavía no se creó nada de esta carpeta.
- **Fase 6 (opcional, solo si da el tiempo)** — Multi-agente: orchestrator + Pokemon Researcher / Battle Analyst / Data Librarian.
- **Docs HTML para el video** — falta armar la documentación/presentación en HTML pensada para grabar el video de demo del proyecto.

## Recursos vivos en Azure ahora mismo

Todo esto sigue consumiendo el crédito del workspace pago mientras exista:

| Recurso | Nombre | Estado |
|---|---|---|
| Resource group | `pokedex-rg` | activo |
| Databricks workspace | `pokedex-workspace` (Premium SKU) | activo |
| Storage account (ADLS Gen2) | `pokedexu13ui3` — containers `bronze`/`silver`/`gold`/`unity-catalog` | activo |
| Unity Catalog | catálogo `pokedex`, schemas `bronze`/`silver`/`gold` | activo |
| SQL Warehouse | "Serverless Starter Warehouse" (`e783d583f5b7768d`) — preexistente de la cuenta, no gestionado por Terraform | serverless, se auto-suspende solo |
| Job | `pokedex-pipeline` (`103793069144325`) — bronze×5 → silver_transform → dq_check → gold_aggregate | solo corre on-demand, no consume nada parado |
| **Databricks App** | `pokedex-mcp-server` — compute `MEDIUM` | **`RUNNING` de forma continua** — a diferencia del warehouse y el job, esto es cómputo prendido todo el tiempo. Si el crédito aprieta, se puede parar con `databricks apps stop pokedex-mcp-server` y volver a levantar cuando se retome Fase 4 (`databricks apps start`), sin perder nada (el código y el estado quedan en Terraform/workspace). |

## Próximo paso concreto para arrancar mañana

Sesión nueva, contexto limpio: arrancar por el service principal M2M (Terraform) + deploy real a Vercel -- es lo único que bloquea que el proyecto deje de depender de una sesión local. Después, `tests/`. Multi-agente (Fase 6) queda opcional al final si da el tiempo. Antes de eso, si el crédito del workspace aprieta, considerar `databricks apps stop pokedex-mcp-server` (queda todo en Terraform/workspace, se vuelve a levantar con `databricks apps start` cuando haga falta).
