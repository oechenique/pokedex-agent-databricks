"""Cliente MCP contra el pokedex-mcp-server real (Databricks App), no un
mock (reglas/03-agente-mcp.md). Conexión streamable-http autenticada con el
mismo perfil OAuth de `databricks auth login` que ya usa el resto del
proyecto -- reglas/07-estado-actual.md: el token de `az login`/Terraform no
sirve para pegarle a una Databricks App, hace falta el OIDC nativo del
propio workspace.

Auth vs. destino, dos hosts distintos (bug real en prod, 2026-09-20):
el host para CONSEGUIR el token OAuth M2M (client_id/secret) tiene que
ser el del WORKSPACE -- de ahí se resuelve el endpoint de descubrimiento
OIDC (`<host>/oidc/.well-known/oauth-authorization-server`). El host de
la Databricks App (MCP_SERVER_URL) no expone ese endpoint, así que
`Config(host=<app_url>).authenticate()` con client_id/secret fallaba en
Vercel. El token resultante SÍ se manda como `Authorization: Bearer` a
la URL de la app -- ese destino no cambia. Confirmado contra la doc
oficial: https://docs.databricks.com/gcp/en/dev-tools/databricks-apps/connect-local
Con perfil OAuth interactivo (uso local) esto no aplica: el perfil ya
trae su propio host cacheado en ~/.databrickscfg, por eso local sigue
andando con MCP_SERVER_URL como host de `Config` (ver `_auth_headers`).
"""

import os
from contextlib import AsyncExitStack
from typing import Any, Optional

import httpx2
from databricks.sdk.core import Config
from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client
from mcp.types import CallToolResult, Tool

import config

# Sin esto, create_mcp_http_client() no tiene timeout y un cuelgue de red
# (Databricks App dormida/redeployando) deja el request colgado en
# silencio en vez de fallar -- nos costó 15 min de diagnóstico en prod
# contra pokedex-agent-databricks.vercel.app (2026-09-20) distinguir eso
# de un error de auth M2M. connect=5s (dar margen al cold start de la
# app), read=15s (una tool_call real contra el SQL warehouse serverless).
# mcp>=2.1.1 usa httpx2 (sucesor de httpx), no el httpx clásico -- es lo
# que espera el parámetro timeout de create_mcp_http_client.
_HTTP_TIMEOUT = httpx2.Timeout(15.0, connect=5.0)


async def _log_error_response(response: httpx2.Response) -> None:
    # DEBUG TEMPORAL (2026-09-20) -- sacar apenas se resuelva el 500 en prod.
    # mcp.client.streamable_http descarta el body real de cualquier
    # respuesta >=400 que no sea un JSON-RPC error válido (ver su
    # _handle_request) y la reemplaza por un ErrorData genérico -- por eso
    # un try/except alrededor de session.initialize() no alcanza, la
    # excepción que llega a este código ya nació sin el body real. Este
    # hook de httpx2 intercepta la respuesta cruda ANTES de que la
    # librería mcp la toque.
    if response.status_code >= 400:
        await response.aread()
        print(
            f"DEBUG mcp http error status={response.status_code} "
            f"url={response.request.url} "
            f"headers={dict(response.headers)!r} "
            f"body={response.text[:2000]!r}"
        )


class PokedexMCPClient:
    def __init__(self) -> None:
        self._stack: Optional[AsyncExitStack] = None
        self.session: Optional[ClientSession] = None

    async def __aenter__(self) -> "PokedexMCPClient":
        self._stack = AsyncExitStack()
        headers = self._auth_headers()
        http_client = await self._stack.enter_async_context(
            create_mcp_http_client(headers=headers, timeout=_HTTP_TIMEOUT)
        )
        http_client.event_hooks.setdefault("response", []).append(_log_error_response)
        read, write = await self._stack.enter_async_context(
            streamable_http_client(config.mcp_endpoint_url(), http_client=http_client)
        )
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        assert self._stack is not None
        await self._stack.aclose()

    @staticmethod
    def _auth_headers() -> dict[str, str]:
        # DEBUG TEMPORAL (2026-09-20) -- sacar apenas se resuelva el 500 en
        # prod. config.py no expone DATABRICKS_CLIENT_ID/SECRET como
        # atributos (el SDK los lee de env por su cuenta, ver docstring de
        # este archivo), así que se leen directo de os.environ acá solo
        # para este log. Nunca el valor completo -- largo + primeros/
        # últimos 4 chars con !r para que un \n o espacio de más se vea
        # literal en vez de como salto de línea invisible.
        _cid = os.environ.get("DATABRICKS_CLIENT_ID")
        _secret = os.environ.get("DATABRICKS_CLIENT_SECRET")
        if _cid:
            print(f"DEBUG client_id len={len(_cid)} repr={_cid[:4]!r}...{_cid[-4:]!r}")
        else:
            print("DEBUG client_id UNSET")
        if _secret:
            print(f"DEBUG secret len={len(_secret)} repr={_secret[:4]!r}...{_secret[-4:]!r}")
        else:
            print("DEBUG secret UNSET")

        # DATABRICKS_HOST (workspace) solo hace falta para resolver el OIDC
        # del OAuth M2M en prod -- sin perfil, cae acá. Con perfil OAuth
        # local, DATABRICKS_HOST no está seteado y se sigue usando
        # MCP_SERVER_URL como host, igual que siempre.
        auth_host = config.DATABRICKS_HOST or config.MCP_SERVER_URL
        cfg = Config(profile=config.DATABRICKS_PROFILE, host=auth_host)
        return cfg.authenticate()

    async def list_tools(self) -> list[Tool]:
        assert self.session is not None
        result = await self.session.list_tools()
        return result.tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> CallToolResult:
        assert self.session is not None
        return await self.session.call_tool(name, arguments)
