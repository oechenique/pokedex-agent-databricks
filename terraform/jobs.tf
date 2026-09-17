/*
Job pipeline: bronze (5 tasks en paralelo, independientes entre sí) ->
silver_transform (depende de las 5, aunque solo lee pokemon_api_raw y
pokemon_species_raw -- se deja depender de las 5 para no arrancar Silver
con Bronze a medio refrescar) -> dq_check (depende de silver_transform)
-> gold_aggregate (depende de dq_check).

Encadenamiento real, no cosmético: dq_check.py levanta una excepción si
algún check de reglas/01-datos-medallion.md falla, el task queda FAILED,
y como gold_aggregate depende de él con la condición default del job
(ALL_SUCCESS), ese task directamente no corre -- Gold nunca se
actualiza con datos que no pasaron el gate. Mismo patrón de "un job con
DAG interno" que asesor-turismo-databricks/terraform/job.tf.

Compute: serverless en las 8 tasks, mismo motivo que ya quedó documentado
en la Fase 1 de este archivo (CLOUD_PROVIDER_RESOURCE_STOCKOUT con
tamaños de VM clásicos).
*/

resource "databricks_job" "pipeline" {
  name = "${var.project_prefix}-pipeline"

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

  task {
    task_key = "silver_transform"
    notebook_task {
      notebook_path = databricks_notebook.silver.path
    }
    depends_on { task_key = "bronze_pokemon_api" }
    depends_on { task_key = "bronze_species" }
    depends_on { task_key = "bronze_types" }
    depends_on { task_key = "bronze_abilities" }
    depends_on { task_key = "bronze_moves" }
  }

  task {
    task_key = "dq_check"
    notebook_task {
      notebook_path = databricks_notebook.dq_check.path
    }
    depends_on { task_key = "silver_transform" }
  }

  task {
    task_key = "gold_aggregate"
    notebook_task {
      notebook_path = databricks_notebook.gold.path
    }
    depends_on { task_key = "dq_check" }
  }

  tags = merge(var.tags, { environment = var.environment })

  depends_on = [databricks_schema.bronze, databricks_schema.silver, databricks_schema.gold]
}
