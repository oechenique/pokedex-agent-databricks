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

output "backend_m2m_client_id" {
  description = "DATABRICKS_CLIENT_ID del service principal M2M del backend (permissions.tf). No es secreto, pero solo tiene sentido junto al client_secret."
  value       = databricks_service_principal.backend_m2m.application_id
}

output "backend_m2m_client_secret" {
  description = "DATABRICKS_CLIENT_SECRET del service principal M2M del backend. Extraer a mano con `terraform output -raw backend_m2m_client_secret`, nunca commitear ni pegar en un archivo del repo."
  value       = databricks_service_principal_secret.backend_m2m.secret
  sensitive   = true
}
