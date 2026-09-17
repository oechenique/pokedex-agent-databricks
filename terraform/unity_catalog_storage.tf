/*
El metastore de Unity Catalog de esta cuenta tiene "Default Storage"
habilitado pero SIN storage root URL propio -- el primer `terraform
apply` falló en databricks_catalog con:
  "Metastore storage root URL does not exist... please provide a storage
  location for the catalog (CREATE CATALOG ... MANAGED LOCATION ...)"
Esto significa que el catálogo necesita su propia managed location
explícita, no que falte asignar el metastore (eso ya estaba resuelto).

Cadena de recursos para que Unity Catalog pueda autenticarse contra el
container `unity-catalog` de storage.tf sin account keys (mismo patrón
"production" que asesor-turismo-databricks dejó pendiente en el comentario
de bronze_clima.py):
  Access Connector (identity administrada por Azure)
    -> Role Assignment (Storage Blob Data Contributor sobre el storage account)
    -> Storage Credential (Unity Catalog, respaldado por el Access Connector)
    -> External Location (URL abfss:// + la Storage Credential)
    -> databricks_catalog.storage_root (catalog.tf) apunta a esa External Location
*/

resource "azurerm_databricks_access_connector" "unity_catalog" {
  name                = "${var.project_prefix}-uc-access-connector"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location

  identity {
    type = "SystemAssigned"
  }

  tags = merge(var.tags, { environment = var.environment })
}

resource "azurerm_role_assignment" "unity_catalog_storage" {
  scope                = azurerm_storage_account.this.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.unity_catalog.identity[0].principal_id
}

# Azure RBAC tarda en propagar -- crear la Storage Credential enseguida
# después del role assignment suele fallar con 403 aunque el rol ya
# figure asignado en el portal. Un margen corto acá evita ese flake sin
# tener que reintentar el apply a mano.
resource "time_sleep" "role_propagation" {
  create_duration = "60s"

  depends_on = [azurerm_role_assignment.unity_catalog_storage]
}

resource "databricks_storage_credential" "unity_catalog" {
  name = "${var.project_prefix}-uc-storage-credential"

  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.unity_catalog.id
  }

  depends_on = [azurerm_databricks_workspace.this, time_sleep.role_propagation]
}

resource "databricks_external_location" "unity_catalog_root" {
  name            = "${var.project_prefix}-uc-root"
  url             = "abfss://unity-catalog@${azurerm_storage_account.this.name}.dfs.core.windows.net/"
  credential_name = databricks_storage_credential.unity_catalog.name

  depends_on = [
    azurerm_storage_container.unity_catalog,
    databricks_storage_credential.unity_catalog,
  ]
}
