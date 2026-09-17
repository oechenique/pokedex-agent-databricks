output "resource_group_name" {
  value = azurerm_resource_group.this.name
}

output "databricks_workspace_url" {
  value = azurerm_databricks_workspace.this.workspace_url
}

output "storage_account_name" {
  value = azurerm_storage_account.this.name
}

output "catalog_name" {
  value = databricks_catalog.this.name
}

output "pipeline_job_id" {
  description = "Para correr el pipeline completo: databricks jobs run-now --job-id <este id>"
  value       = databricks_job.pipeline.id
}
