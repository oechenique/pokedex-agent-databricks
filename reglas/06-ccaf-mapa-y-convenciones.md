# 06 — Mapa de aprendizaje CCA-F + convenciones de Claude Code

## Mapa: dominio del examen → pieza de este proyecto

| Dominio (peso) | Dónde se practica en el proyecto |
|---|---|
| Agentic Architecture & Orchestration (27%) | Contexto explícito coordinador→subagentes en la fase multi-agente (`03-agente-mcp.md`); paralelismo si se procesan varios pokemon a la vez |
| Claude Code Config & Workflows (20%) | CLAUDE.md/rules/skills de este mismo repo (ver tabla abajo); hooks pre/post tool; fork de sesión al probar dos personalidades de Profesor Oak |
| Prompt Engineering & Structured Output (20%) | Schemas de las tools, `tool_choice`, manejo de `null` en cartas sin precio, formato de salida por tipo de dato |
| Tool Design & MCP Integration (18%) | Diseño de las 5 tools granulares, `isError` vs error de protocolo, MCP server en Databricks Apps |
| Context Management & Reliability (15%) | Data Quality gate (nunca datos inválidos llegan al agente), separación Gold=verdad vs. prompt=redacción |

## `tests/` — casos reproducibles (carpeta del repo, no solo teoría)
```
tests/
├── tool_choice/         # forzar compare_pokemon vs. dejar "any"
├── tool_errors/         # simular isError=true, ver que el agente no lo trate como dato válido
├── hooks/                # generation="banana" bloqueado en PreToolUse
├── structured_output/    # pokemon sin carta TCG → card:null, nunca inventado
├── permissions/          # qué puede/no puede tocar el service principal del Databricks App
├── subagents/            # (fase 6) contexto pasado explícito entre Researcher/Analyst/Librarian
└── claude_code/          # ejemplos de qué va en CLAUDE.md vs rules vs hooks, con el propio repo de ejemplo
```
Cada carpeta = una pregunta tipo examen convertida en código que corre de verdad.

## Convenciones de Claude Code para este repo (para compartir con el equipo)

| Mecanismo | Repo (`./`) | Usuario (`~/.claude/`) |
|---|---|---|
| **CLAUDE.md** | Hechos siempre-vigentes del proyecto: estructura Bronze/Silver/Gold, comandos de Terraform, convención de nombres de tablas | Preferencias personales tuyas (ej. "resumime en bullets"), no se commitea |
| **`.claude/rules/`** (con `paths:`) | Ej.: regla scoped a `mcp_server/tools/**` — "toda tool valida el nombre del pokemon contra Gold antes de pegarle a la API externa" | Reglas personales que querés en cualquier repo |
| **Skills** | Procedimiento compartido: "cómo correr el pipeline Bronze→Gold local antes de un PR" | Tus skills personales reusables |
| **Hooks** | `PreToolUse`/`PostToolUse` de este proyecto (ver `03-agente-mcp.md`) — siempre en el repo, es enforcement del equipo | — |

> Nota: para el repo real usamos `AGENTS.md` (soporte nuevo, cross-tool); el `AGENTS.md` raíz reemplaza la instrucción manual de leer reglas/ en cada prompt. Para el examen CCA-F la terminología sigue siendo CLAUDE.md, no confundir uno con otro.

Regla de oro: si es específico de este proyecto y el equipo lo tiene que ver → repo. Si es tuyo y aplica a cualquier repo → `~/.claude/`, nunca se commitea.

## Cómo lo vamos a construir con Claude Code (para no quemar tokens de más)
Fases chicas y validadas una por una (mismo patrón que el asesor de turismo): Terraform+Bronze → Silver+Gold+DQ → MCP tools → agente+hooks → frontend → (opcional) multi-agente → `tests/`. Cada fase se cierra y valida antes de pasar a la siguiente, no se le tira todo el proyecto de una a Claude Code en un solo prompt.
