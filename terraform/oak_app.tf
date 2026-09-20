/*
Segunda Databricks App: frontend Streamlit de Profesor Oak
(reglas/07-estado-actual.md -- reemplaza el deploy a Vercel, bloqueado
por un 401 de propagación M2M del lado de Databricks). Mismo patrón sin
Dockerfile que mcp_server (apps.tf): app.py + requirements.txt +
app.yaml como Workspace Files.

Esqueleto mínimo validado primero (un solo botón, auth app-to-app
automática con WorkspaceClient() sin credenciales explícitas) ANTES de
portar el resto -- ver historial en reglas/07-estado-actual.md. Ahora
además de app.py se suben render.py/serialize.py (copias de backend/,
mismo contrato) y TODO agent/ como subdirectorio propio -- Databricks
Apps solo ve lo que vive bajo source_code_path, así que agent/ no viaja
gratis como en Vercel (Root Directory = raíz del repo); acá hay que
subirlo explícito a oak_app/agent/ en el workspace, y app.py agrega esa
ruta relativa a sys.path (mismo patrón que backend/app.py, pero con
paths distintos porque el árbol deployado es distinto).

El permiso CAN_USE de este SP sobre pokedex-mcp-server vive en
permissions.tf, en el MISMO databricks_permissions que ya tiene
backend_m2m -- nunca un databricks_permissions separado apuntando al
mismo app_name (mismo error que el de databricks_grants, ver apps.tf).
*/

locals {
  oak_app_dir   = "${path.module}/../oak_app"
  oak_app_files = toset(["app.py", "render.py", "serialize.py", "requirements.txt", "app.yaml"])

  agent_dir   = "${path.module}/../agent"
  agent_files = toset(["agent.py", "hooks.py", "tool_choice.py", "system_prompt.py", "mcp_client.py", "config.py"])
}

resource "databricks_directory" "oak_app" {
  path       = "${local.workspace_root}/oak_app"
  depends_on = [databricks_directory.shared_root]
}

resource "databricks_directory" "oak_app_agent" {
  path       = "${local.workspace_root}/oak_app/agent"
  depends_on = [databricks_directory.oak_app]
}

resource "databricks_workspace_file" "oak_app" {
  for_each   = local.oak_app_files
  path       = "${local.workspace_root}/oak_app/${each.value}"
  source     = "${local.oak_app_dir}/${each.value}"
  depends_on = [databricks_directory.oak_app]
}

resource "databricks_workspace_file" "oak_app_agent" {
  for_each   = local.agent_files
  path       = "${local.workspace_root}/oak_app/agent/${each.value}"
  source     = "${local.agent_dir}/${each.value}"
  depends_on = [databricks_directory.oak_app_agent]
}

/*
ANTHROPIC_API_KEY -- primer intento del skeleton no la seteaba y
anthropic.Anthropic() falló en vivo ("Could not resolve authentication
method"). Nunca texto plano en app.yaml (reglas/05-guardrails-
seguridad.md): va a un databricks_secret, e igual que
DATABRICKS_WAREHOUSE_ID en mcp_server (apps.tf), se inyecta vía el
resource block "anthropic_api_key" + valueFrom en app.yaml.
*/
resource "databricks_secret_scope" "oak_app" {
  name = "${var.project_prefix}-oak-secrets"
}

resource "databricks_secret" "anthropic_api_key" {
  scope        = databricks_secret_scope.oak_app.name
  key          = "anthropic_api_key"
  string_value = var.anthropic_api_key
}

resource "databricks_app" "oak_frontend" {
  name        = "${var.project_prefix}-oak"
  description = "Frontend Streamlit de Profesor Oak -- llama a pokedex-mcp-server via auth app-to-app automática."

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

  source_code_path = databricks_directory.oak_app.path

  depends_on = [
    databricks_workspace_file.oak_app,
    databricks_workspace_file.oak_app_agent,
  ]
}
