/*
Job bronze_ingest: las 5 tasks Bronze corren en paralelo -- son
independientes entre sí (cada una pega a un endpoint distinto de PokeAPI
y escribe su propia tabla), no hay depends_on entre ellas.

Compute: serverless, sin job_cluster ni node_type_id -- mismo motivo que
asesor-turismo-databricks/terraform/job.tf: CLOUD_PROVIDER_RESOURCE_STOCKOUT
repetido con tamaños de VM clásicos. Como todas las tasks son
notebook_task, alcanza con no declarar job_cluster para que Databricks
resuelva serverless automáticamente.

catalog_name/base_url son parámetros del job (no hardcodeados en cada
notebook) para poder apuntar a otro catálogo o mirrorear la API sin tocar
código. `limit=0` trae el dataset completo -- subirlo a un número chico
(ej. 20) sirve para una corrida de prueba rápida sin esperar el pull
entero de PokeAPI.
*/

resource "databricks_job" "bronze_ingest" {
  name = "${var.project_prefix}-bronze-ingest"

  parameter {
    name    = "catalog_name"
    default = databricks_catalog.this.name
  }
  parameter {
    name    = "base_url"
    default = "https://pokeapi.co/api/v2"
  }
  parameter {
    name    = "limit"
    default = "0"
  }
  parameter {
    name    = "process_date"
    default = "" # vacío -> cada notebook usa la fecha de hoy
  }

  task {
    task_key = "bronze_pokemon_api"
    notebook_task {
      notebook_path = databricks_notebook.bronze_pokemon_api.path
    }
  }

  task {
    task_key = "bronze_species"
    notebook_task {
      notebook_path = databricks_notebook.bronze_species.path
    }
  }

  task {
    task_key = "bronze_types"
    notebook_task {
      notebook_path = databricks_notebook.bronze_types.path
    }
  }

  task {
    task_key = "bronze_abilities"
    notebook_task {
      notebook_path = databricks_notebook.bronze_abilities.path
    }
  }

  task {
    task_key = "bronze_moves"
    notebook_task {
      notebook_path = databricks_notebook.bronze_moves.path
    }
  }

  tags = merge(var.tags, { environment = var.environment })

  depends_on = [databricks_schema.bronze]
}
