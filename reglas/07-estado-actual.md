# 07 — Estado actual del proyecto

_Última actualización: Fase 3 cerrada, 2026-09-17._

## Qué está cerrado

**Fase 1 — Terraform + Bronze.** Workspace Azure Databricks (Premium) desde cero, ADLS Gen2, catálogo Unity Catalog `pokedex` con schemas bronze/silver/gold, job de ingesta con 5 tasks en paralelo (`pokemon_api_raw`, `pokemon_species_raw`, `pokemon_types_raw`, `pokemon_abilities_raw`, `pokemon_moves_raw`) tal cual vienen de PokeAPI. Commiteado y pusheado.

**Fase 2 — Silver + Gold + DQ gate.** `silver.py` aplana Bronze en 5 tablas tipadas (`pokemon`, `pokemon_stats`, `pokemon_types`, `pokemon_abilities`, `pokemon_moves`); `generation` se resuelve joineando `species.url` contra `pokemon_species_raw` (nunca `species_id == pokemon_id`, por las formas alternativas). `dq_check.py` valida los 6 checks de `01-datos-medallion.md` y frena el pipeline de verdad si algo falla (probado con un bug real en la primera corrida: `gold_aggregate` se salteó solo). Gold: `pokemon_profile` (con lore, español si existe/inglés si no, una sola entrada), `pokemon_battle_stats`, `pokemon_type_matchups` (derivado del `damage_relations` real de PokeAPI, no hardcodeado), `pokemon_generation_summary`. `pokemon_card_summary` queda afuera (no hay TCG ingerido). Commiteado y pusheado.

**Fase 3 — MCP server sobre Databricks Apps.** 4 tools (`get_pokemon_stats`, `search_pokemon`, `compare_pokemon`, `get_type_matchups`) sobre `gold.*` — `get_card_info` queda afuera por lo mismo que `pokemon_card_summary`. Schema estricto con enum de 21 tipos reales (sacado de una query, no de memoria). Desplegado como Databricks App real (`pokedex-mcp-server`, `RUNNING`), probado de punta a punta contra la app en la nube, no solo local. Commiteado (`b174b2e` + commit de detalle `ec022c6`) y pusheado a `github.com/oechenique/pokedex-agent-databricks`.

### Hallazgo importante: dos audiencias de token distintas
El token que usa Terraform/CLI vía `az login` (Azure AD, recurso fijo "AzureDatabricks") sirve para las REST APIs del workspace (Jobs, SQL Statement Execution) — con eso alcanzó para todo Fase 1 y 2. **Pero no sirve para pegarle a una Databricks App desplegada**: el front door de Apps valida contra el OIDC nativo del propio workspace, que solo se consigue con `databricks auth login` (flujo OAuth por navegador, no headless). Si en alguna fase futura hay que llamar a la app programáticamente (ej. desde el agente en Fase 4), hay que loguearse así primero — no alcanza con la sesión de Azure CLI que ya está activa.

## Qué falta

- **Fase 4** — Agente (Claude Agent SDK) single-agent sobre las 4 tools del MCP server: system prompt con IDENTITY/RULES separados ("Profesor Oak"), hooks `PreToolUse`/`PostToolUse` (validar pokemon/generation antes de pegarle a la tool, nunca tratar `isError:true` como dato válido), `tool_choice` forzado en `compare_pokemon` cuando el pedido es explícito. Acá es donde entra en juego el hallazgo de auth de arriba.
- **Fase 5** — Frontend en Vercel, consumiendo el agente (nunca pegándole directo a Databricks desde el browser), formato de salida según tipo de dato (tarjeta/tabla/badges/texto).
- **Fase 6** (opcional, solo si da el tiempo) — Multi-agente: orchestrator + Pokemon Researcher / Battle Analyst / Data Librarian.
- **`tests/`** — casos reproducibles mapeados a los dominios del examen CCA-F (`tool_choice/`, `tool_errors/`, `hooks/`, `structured_output/`, `permissions/`, `subagents/`, `claude_code/`), todavía no se creó nada de esta carpeta.

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

Empezar Fase 4 leyendo `reglas/03-agente-mcp.md` (ya escrito) y decidiendo cómo el agente se autentica contra `pokedex-mcp-server` en runtime — el hallazgo de arriba (auth de Apps ≠ auth de Azure CLI) es la primera decisión de diseño a tomar, antes de escribir una línea del agente: ¿el agente corre con una sesión `databricks auth login` propia, o hay que armar un service principal M2M con client credentials para no depender de un login interactivo en producción?
