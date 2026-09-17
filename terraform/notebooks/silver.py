# Databricks notebook source
# MAGIC %md
# MAGIC # Silver — normalización desde Bronze (reglas/01-datos-medallion.md)
# MAGIC Aplana el JSON crudo de `pokemon_api_raw` en 5 tablas tipadas y
# MAGIC deduplicadas. `pokemon_species_raw` se usa solo para resolver
# MAGIC `generation` (ver nota más abajo) -- las tablas `pokemon_types_raw` /
# MAGIC `pokemon_abilities_raw` / `pokemon_moves_raw` de Bronze son el catálogo
# MAGIC GLOBAL de tipos/habilidades/movimientos (detalle, efectos, etc.), no la
# MAGIC relación pokemon↔tipo/habilidad/movimiento -- esa relación ya viene
# MAGIC embebida en el propio JSON de cada pokemon dentro de `pokemon_api_raw`,
# MAGIC así que se extrae de ahí directamente sin joinear contra esas tres
# MAGIC tablas de catálogo (que sí se usan más adelante en Gold, para los
# MAGIC matchups de tipo).
# MAGIC
# MAGIC **De dónde sale `generation`** (no viene en `pokemon_api_raw`): cada
# MAGIC pokemon referencia su especie (`species.url`, ej.
# MAGIC `.../pokemon-species/25/`) -- nunca asumir `species_id == pokemon_id`,
# MAGIC porque las formas alternativas (mega, gmax, regionales) tienen su
# MAGIC propio `pokemon_id` pero comparten especie con el pokemon base. Se
# MAGIC extrae el id de especie de esa URL y se joinea contra
# MAGIC `pokemon_species_raw`, que sí trae `generation.name` (ej.
# MAGIC `"generation-i"`). PokeAPI codifica la generación como numeral romano
# MAGIC en el nombre del recurso, no como entero -- se mapea a mano acá.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "pokedex")
catalog_name = dbutils.widgets.get("catalog_name")

# COMMAND ----------

from pyspark.sql import Window
from pyspark.sql import functions as F

bronze_pokemon = spark.table(f"{catalog_name}.bronze.pokemon_api_raw")
bronze_species = spark.table(f"{catalog_name}.bronze.pokemon_species_raw")

# Dedup por id quedándose con el fetched_at más reciente -- Bronze hoy
# corre en overwrite puro así que no debería haber duplicados, pero esto
# deja Silver correcto igual si algún día Bronze pasa a append.
dedup_pokemon = (
    bronze_pokemon.withColumn(
        "_rn", F.row_number().over(Window.partitionBy("id").orderBy(F.col("fetched_at").desc()))
    )
    .filter("_rn = 1")
    .drop("_rn")
)

dedup_species = (
    bronze_species.withColumn(
        "_rn", F.row_number().over(Window.partitionBy("id").orderBy(F.col("fetched_at").desc()))
    )
    .filter("_rn = 1")
    .drop("_rn")
)

# COMMAND ----------

# Schema tipado del JSON de /pokemon -- se parsea una sola vez y se reusa
# en las 5 tablas de abajo. sprite_url/artwork_url se extraen aparte con
# get_json_object (la clave "official-artwork" tiene un guion, más simple
# vía JSONPath con corchetes que peleando con backticks en la DDL).
pokemon_schema = """
    id INT,
    name STRING,
    height INT,
    weight INT,
    species STRUCT<name: STRING, url: STRING>,
    stats ARRAY<STRUCT<base_stat: INT, stat: STRUCT<name: STRING>>>,
    types ARRAY<STRUCT<slot: INT, type: STRUCT<name: STRING>>>,
    abilities ARRAY<STRUCT<slot: INT, is_hidden: BOOLEAN, ability: STRUCT<name: STRING>>>,
    moves ARRAY<STRUCT<
        move: STRUCT<name: STRING>,
        version_group_details: ARRAY<STRUCT<
            level_learned_at: INT,
            move_learn_method: STRUCT<name: STRING>
        >>
    >>
"""

pokemon_parsed = (
    dedup_pokemon.withColumn("payload", F.from_json("raw_json", pokemon_schema))
    .withColumn("sprite_url", F.get_json_object("raw_json", "$['sprites']['front_default']"))
    .withColumn(
        "artwork_url",
        F.get_json_object("raw_json", "$['sprites']['other']['official-artwork']['front_default']"),
    )
)

species_parsed = dedup_species.withColumn(
    "generation_name", F.get_json_object("raw_json", "$['generation']['name']")
).select(F.col("id").alias("species_id"), "generation_name")

# COMMAND ----------

