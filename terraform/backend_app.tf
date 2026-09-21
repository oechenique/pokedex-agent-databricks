/*
App híbrida Node.js + Python (reglas/07-estado-actual.md, "Migración
Next.js a Databricks App"): reusa `pokedex-backend` -- ya en RUNNING,
cupo de apps del workspace ya al límite (3) -- en vez de crear una 4ta
app para el frontend. Mismo patrón sin Dockerfile que mcp_server/oak_app:
todo sube como Workspace Files, Databricks Apps lo corre internamente.

`package.json` en la RAÍZ de source_code_path (backend_app/, ver más
abajo) hace que la plataforma corra `npm install`/`npm run build` ADEMÁS
de `pip install -r requirements.txt` -- confirmado contra la doc oficial
antes de escribir esto (docs.databricks.com/dev-tools/databricks-apps/
deploy, sección de apps npm/híbridas). `npm start` (comando en app.yaml)
usa `concurrently` para levantar Next.js (puerto público) y
`python -m backend.app` (loopback 127.0.0.1:8000) en paralelo; Next.js
proxea /api/* al backend server-side (frontend/next.config.ts).

Esqueleto de validación primero -- confirmar que la home de Next.js y
`/api/chat` responden de punta a punta contra pokedex-mcp-server real,
ANTES de portar el resto de la UI (tarjetas, comparación, matchups,
día/noche, multi-agente -- ya existen en frontend/ pero se portan recién
cuando el esqueleto funcione).
*/

locals {
  repo_root_dir    = "${path.module}/.."
  backend_app_dir  = "${path.module}/../backend"
  frontend_app_dir = "${path.module}/../frontend"

  # app.yaml/package.json/requirements.txt van en la RAÍZ de
  # source_code_path (backend_app/), no adentro de backend/ ni de
  # frontend/ -- Databricks Apps los busca ahí, y "python -m backend.app"
  # necesita correr parado en esa raíz para que `backend` resuelva como
  # paquete (ver nota en backend/app.py).
  backend_app_pkg_files = toset(["__init__.py", "app.py", "rate_limit.py", "render.py", "serialize.py"])

  # frontend/ sube archivo por archivo, igual que backend/agent/mcp_server
  # -- NO node_modules/.next (Databricks Apps corre `npm install`/`npm run
  # build` solo, ver docstring de arriba), NO .env.local (ya no se usa,
  # el front pega a /api/chat con path relativo -- ver next.config.ts).
  frontend_root_files = toset([
    "package.json", "package-lock.json", "next.config.ts", "tsconfig.json", "eslint.config.mjs",
  ])
  frontend_public_files = toset(["file.svg", "globe.svg", "next.svg", "vercel.svg", "window.svg"])
  frontend_app_dir_files = toset([
    "favicon.ico", "globals.css", "layout.tsx", "page.module.css", "page.tsx",
    "theme-provider.tsx", "theme-toggle.module.css", "theme-toggle.tsx",
  ])
  frontend_components_files = toset([
    "chat-turn.module.css", "chat-turn.tsx",
    "compare-table.module.css", "compare-table.tsx",
    "oak-text.tsx",
    "pokemon-card.module.css", "pokemon-card.tsx",
    "stat-bar.module.css", "stat-bar.tsx",
    "type-badge.module.css", "type-badge.tsx",
    "type-matchups.module.css", "type-matchups.tsx",
  ])
  frontend_lib_files = toset(["api.ts", "type-colors.ts", "types.ts"])
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

resource "databricks_directory" "frontend_app" {
  path       = "${local.workspace_root}/backend_app/frontend"
  depends_on = [databricks_directory.backend_app]
}

resource "databricks_directory" "frontend_app_public" {
  path       = "${local.workspace_root}/backend_app/frontend/public"
  depends_on = [databricks_directory.frontend_app]
}

resource "databricks_directory" "frontend_app_src" {
  path       = "${local.workspace_root}/backend_app/frontend/src"
  depends_on = [databricks_directory.frontend_app]
}

resource "databricks_directory" "frontend_app_src_app" {
  path       = "${local.workspace_root}/backend_app/frontend/src/app"
  depends_on = [databricks_directory.frontend_app_src]
}

resource "databricks_directory" "frontend_app_src_components" {
  path       = "${local.workspace_root}/backend_app/frontend/src/components"
  depends_on = [databricks_directory.frontend_app_src]
}

resource "databricks_directory" "frontend_app_src_lib" {
  path       = "${local.workspace_root}/backend_app/frontend/src/lib"
  depends_on = [databricks_directory.frontend_app_src]
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

resource "databricks_workspace_file" "frontend_app_root" {
  for_each   = local.frontend_root_files
  path       = "${local.workspace_root}/backend_app/frontend/${each.value}"
  source     = "${local.frontend_app_dir}/${each.value}"
  depends_on = [databricks_directory.frontend_app]
}

resource "databricks_workspace_file" "frontend_app_public" {
  for_each   = local.frontend_public_files
  path       = "${local.workspace_root}/backend_app/frontend/public/${each.value}"
  source     = "${local.frontend_app_dir}/public/${each.value}"
  depends_on = [databricks_directory.frontend_app_public]
}

resource "databricks_workspace_file" "frontend_app_src_app" {
  for_each   = local.frontend_app_dir_files
  path       = "${local.workspace_root}/backend_app/frontend/src/app/${each.value}"
  source     = "${local.frontend_app_dir}/src/app/${each.value}"
  depends_on = [databricks_directory.frontend_app_src_app]
}

resource "databricks_workspace_file" "frontend_app_src_components" {
  for_each   = local.frontend_components_files
  path       = "${local.workspace_root}/backend_app/frontend/src/components/${each.value}"
  source     = "${local.frontend_app_dir}/src/components/${each.value}"
  depends_on = [databricks_directory.frontend_app_src_components]
}

resource "databricks_workspace_file" "frontend_app_src_lib" {
  for_each   = local.frontend_lib_files
  path       = "${local.workspace_root}/backend_app/frontend/src/lib/${each.value}"
  source     = "${local.frontend_app_dir}/src/lib/${each.value}"
  depends_on = [databricks_directory.frontend_app_src_lib]
}

resource "databricks_workspace_file" "backend_app_requirements" {
  path       = "${local.workspace_root}/backend_app/requirements.txt"
  source     = "${local.backend_app_dir}/requirements.txt"
  depends_on = [databricks_directory.backend_app]
}

# app.yaml y package.json viven en la RAÍZ del repo (ya no adentro de
# backend/) -- dejaron de ser backend-específicos cuando la app pasó a
# ser híbrida Next.js + FastAPI.
resource "databricks_workspace_file" "backend_app_hybrid_root" {
  for_each   = toset(["app.yaml", "package.json"])
  path       = "${local.workspace_root}/backend_app/${each.value}"
  source     = "${local.repo_root_dir}/${each.value}"
  depends_on = [databricks_directory.backend_app]
}

resource "databricks_app" "backend_app" {
  name        = "${var.project_prefix}-backend"
  description = "Next.js + backend FastAPI de Profesor Oak en una app híbrida -- llama a pokedex-mcp-server via auth app-to-app automática (reglas/07, Migración Next.js a Databricks App)."

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
    databricks_workspace_file.backend_app_requirements,
    databricks_workspace_file.backend_app_hybrid_root,
    databricks_workspace_file.frontend_app_root,
    databricks_workspace_file.frontend_app_public,
    databricks_workspace_file.frontend_app_src_app,
    databricks_workspace_file.frontend_app_src_components,
    databricks_workspace_file.frontend_app_src_lib,
  ]
}
