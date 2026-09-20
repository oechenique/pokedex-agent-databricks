# tests/

Casos reproducibles mapeados a los dominios del examen CCA-F
(`reglas/06-ccaf-mapa-y-convenciones.md`). Todo lo que es código en esta
carpeta corre contra el sistema real -- `pokedex-mcp-server` (Databricks
App real) y el agente real vía la API de Claude -- nunca contra un mock.
`claude_code/` es la única excepción: son ejemplos documentados, no
tests de código (ver `claude_code/EJEMPLOS.md`).

## Correr la suite

```bash
cp .env.example .env   # completar, si todavía no lo hiciste (raíz del repo)
pip install -r tests/requirements.txt
pip install -r agent/requirements.txt
cd terraform && terraform init   # una vez, si no corriste terraform antes -- tests/permissions/ usa `terraform output`
cd ..
pytest tests/ -v
```

`tests/permissions/` necesita además que Terraform esté inicializado en
`terraform/` (usa `terraform output` para extraer las credenciales del
service principal M2M, nunca hardcodeadas -- reglas/05-guardrails-
seguridad.md) y que el SQL warehouse esté disponible (se auto-resuma
solo si estaba dormido, puede tardar unos segundos extra la primera
corrida).

## Carpetas

| Carpeta | Qué prueba |
|---|---|
| `tool_choice/` | Heurística real de forzado/any/auto (`agent/tool_choice.py`) + confirmación en vivo de que el forzado se traduce en la tool_use real de Claude. |
| `tool_errors/` | `isError` genuino de un enum inválido, y que el agente lo reporta sin fabricar un resultado alrededor. |
| `hooks/` | `PreToolUse` bloqueando `generation` inválida y un pokemon inexistente (existence oracle real contra Gold). |
| `structured_output/` | `null` explícito para un dato ausente, y el schema (Pydantic) rechazando un tipo fuera del enum de 21 reales. |
| `permissions/` | El service principal M2M (mismo perfil de permisos que oak_app) puede SELECT en `gold`, no puede ni siquiera `USE SCHEMA` en `bronze`/`silver`. |
| `subagents/` | Coordinador + subagentes reales (Fase 6): contexto explícito pasado por el coordinador, aislamiento estructural (ningún subagente puede llamar a otro), y regresión del bug real de scope (Mega Evoluciones no pedidas). |
| `claude_code/` | Sin código -- 2-3 ejemplos documentados de este mismo repo (`AGENTS.md` vs. hook vs. rule con `paths:` scoped). |
