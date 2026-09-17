"""Cliente Databricks SQL para las tools del MCP server.

Usa la Statement Execution API vía `databricks-sdk` (no
`databricks-sql-connector`/ODBC) -- misma auth que Terraform y el CLI en
las fases anteriores: sesión de `az login` local, identidad de la propia
app cuando esto corre como Databricks App. `WorkspaceClient()` la resuelve
sola con `DATABRICKS_HOST` seteado, sin credenciales hardcodeadas acá.

Todas las queries son parametrizadas -- `pokemon`/`query`/`type` llegan
como texto libre desde el agente, nunca se arma la sentencia con
f-strings sobre esos valores.
"""

import os
from typing import Any

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementParameterListItem, StatementState

CATALOG = os.environ.get("DATABRICKS_CATALOG", "pokedex")

_client: WorkspaceClient | None = None


def _get_client() -> WorkspaceClient:
    global _client
    if _client is None:
        _client = WorkspaceClient()
    return _client


def _warehouse_id() -> str:
    warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID")
    if not warehouse_id:
        raise RuntimeError(
            "Falta DATABRICKS_WAREHOUSE_ID -- ver app.yaml (resource del SQL warehouse)."
        )
    return warehouse_id


def run_query(
    statement: str,
    schema: str,
    parameters: dict[str, tuple[Any, str]] | None = None,
) -> list[dict[str, Any]]:
    """Corre una query parametrizada contra Unity Catalog y devuelve las
    filas como dicts column_name -> valor (todo viene como string desde la
    API; cada tool castea lo que necesita).

    `parameters` mapea nombre -> (valor, tipo_sql) para los placeholders
    `:nombre` del `statement` (ej. {"pokemon": ("pikachu", "STRING")}).
    """
    client = _get_client()
    param_items = [
        StatementParameterListItem(name=name, value=str(value), type=sql_type)
        for name, (value, sql_type) in (parameters or {}).items()
    ]

    response = client.statement_execution.execute_statement(
        warehouse_id=_warehouse_id(),
        statement=statement,
        catalog=CATALOG,
        schema=schema,
        parameters=param_items or None,
        wait_timeout="30s",
    )

    if response.status.state != StatementState.SUCCEEDED:
        error = response.status.error
        raise RuntimeError(f"Query falló ({response.status.state}): {error}")

    if response.manifest and response.manifest.total_chunk_count and response.manifest.total_chunk_count > 1:
        # Ninguna tool de esta fase debería generar resultados tan grandes
        # (un pokemon, <=25 resultados de búsqueda, <=21 filas de tipo) --
        # si esto dispara, mejor un error explícito que devolver una
        # página parcial en silencio.
        raise RuntimeError("Resultado con múltiples chunks -- no implementado en esta fase.")

    if response.result is None or not response.result.data_array:
        return []

    columns = [c.name for c in response.manifest.schema.columns]
    return [dict(zip(columns, row)) for row in response.result.data_array]
