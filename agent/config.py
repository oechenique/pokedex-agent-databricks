"""Config del agente -- todo por variable de entorno, nada hardcodeado
(reglas/05-guardrails-seguridad.md). Ver `.env.example` en la raíz del repo.
"""

import os
from pathlib import Path


def _load_dotenv() -> None:
    """Carga `.env` de la raíz del repo si existe, sin pisar variables ya
    seteadas en el entorno. Sin dependencia nueva (`python-dotenv`) para un
    parser de 3 líneas -- mismo criterio minimalista que `ingestion/pokeapi_client.py`."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if not value:
            continue
        os.environ.setdefault(key.strip(), value)


_load_dotenv()

ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")

# Perfil de `databricks auth login` (OAuth U2M) -- reglas/07-estado-actual.md:
# el token de `az login`/Terraform no sirve para pegarle a una Databricks App,
# hace falta el OIDC nativo del workspace. None = perfil DEFAULT de
# ~/.databrickscfg.
DATABRICKS_PROFILE = os.environ.get("DATABRICKS_PROFILE") or None

# Host del WORKSPACE (no el de la Databricks App) -- solo hace falta para
# el OAuth M2M en prod, donde no hay perfil: el endpoint de descubrimiento
# OIDC se resuelve contra este host, nunca contra MCP_SERVER_URL (ver
# mcp_client.py._auth_headers). None en local -- el perfil OAuth ya trae
# su propio host cacheado.
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST") or None

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL")
MCP_ENDPOINT_PATH = "/mcp"


def mcp_endpoint_url() -> str:
    if not MCP_SERVER_URL:
        raise RuntimeError(
            "Falta MCP_SERVER_URL -- URL de la Databricks App pokedex-mcp-server "
            "(`databricks apps get pokedex-mcp-server` -> campo url)."
        )
    return MCP_SERVER_URL.rstrip("/") + MCP_ENDPOINT_PATH
