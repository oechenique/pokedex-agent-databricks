"""Dominio: permissions (reglas/06-ccaf-mapa-y-convenciones.md).
Confirma en vivo el límite real de Unity Catalog para el service
principal que corre oak_app: SELECT sobre gold sí, bronze/silver no.

No podemos autenticar como el service principal DE oak_app desde afuera
de su propio contenedor -- Databricks Apps solo inyecta esas
credenciales dentro del proceso de la app (reglas/07-estado-actual.md,
"auth app-to-app"). Este test usa backend_m2m en su lugar: mismo perfil
de permisos exacto sobre datos (USE_CATALOG + gold USE_SCHEMA/SELECT,
nada en bronze/silver -- ver terraform/apps.tf, un único
databricks_grants por securable). La query SQL y el error son 100%
reales contra el warehouse real, no un mock.
"""

import subprocess
from pathlib import Path

import pytest
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

# Ruta calculada localmente (no importada de conftest.py) -- conftest no
# es un módulo confiable de importar desde un subdirectorio de tests/,
# pytest lo carga de forma especial, no como paquete normal.
TERRAFORM_DIR = Path(__file__).resolve().parent.parent.parent / "terraform"

WORKSPACE_HOST = "https://adb-7405616363788532.12.azuredatabricks.net"
SQL_WAREHOUSE_ID = "e783d583f5b7768d"
CATALOG = "pokedex"


def _tf_output(name: str) -> str:
    out = subprocess.run(
        ["terraform", "output", "-raw", name],
        cwd=TERRAFORM_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


@pytest.fixture(scope="module")
def restricted_client() -> WorkspaceClient:
    return WorkspaceClient(
        host=WORKSPACE_HOST,
        client_id=_tf_output("backend_m2m_client_id"),
        client_secret=_tf_output("backend_m2m_client_secret"),
    )


def test_select_sobre_gold_permitido(restricted_client: WorkspaceClient):
    resp = restricted_client.statement_execution.execute_statement(
        warehouse_id=SQL_WAREHOUSE_ID,
        statement="SELECT 1 AS ok FROM pokemon_profile LIMIT 1",
        catalog=CATALOG,
        schema="gold",
        wait_timeout="30s",
    )
    assert resp.status.state == StatementState.SUCCEEDED


@pytest.mark.parametrize(
    "schema,table",
    [("bronze", "pokemon_api_raw"), ("silver", "pokemon")],
)
def test_select_sobre_bronze_silver_rechazado(restricted_client: WorkspaceClient, schema: str, table: str):
    resp = restricted_client.statement_execution.execute_statement(
        warehouse_id=SQL_WAREHOUSE_ID,
        statement=f"SELECT 1 FROM {table} LIMIT 1",
        catalog=CATALOG,
        schema=schema,
        wait_timeout="30s",
    )
    assert resp.status.state == StatementState.FAILED
    assert "INSUFFICIENT_PERMISSIONS" in (resp.status.error.message or "")