generation_by_name = {
    "generation-i": 1,
    "generation-ii": 2,
    "generation-iii": 3,
    "generation-iv": 4,
    "generation-v": 5,
    "generation-vi": 6,
    "generation-vii": 7,
    "generation-viii": 8,
    "generation-ix": 9,
}
map_entries = []
for name, number in generation_by_name.items():
    map_entries += [F.lit(name), F.lit(number)]
roman_to_int = F.create_map(*map_entries)

species_with_generation = species_parsed.withColumn(
    "generation", roman_to_int[F.col("generation_name")]
).select("species_id", "generation")

pokemon_with_species_id = pokemon_parsed.withColumn(
    "species_id",
    F.regexp_extract(F.col("payload.species.url"), r"/pokemon-species/(\d+)/?$", 1).cast("int"),
)

# COMMAND ----------

# --- silver.pokemon ---
silver_pokemon = pokemon_with_species_id.join(species_with_generation, "species_id", "left").select(
    F.col("id").alias("pokemon_id"),
    F.col("name").alias("pokemon_name"),
    F.col("payload.height").cast("int").alias("height"),
    F.col("payload.weight").cast("int").alias("weight"),
    "sprite_url",
    "artwork_url",
    F.col("generation").cast("int").alias("generation"),
)

silver_pokemon.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{catalog_name}.silver.pokemon")

# COMMAND ----------

# --- silver.pokemon_stats ---
stats_exploded = pokemon_parsed.select(
    F.col("id").alias("pokemon_id"), F.explode("payload.stats").alias("stat_entry")
).select(
    "pokemon_id",
    F.regexp_replace(F.col("stat_entry.stat.name"), "-", "_").alias("stat_name"),
    F.col("stat_entry.base_stat").cast("int").alias("base_stat"),
)

silver_pokemon_stats = (
    stats_exploded.groupBy("pokemon_id")
    .pivot("stat_name", ["hp", "attack", "defense", "special_attack", "special_defense", "speed"])
    .agg(F.first("base_stat"))
    .select(
        "pokemon_id",
        F.col("hp").cast("int").alias("hp"),
        F.col("attack").cast("int").alias("attack"),
        F.col("defense").cast("int").alias("defense"),
        F.col("special_attack").cast("int").alias("special_attack"),
        F.col("special_defense").cast("int").alias("special_defense"),
        F.col("speed").cast("int").alias("speed"),
    )
)

silver_pokemon_stats.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{catalog_name}.silver.pokemon_stats")

# COMMAND ----------

# --- silver.pokemon_types --- (relación normalizada, no array embebido)
silver_pokemon_types = pokemon_parsed.select(
    F.col("id").alias("pokemon_id"), F.explode("payload.types").alias("type_entry")
).select(
    "pokemon_id",
    F.col("type_entry.slot").cast("int").alias("slot"),
    F.col("type_entry.type.name").alias("type_name"),
)

silver_pokemon_types.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{catalog_name}.silver.pokemon_types")

# COMMAND ----------

# --- silver.pokemon_abilities ---
silver_pokemon_abilities = pokemon_parsed.select(
    F.col("id").alias("pokemon_id"), F.explode("payload.abilities").alias("ability_entry")
).select(
    "pokemon_id",
    F.col("ability_entry.slot").cast("int").alias("slot"),
    F.col("ability_entry.ability.name").alias("ability_name"),
    F.col("ability_entry.is_hidden").alias("is_hidden"),
)

silver_pokemon_abilities.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{catalog_name}.silver.pokemon_abilities"
)

# COMMAND ----------

# --- silver.pokemon_moves ---
# Grain: (pokemon_id, move_name, learn_method). PokeAPI trackea el detalle
# por version_group (ej. "red-blue" vs "scarlet-violet"), pero esa
# granularidad de videojuego específico no aporta nada a un Pokedex --
# se colapsa quedándose con el level_learned_at mínimo visto en cualquier
# version_group para ese método de aprendizaje.
moves_exploded = pokemon_parsed.select(
    F.col("id").alias("pokemon_id"), F.explode("payload.moves").alias("move_entry")
).select(
    "pokemon_id",
    F.col("move_entry.move.name").alias("move_name"),
    F.explode("move_entry.version_group_details").alias("vgd"),
).select(
    "pokemon_id",
    "move_name",
    F.col("vgd.move_learn_method.name").alias("learn_method"),
    F.col("vgd.level_learned_at").cast("int").alias("level_learned_at"),
)

silver_pokemon_moves = moves_exploded.groupBy("pokemon_id", "move_name", "learn_method").agg(
    F.min("level_learned_at").alias("level_learned_at")
)

silver_pokemon_moves.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{catalog_name}.silver.pokemon_moves")
