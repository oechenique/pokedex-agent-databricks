/*
Databricks App para el MCP server (reglas/02-infra-terraform.md,
reglas/03-agente-mcp.md) -- sin Dockerfile, se sube app.py +
requirements.txt + app.yaml como Workspace Files y Databricks Apps corre
todo internamente.

sql_warehouse: reusa el "Serverless Starter Warehouse" que ya trae la
cuenta por default (no lo creamos nosotros por Terraform, por eso va
como variable en vez de un recurso databricks_sql_endpoint acá) -- mismo
warehouse que se usó para validar Fases 1 y 2. El resource block de abajo
se llama "sql_warehouse" porque mcp_server/app.yaml ya espera esa clave
exacta en `valueFrom` para inyectar DATABRICKS_WAREHOUSE_ID.

Permisos: el service principal de la app no hereda nada por default --
se le da USE_CATALOG en el catálogo y USE_SCHEMA + SELECT en el schema
gold nada más (nunca acceso a bronze/silver, las tools solo leen Gold).
*/

locals {
  mcp_server_dir   = "${path.module}/../mcp_server"
  mcp_server_files = toset(["app.py", "db.py", "tools.py", "requirements.txt", "app.yaml"])
}

resource "databricks_directory" "mcp_server" {
  path       = "${local.workspace_root}/mcp_server"
  depends_on = [databricks_directory.shared_root]
}

resource "databricks_workspace_file" "mcp_server" {
  for_each   = local.mcp_server_files
  path       = "${local.workspace_root}/mcp_server/${each.value}"
  source     = "${local.mcp_server_dir}/${each.value}"
  depends_on = [databricks_directory.mcp_server]
}

resource "databricks_app" "mcp_server" {
  name        = "${var.project_prefix}-mcp-server"
  description = "MCP server de solo lectura sobre gold.* -- reglas/03-agente-mcp.md"

  resources = [
    {
      name = "sql_warehouse"
      sql_warehouse = {
        id         = var.sql_warehouse_id
        permission = "CAN_USE"
      }
    }
  ]

  source_code_path = databricks_directory.mcp_server.path

  depends_on = [
    databricks_workspace_file.mcp_server,
  ]
}

/*
IMPORTANTE -- databricks_grants es autoritativo por securable completo,
no aditivo por principal (bug real 2026-09-20: un segundo
databricks_grants apuntando a este mismo catalog/schema desde
permissions.tf pisó silenciosamente el grant de acá, dejando al service
principal de la app sin USE_CATALOG y rompiendo el MCP server en
producción -- "INSUFFICIENT_PERMISSIONS" real en los logs de la app).
Todo grant sobre este catalog/schema tiene que vivir en ESTE resource,
un grant{} block por principal, nunca en un databricks_grants separado.
*/
resource "databricks_grants" "mcp_server_catalog" {
  catalog = databricks_catalog.this.name

  grant {
    principal  = databricks_app.mcp_server.service_principal_client_id
    privileges = ["USE_CATALOG"]
  }

  grant {
    principal  = databricks_service_principal.backend_m2m.application_id
    privileges = ["USE_CATALOG"]
  }
}

resource "databricks_grants" "mcp_server_gold_schema" {
  schema = "${databricks_catalog.this.name}.${databricks_schema.gold.name}"

  grant {
    principal  = databricks_app.mcp_server.service_principal_client_id
    privileges = ["USE_SCHEMA", "SELECT"]
  }

  grant {
    principal  = databricks_service_principal.backend_m2m.application_id
    privileges = ["USE_SCHEMA", "SELECT"]
  }
}
