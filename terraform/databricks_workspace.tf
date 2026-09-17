resource "azurerm_databricks_workspace" "this" {
  name                        = "${var.project_prefix}-workspace"
  resource_group_name         = azurerm_resource_group.this.name
  location                    = azurerm_resource_group.this.location
  sku                         = var.databricks_sku # "premium" -- ver variables.tf
  managed_resource_group_name = "${var.project_prefix}-workspace-managed-rg"

  tags = merge(var.tags, { environment = var.environment })
}
