/*
Fase 1 — providers.

Autenticación: sesión de `az login` activa localmente, igual que en
asesor-turismo-databricks (terraform/main.tf de ese repo). Sin service
principal ni secret adicional -- ni `azurerm` ni `databricks` reciben
client_id/client_secret acá, los dos reusan esa sesión de Azure CLI.

Versiones fijadas al mismo rango que asesor-turismo-databricks (ya
validado contra el Registry real en ese proyecto).
*/

terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.130"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {}
}

data "azurerm_client_config" "current" {}

# El provider databricks necesita atributos de azurerm_databricks_workspace
# (workspace_url, id) para autenticar -- dependencia implícita en el grafo
# de Terraform. Cada recurso databricks_* de este proyecto además tiene un
# depends_on explícito a azurerm_databricks_workspace.this (ver catalog.tf,
# notebooks.tf, jobs.tf) porque el provider suele intentar autenticar antes
# de que el workspace esté realmente listo para servir su API
# ("cannot configure default credentials") -- mismo patrón confirmado en
# asesor-turismo-databricks.
provider "databricks" {
  host                        = azurerm_databricks_workspace.this.workspace_url
  azure_workspace_resource_id = azurerm_databricks_workspace.this.id
}
