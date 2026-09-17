/*
Sube el cliente de PokeAPI como Workspace File y los 5 notebooks Bronze
al workspace -- mismo patrón que asesor-turismo-databricks/terraform/notebooks.tf:
wrappers finos que importan código ya escrito, no reimplementan lógica acá.

No se usa Databricks Repos (Git) porque este repo todavía no tiene
remoto -- eso queda para una fase posterior. `databricks_workspace_file`
sube el contenido directo desde disco local.
*/

locals {
  workspace_root = "/Shared/${var.project_prefix}"
}

# Carpeta compartida creada explícitamente antes de subir ningún archivo:
# dejar que cada recurso cree su propia carpeta padre implícitamente los
# lanza a todos en paralelo y pisan la creación del mismo directorio a la
# vez ("The parent folder does not exist" para el que pierde la carrera).
resource "databricks_directory" "shared_root" {
  path       = local.workspace_root
  depends_on = [azurerm_databricks_workspace.this]
}

resource "databricks_directory" "notebooks" {
  path       = "${local.workspace_root}/notebooks"
  depends_on = [databricks_directory.shared_root]
}

resource "databricks_workspace_file" "pokeapi_client" {
  path       = "${local.workspace_root}/pokeapi_client.py"
  source     = "${path.module}/../ingestion/pokeapi_client.py"
  depends_on = [databricks_directory.shared_root]
}

resource "databricks_notebook" "bronze_pokemon_api" {
  path       = "${local.workspace_root}/notebooks/bronze_pokemon_api"
  source     = "${path.module}/notebooks/bronze_pokemon_api.py"
  depends_on = [databricks_directory.notebooks, databricks_workspace_file.pokeapi_client]
}

resource "databricks_notebook" "bronze_species" {
  path       = "${local.workspace_root}/notebooks/bronze_species"
  source     = "${path.module}/notebooks/bronze_species.py"
  depends_on = [databricks_directory.notebooks, databricks_workspace_file.pokeapi_client]
}

resource "databricks_notebook" "bronze_types" {
  path       = "${local.workspace_root}/notebooks/bronze_types"
  source     = "${path.module}/notebooks/bronze_types.py"
  depends_on = [databricks_directory.notebooks, databricks_workspace_file.pokeapi_client]
}

resource "databricks_notebook" "bronze_abilities" {
  path       = "${local.workspace_root}/notebooks/bronze_abilities"
  source     = "${path.module}/notebooks/bronze_abilities.py"
  depends_on = [databricks_directory.notebooks, databricks_workspace_file.pokeapi_client]
}

resource "databricks_notebook" "bronze_moves" {
  path       = "${local.workspace_root}/notebooks/bronze_moves"
  source     = "${path.module}/notebooks/bronze_moves.py"
  depends_on = [databricks_directory.notebooks, databricks_workspace_file.pokeapi_client]
}

resource "databricks_notebook" "silver" {
  path       = "${local.workspace_root}/notebooks/silver"
  source     = "${path.module}/notebooks/silver.py"
  depends_on = [databricks_directory.notebooks]
}

resource "databricks_notebook" "dq_check" {
  path       = "${local.workspace_root}/notebooks/dq_check"
  source     = "${path.module}/notebooks/dq_check.py"
  depends_on = [databricks_directory.notebooks]
}

resource "databricks_notebook" "gold" {
  path       = "${local.workspace_root}/notebooks/gold"
  source     = "${path.module}/notebooks/gold.py"
  depends_on = [databricks_directory.notebooks]
}
