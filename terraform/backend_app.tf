/*
Segundo intento de frontend real (reglas/07-estado-actual.md): backend
FastAPI corriendo como Databricks App en vez de Vercel serverless.
Mismo patrón sin Dockerfile que mcp_server/oak_app.tf: backend/*.py +
agent/*.py como subdirectorios propios (Databricks Apps no bundlea el
resto del repo como Vercel), auth app-to-app automática (WorkspaceClient()
sin credenciales explícitas -- el mismo mecanismo ya validado en
oak_app, no M2M).

Esqueleto de validación primero -- confirmar que backend/app.py, sin
tocar su lógica, autentica solo contra pokedex-mcp-server corriendo
acá, ANTES de portar el resto de frontend/ (reglas/07).
*/

locals {
  backend_app_dir = "${path.module}/../backend"
  # app.yaml/requirements.txt NO van acá -- Databricks Apps los busca en
  # la raíz de source_code_path (backend_app/), no adentro del paquete
  # backend/ (ver databricks_workspace_file.backend_app_root_config).
  backend_app_pkg_files = toset(["__init__.py", "app.py", "rate_limit.py", "render.py", "serialize.py"])
}

resource "databricks_directory" "backend_app" {
  path       = "${local.workspace_root}/backend_app"
  depends_on = [databricks_directory.shared_root]
}

resource "databricks_directory" "backend_app_pkg" {
  path       = "${local.workspace_root}/backend_app/backend"
  depends_on = [databricks_directory.backend_app]
}

resource "databricks_directory" "backend_app_agent" {
  path       = "${local.workspace_root}/backend_app/agent"
  depends_on = [databricks_directory.backend_app]
}

resource "databricks_workspace_file" "backend_app_pkg" {
  for_each   = local.backend_app_pkg_files
  path       = "${local.workspace_root}/backend_app/backend/${each.value}"
  source     = "${local.backend_app_dir}/${each.value}"
  depends_on = [databricks_directory.backend_app_pkg]
}

resource "databricks_workspace_file" "backend_app_agent" {
  for_each = toset([
    "agent.py", "hooks.py", "tool_choice.py", "system_prompt.py",
    "mcp_client.py", "config.py", "orchestrator.py", "subagents.py",
  ])
  path       = "${local.workspace_root}/backend_app/agent/${each.value}"
  source     = "${path.module}/../agent/${each.value}"
  depends_on = [databricks_directory.backend_app_agent]
}

# app.yaml/requirements.txt van en la RAÍZ de source_code_path
# (backend_app/), no adentro de backend/ -- Databricks Apps los busca
# ahí, y "python -m backend.app" necesita correr parado en esa raíz para
# que `backend` resuelva como paquete (ver nota en backend/app.py).
resource "databricks_workspace_file" "backend_app_root_config" {
  for_each   = toset(["app.yaml", "requirements.txt"])
  path       = "${local.workspace_root}/backend_app/${each.value}"
  source     = "${local.backend_app_dir}/${each.value}"
  depends_on = [databricks_directory.backend_app]
}

resource "databricks_app" "backend_app" {
  name        = "${var.project_prefix}-backend"
  description = "Backend FastAPI de Profesor Oak -- llama a pokedex-mcp-server via auth app-to-app automática (reglas/07, segundo intento de frontend real)."

  # Mismo databricks_secret que ya usa oak_app (oak_app.tf) -- un secret
  # no es exclusivo de una app, se puede referenciar desde varias.
  resources = [
    {
      name = "anthropic_api_key"
      secret = {
        scope      = databricks_secret_scope.oak_app.name
        key        = databricks_secret.anthropic_api_key.key
        permission = "READ"
      }
    }
  ]

  source_code_path = databricks_directory.backend_app.path

  depends_on = [
    databricks_workspace_file.backend_app_pkg,
    databricks_workspace_file.backend_app_agent,
    databricks_workspace_file.backend_app_root_config,
  ]
}
