/*
Segunda Databricks App: frontend Streamlit de Profesor Oak
(reglas/07-estado-actual.md -- reemplaza el deploy a Vercel, bloqueado
por un 401 de propagación M2M del lado de Databricks). Mismo patrón sin
Dockerfile que mcp_server (apps.tf): app.py + requirements.txt +
app.yaml como Workspace Files.

Esqueleto mínimo primero (oak_app/app.py, un solo botón) para validar
que la auth app-to-app automática (WorkspaceClient() sin credenciales
explícitas, service principal propio de esta app inyectado por la
plataforma) funciona contra pokedex-mcp-server -- ANTES de portar el
resto de agent/ y la UI completa.

El permiso CAN_USE de este SP sobre pokedex-mcp-server vive en
permissions.tf, en el MISMO databricks_permissions que ya tiene
backend_m2m -- nunca un databricks_permissions separado apuntando al
mismo app_name (mismo error que el de databricks_grants, ver apps.tf).
*/

locals {
  oak_app_dir   = "${path.module}/../oak_app"
  oak_app_files = toset(["app.py", "requirements.txt", "app.yaml"])
}

resource "databricks_directory" "oak_app" {
  path       = "${local.workspace_root}/oak_app"
  depends_on = [databricks_directory.shared_root]
}

resource "databricks_workspace_file" "oak_app" {
  for_each   = local.oak_app_files
  path       = "${local.workspace_root}/oak_app/${each.value}"
  source     = "${local.oak_app_dir}/${each.value}"
  depends_on = [databricks_directory.oak_app]
}

resource "databricks_app" "oak_frontend" {
  name        = "${var.project_prefix}-oak"
  description = "Frontend Streamlit de Profesor Oak -- llama a pokedex-mcp-server via auth app-to-app automática."

  source_code_path = databricks_directory.oak_app.path

  depends_on = [
    databricks_workspace_file.oak_app,
  ]
}
