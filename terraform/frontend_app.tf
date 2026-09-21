/*
Tercer intento de frontend real (reglas/07-estado-actual.md): Next.js
corriendo como Databricks App (server real via `output: "standalone"`,
no export estático), en vez de Vercel. Mismo patrón de auth app-to-app
que backend_app.tf hacia mcp_server -- WorkspaceClient()/token
automático del service principal propio de esta app, nada de M2M.

A diferencia de mcp_server/oak_app/backend_app (paquetes chicos de .py
subidos archivo por archivo con databricks_workspace_file), el build
standalone de Next.js trae node_modules (>1000 archivos) -- modelarlo
con un databricks_workspace_file por archivo no es viable. Los archivos
se suben en bulk con `databricks workspace import-dir` (CLI, fuera de
Terraform) ANTES de este apply; acá solo se registra la app apuntando a
ese path ya existente.
*/

resource "databricks_app" "frontend_app" {
  name        = "${var.project_prefix}-web"
  description = "Next.js standalone corriendo como Databricks App -- llama a pokedex-backend via auth app-to-app automática (reglas/07, tercer intento de frontend real)."

  source_code_path = "${local.workspace_root}/frontend_app"
}

/*
IMPORTANTE -- igual que permissions.tf, databricks_permissions es
autoritativo por app_name completo. Este es un resource nuevo (no el de
permissions.tf, que es para pokedex-mcp-server) porque el objeto target
acá es pokedex-backend, no pokedex-mcp-server.
*/
resource "databricks_permissions" "backend_app_use" {
  app_name = databricks_app.backend_app.name

  access_control {
    service_principal_name = databricks_app.frontend_app.service_principal_client_id
    permission_level       = "CAN_USE"
  }
}
