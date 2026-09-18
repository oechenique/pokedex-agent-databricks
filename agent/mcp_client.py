"""Cliente MCP contra el pokedex-mcp-server real (Databricks App), no un
mock (reglas/03-agente-mcp.md). Conexión streamable-http autenticada con el
mismo perfil OAuth de `databricks auth login` que ya usa el resto del
proyecto -- reglas/07-estado-actual.md: el token de `az login`/Terraform no
sirve para pegarle a una Databricks App, hace falta el OIDC nativo del
propio workspace, que es lo que `Config(host=<app_url>).authenticate()`
resuelve (mismo mecanismo que `databricks auth token --host <app-url>`).
"""

from contextlib import AsyncExitStack
from typing import Any, Optional

from databricks.sdk.core import Config
from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client
from mcp.types import CallToolResult, Tool

import config


class PokedexMCPClient:
    def __init__(self) -> None:
        self._stack: Optional[AsyncExitStack] = None
        self.session: Optional[ClientSession] = None

    async def __aenter__(self) -> "PokedexMCPClient":
        self._stack = AsyncExitStack()
        headers = self._auth_headers()
        http_client = await self._stack.enter_async_context(create_mcp_http_client(headers=headers))
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
        cfg = Config(profile=config.DATABRICKS_PROFILE, host=config.MCP_SERVER_URL)
        return cfg.authenticate()

    async def list_tools(self) -> list[Tool]:
        assert self.session is not None
        result = await self.session.list_tools()
        return result.tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> CallToolResult:
        assert self.session is not None
        return await self.session.call_tool(name, arguments)
