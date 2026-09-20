/*
Service principal M2M para el backend FastAPI en producción
(reglas/02-infra-terraform.md, reglas/07-estado-actual.md -- "Service
principal M2M + deploy real a Vercel").

`databricks auth login` (OAuth interactivo, usado hoy por mcp_client.py)
no sirve en un entorno serverless headless como Vercel -- hace falta un
service principal propio con OAuth client credentials (M2M).

Permisos: exactamente los mismos que ya tiene el service principal de la
Databricks App (ver apps.tf) -- USE_CATALOG en el catálogo y USE_SCHEMA +
SELECT en gold nada más. Nunca acceso a bronze/silver.

El client_secret nunca se escribe a un archivo del repo: el resource
databricks_service_principal_secret lo expone como atributo sensible, y
el output de abajo lo vuelve a marcar sensitive = true. Se extrae a mano
con `terraform output -raw backend_m2m_client_secret` después del apply.
*/

resource "databricks_service_principal" "backend_m2m" {
  display_name = "${var.project_prefix}-backend-m2m"
  active       = true
}

resource "databricks_service_principal_secret" "backend_m2m" {
  service_principal_id = databricks_service_principal.backend_m2m.id
}

resource "databricks_grants" "backend_m2m_catalog" {
  catalog = databricks_catalog.this.name

  grant {
    principal  = databricks_service_principal.backend_m2m.application_id
    privileges = ["USE_CATALOG"]
  }
}

resource "databricks_grants" "backend_m2m_gold_schema" {
  schema = "${databricks_catalog.this.name}.${databricks_schema.gold.name}"

  grant {
    principal  = databricks_service_principal.backend_m2m.application_id
    privileges = ["USE_SCHEMA", "SELECT"]
  }
}
