# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze — pokemon_types_raw (PokeAPI /type)
# MAGIC Tipos y sus relaciones de daño (double_damage_from, etc.) -- tal cual
# MAGIC viene, sin transformar (reglas/01-datos-medallion.md). Esta tabla es
# MAGIC la fuente de `pokemon_type_matchups` en Gold más adelante, pero ese
# MAGIC cálculo determinista vive en el pipeline Silver→Gold, no acá.

# COMMAND ----------

import sys

WORKSPACE_ROOT = "/Workspace/Shared/pokedex"
sys.path.append(WORKSPACE_ROOT)

from pokeapi_client import fetch_all_resource_urls, fetch_json  # noqa: E402

# COMMAND ----------

dbutils.widgets.text("catalog_name", "pokedex")
dbutils.widgets.text("base_url", "https://pokeapi.co/api/v2")
dbutils.widgets.text("limit", "0")
dbutils.widgets.text("process_date", "")

catalog_name = dbutils.widgets.get("catalog_name")
base_url = dbutils.widgets.get("base_url")
limit = int(dbutils.widgets.get("limit"))
process_date = dbutils.widgets.get("process_date") or None

# COMMAND ----------

import datetime as dt
import json

urls = fetch_all_resource_urls(f"{base_url}/type", limit=limit)
fetched_at = dt.datetime.utcnow().isoformat()

records = []
for url in urls:
    payload = fetch_json(url)
    records.append(
        {
            "id": payload.get("id"),
            "name": payload.get("name"),
            "raw_json": json.dumps(payload),
            "source_url": url,
            "fetched_at": fetched_at,
            "process_date": process_date or dt.date.today().isoformat(),
        }
    )

# COMMAND ----------

df = spark.createDataFrame(records)
df.write.format("delta").mode("overwrite").saveAsTable(f"{catalog_name}.bronze.pokemon_types_raw")
