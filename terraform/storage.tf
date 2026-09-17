/*
ADLS Gen2 -- Storage Account con jerarquía habilitada (is_hns_enabled) +
containers bronze/silver/gold, tal como pide reglas/02-infra-terraform.md.

Fase 1: estos containers quedan disponibles como destino de blob storage
"que sobrevive" cuando se acabe el workspace pago (mismo punto que marca
esa regla), pero las tablas Bronze de esta fase se escriben como tablas
gestionadas de Unity Catalog (catalog.tf), no como external tables sobre
estos containers -- igual que la simplificación documentada en
asesor-turismo-databricks/terraform/notebooks/bronze_clima.py: conectar
serverless compute a ADLS Gen2 vía Unity Catalog Storage Credentials +
Access Connector es trabajo de infraestructura aparte, no bloquea tener
el dataset Bronze ya curado y a salvo en Delta.

El nombre del Storage Account tiene que ser único en TODO Azure -- se le
agrega un sufijo random para evitar choques.
*/

resource "random_string" "storage_suffix" {
  length  = 6
  special = false
  upper   = false
  numeric = true
}

resource "azurerm_storage_account" "this" {
  name                     = "${replace(var.project_prefix, "-", "")}${random_string.storage_suffix.result}"
  resource_group_name      = azurerm_resource_group.this.name
  location                 = azurerm_resource_group.this.location
  account_tier             = "Standard"
  account_replication_type = var.storage_replication_type
  is_hns_enabled           = true # ADLS Gen2

  tags = merge(var.tags, { environment = var.environment })
}

resource "azurerm_storage_container" "bronze" {
  name                  = "bronze"
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "silver" {
  name                  = "silver"
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "gold" {
  name                  = "gold"
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"
}

# Container dedicado a la managed storage de Unity Catalog (ver
# unity_catalog_storage.tf) -- separado de bronze/silver/gold de arriba,
# que quedan libres para el export/backup plano mencionado en
# reglas/02-infra-terraform.md, sin mezclarlo con los archivos internos
# que Unity Catalog gestiona bajo su storage root.
resource "azurerm_storage_container" "unity_catalog" {
  name                  = "unity-catalog"
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"
}
