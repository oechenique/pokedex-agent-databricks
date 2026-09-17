resource "azurerm_resource_group" "this" {
  name     = "${var.project_prefix}-rg"
  location = var.location

  tags = merge(var.tags, { environment = var.environment })
}
