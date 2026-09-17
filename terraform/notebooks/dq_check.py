# Databricks notebook source
# MAGIC %md
# MAGIC # Data Quality gate — Silver → Gold (reglas/01-datos-medallion.md)
# MAGIC Si CUALQUIER check falla, este notebook levanta una excepción real
# MAGIC (no un log, no un warning) -- el task queda `FAILED` y el task
# MAGIC `gold_aggregate` (que depende de este con la condición default
# MAGIC `ALL_SUCCESS` del job) nunca llega a correr. Gold no se actualiza con
# MAGIC datos sucios: el pipeline se frena acá, visiblemente, no en silencio.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "pokedex")
catalog_name = dbutils.widgets.get("catalog_name")

# COMMAND ----------

from pyspark.sql import functions as F

pokemon = spark.table(f"{catalog_name}.silver.pokemon")
stats = spark.table(f"{catalog_name}.silver.pokemon_stats")

checked = pokemon.join(stats, "pokemon_id", "left").select(
    "pokemon_id", "pokemon_name", "generation", "hp", "attack", "defense"
)

# COMMAND ----------

failures = []


def check(label, bad_count):
    if bad_count > 0:
        failures.append(f"{label}: {bad_count} fila(s) rota(s)")


check("pokemon_id IS NOT NULL", checked.filter(F.col("pokemon_id").isNull()).count())
check("pokemon_name IS NOT NULL", checked.filter(F.col("pokemon_name").isNull()).count())
check("attack >= 0", checked.filter((F.col("attack") < 0) | F.col("attack").isNull()).count())
check("defense >= 0", checked.filter((F.col("defense") < 0) | F.col("defense").isNull()).count())
check("hp > 0", checked.filter((F.col("hp") <= 0) | F.col("hp").isNull()).count())
check(
    "generation BETWEEN 1 AND 9",
    checked.filter(
        (F.col("generation") < 1) | (F.col("generation") > 9) | F.col("generation").isNull()
    ).count(),
)

duplicate_names = checked.groupBy("pokemon_name").count().filter("count > 1")
check("pokemon_name UNIQUE", duplicate_names.count())

# COMMAND ----------

if failures:
    detail = "\n".join(f"  - {f}" for f in failures)
    raise Exception(f"Data Quality gate FALLÓ -- Gold NO se actualiza.\n{detail}")

print(f"Data Quality gate OK -- {checked.count()} pokemon validados, 0 checks rotos.")
