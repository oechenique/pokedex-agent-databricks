/*
Unity Catalog: catálogo "pokedex" + schemas bronze/silver/gold
(reglas/01-datos-medallion.md, reglas/02-infra-terraform.md).

No se define storage_root: se apoya en el metastore de Unity Catalog que
Azure Databricks asigna automáticamente a workspaces nuevos (managed
storage default). SI el `terraform apply` falla acá con algo del estilo
"no metastore assigned to workspace" / "UNAUTHORIZED" en
databricks_catalog, es porque esta suscripción/tenant todavía no tiene
metastore auto-asignado en la región elegida -- hay que asignarlo a mano
una vez (Databricks Account Console, nivel cuenta, no workspace) antes de
reintentar el apply. No lo pudimos confirmar de antemano porque requiere
un workspace real ya desplegado para verificarlo.
*/

resource "databricks_catalog" "this" {
  name    = var.catalog_name
  comment = "Plataforma de datos Pokémon -- Bronze/Silver/Gold (reglas/01-datos-medallion.md)."

  depends_on = [azurerm_databricks_workspace.this]
}

resource "databricks_schema" "bronze" {
  catalog_name = databricks_catalog.this.name
  name         = "bronze"
  comment      = "JSON crudo tal cual viene de las fuentes, sin transformar."
}

resource "databricks_schema" "silver" {
  catalog_name = databricks_catalog.this.name
  name         = "silver"
  comment      = "Datos normalizados, tipados y deduplicados."
}

resource "databricks_schema" "gold" {
  catalog_name = databricks_catalog.this.name
  name         = "gold"
  comment      = "Listo para el agente -- única capa que consultan las tools del MCP server."
}
