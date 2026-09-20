"""Fixtures compartidos para tests/ (reglas/06-ccaf-mapa-y-convenciones.md).

Agrega agent/ al sys.path -- mismo patrón que agent/cli.py, backend/app.py
y oak_app/app.py -- para poder importar config, agent, hooks, mcp_client,
tool_choice, orchestrator y subagents TAL CUAL están deployados, no una
copia para test.

Todos los tests de esta suite corren contra el sistema real (MCP server
`pokedex-mcp-server` y, donde aplica, el agente real vía la API de
Claude) -- nunca contra un mock. Auth local: perfil OAuth de
`databricks auth login` vía .env (DATABRICKS_PROFILE), igual que
`agent/cli.py` -- correr `cp .env.example .env` y completar antes de
correr la suite (ver README.md, "Cómo correr todo").
"""

import sys
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
sys.path.insert(0, str(AGENT_DIR))
