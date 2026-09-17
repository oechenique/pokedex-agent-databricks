/*
Unity Catalog: catálogo "pokedex" + schemas bronze/silver/gold
(reglas/01-datos-medallion.md, reglas/02-infra-terraform.md).

storage_root apunta a la External Location creada en
unity_catalog_storage.tf -- el metastore de esta cuenta tiene "Default
Storage" sin root URL propio, así que el catálogo necesita su managed
location explícita (confirmado con el error real del primer apply, ver
comentario en unity_catalog_storage.tf).
*/

resource "databricks_catalog" "this" {
  name         = var.catalog_name
  comment      = "Plataforma de datos Pokémon -- Bronze/Silver/Gold (reglas/01-datos-medallion.md)."
  storage_root = databricks_external_location.unity_catalog_root.url

  depends_on = [databricks_external_location.unity_catalog_root]
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
