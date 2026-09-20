variable "project_prefix" {
  description = "Prefijo para nombrar los recursos Azure y el catálogo Unity Catalog."
  type        = string
  default     = "pokedex"
}

variable "environment" {
  description = "Entorno de este deploy -- va en tags, no en nombres de recursos."
  type        = string
  default     = "demo"
}

variable "location" {
  description = "Región de Azure donde se crean todos los recursos (resource group, storage account, databricks workspace -- todos heredan esta location). westus3 por default: mismo valor que quedó validado en asesor-turismo-databricks tras CLOUD_PROVIDER_RESOURCE_STOCKOUT persistente en eastus2. El job de este proyecto usa compute serverless (jobs.tf), así que el stockout de tamaños de VM específicos no debería repetirse, pero se mantiene la región ya probada por las dudas."
  type        = string
  default     = "westus3"
}

variable "storage_replication_type" {
  description = "Replicación del Storage Account. LRS (la más barata) alcanza para un proyecto de portfolio -- no hace falta redundancia geográfica."
  type        = string
  default     = "LRS"
}

variable "databricks_sku" {
  description = "SKU del workspace de Databricks. Azure dejó de permitir crear workspaces nuevos en 'standard' desde abril de 2026 (DatabricksStandardSkuNotSupported) -- forzado a 'premium'."
  type        = string
  default     = "premium"
}

variable "catalog_name" {
  description = "Nombre del catálogo Unity Catalog que contiene los schemas bronze/silver/gold (reglas/01-datos-medallion.md)."
  type        = string
  default     = "pokedex"
}

variable "sql_warehouse_id" {
  description = "Id del SQL warehouse que consulta el MCP server (apps.tf). Es el 'Serverless Starter Warehouse' que la cuenta ya trae por default -- no lo gestiona este Terraform, por eso es variable y no un recurso databricks_sql_endpoint."
  type        = string
  default     = "e783d583f5b7768d"
}

variable "anthropic_api_key" {
  description = "API key de Anthropic para el agente de oak_app (Profesor Oak corriendo como Databricks App). Sensitive -- se pasa por terraform.tfvars (gitignored) o TF_VAR_anthropic_api_key, nunca hardcodeada ni commiteada (reglas/05-guardrails-seguridad.md). Termina en un databricks_secret, nunca en texto plano en app.yaml."
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Tags comunes para todos los recursos."
  type        = map(string)
  default = {
    proyecto = "pokedex-agent-databricks"
    origen   = "terraform"
  }
}
