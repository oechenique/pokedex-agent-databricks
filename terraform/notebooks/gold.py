# Databricks notebook source
# MAGIC %md
# MAGIC # Gold — única capa que las tools del agente van a consultar
# MAGIC (reglas/01-datos-medallion.md). Todo cálculo (totales, ratios,
# MAGIC matchups de tipo) se hace ACÁ, nunca en el prompt del agente -- el
# MAGIC agente lee el resultado ya calculado. Este notebook solo corre si
# MAGIC `dq_check` terminó OK (depends_on a nivel job).
# MAGIC
# MAGIC `tcg_cards` / `pokemon_card_summary` quedan afuera -- no ingerimos
# MAGIC pokemontcg.io todavía (Fase 1 fue solo PokeAPI).

# COMMAND ----------

dbutils.widgets.text("catalog_name", "pokedex")
catalog_name = dbutils.widgets.get("catalog_name")

# COMMAND ----------

from pyspark.sql import Window
from pyspark.sql import functions as F

pokemon = spark.table(f"{catalog_name}.silver.pokemon")
stats = spark.table(f"{catalog_name}.silver.pokemon_stats")
types = spark.table(f"{catalog_name}.silver.pokemon_types")

# COMMAND ----------

# --- gold.pokemon_profile --- ficha completa: stats + tipos + sprite/artwork + lore
types_agg = (
    types.groupBy("pokemon_id")
    .agg(F.sort_array(F.collect_list(F.struct("slot", "type_name"))).alias("type_structs"))
    .select("pokemon_id", F.col("type_structs.type_name").alias("types"))
)

# Lore: se recalcula acá adentro (species_id incluido) en vez de sumarlo a
# silver.pokemon, a propósito -- así el lore se puede recomputar corriendo
# SOLO este task sin tocar silver_transform/dq_check. bronze.pokemon_api_raw
# corre en overwrite puro (Fase 1), así que no hace falta dedup defensivo
# acá como en silver.py.
pokemon_species_map_schema = "id INT, species STRUCT<url: STRING>"
pokemon_species_map = (
    spark.table(f"{catalog_name}.bronze.pokemon_api_raw")
    .withColumn("payload", F.from_json("raw_json", pokemon_species_map_schema))
    .select(
        F.col("id").alias("pokemon_id"),
        F.regexp_extract(F.col("payload.species.url"), r"/pokemon-species/(\d+)/?$", 1)
        .cast("int")
        .alias("species_id"),
    )
)

species_lore_schema = """
    id INT,
    flavor_text_entries ARRAY<STRUCT<
        flavor_text: STRING,
        language: STRUCT<name: STRING>,
        version: STRUCT<name: STRING>
    >>
"""

lore_entries = (
    spark.table(f"{catalog_name}.bronze.pokemon_species_raw")
    .withColumn("payload", F.from_json("raw_json", species_lore_schema))
    .select(F.col("id").alias("species_id"), F.explode("payload.flavor_text_entries").alias("entry"))
    .select(
        "species_id",
        F.col("entry.language.name").alias("language"),
        F.col("entry.version.name").alias("version"),
        # PokeAPI trae flavor_text con \n y \f (form feed) de line-wrapping
        # del juego original -- se normaliza a espacios simples.
        F.trim(F.regexp_replace(F.col("entry.flavor_text"), r"\s+", " ")).alias("lore"),
    )
    .filter((F.col("language").isin("es", "en")) & (F.length("lore") > 0))
)

# Preferencia por especie: español si existe alguna entrada "es", si no inglés.
species_has_spanish = lore_entries.groupBy("species_id").agg(
    F.max(F.when(F.col("language") == "es", 1).otherwise(0)).alias("has_es")
)

lore_preferred_language = lore_entries.join(species_has_spanish, "species_id").filter(
    ((F.col("has_es") == 1) & (F.col("language") == "es"))
    | ((F.col("has_es") == 0) & (F.col("language") == "en"))
)

# Entre las variantes de versión de juego que sobreviven el filtro de
# idioma, una sola por especie (pick determinístico por nombre de versión,
# no "las 20 variantes" -- reglas/01-datos-medallion.md).
lore_pick_window = Window.partitionBy("species_id").orderBy("version")
species_lore = (
    lore_preferred_language.withColumn("_rn", F.row_number().over(lore_pick_window))
    .filter("_rn = 1")
    .select("species_id", "lore")
)

pokemon_lore = pokemon_species_map.join(species_lore, "species_id", "left").select("pokemon_id", "lore")

pokemon_profile = (
    pokemon.join(stats, "pokemon_id", "left")
    .join(types_agg, "pokemon_id", "left")
    .join(pokemon_lore, "pokemon_id", "left")
    .select(
        "pokemon_id",
        "pokemon_name",
        "generation",
        "height",
        "weight",
        "sprite_url",
        "artwork_url",
        "types",
        "hp",
        "attack",
        "defense",
        "special_attack",
        "special_defense",
        "speed",
        "lore",
    )
)

pokemon_profile.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{catalog_name}.gold.pokemon_profile")

# COMMAND ----------

# --- gold.pokemon_battle_stats --- totales y ratios calculados acá, nunca en el prompt
pokemon_battle_stats = pokemon.join(stats, "pokemon_id", "left").select(
    "pokemon_id",
    "pokemon_name",
    "hp",
    "attack",
    "defense",
    "special_attack",
    "special_defense",
    "speed",
    (
        F.col("hp")
        + F.col("attack")
        + F.col("defense")
        + F.col("special_attack")
        + F.col("special_defense")
        + F.col("speed")
    ).alias("total_stats"),
    # null explícito si defense=0 -- nunca fabricar un ratio (reglas/01-datos-medallion.md)
    F.when(F.col("defense") > 0, F.round(F.col("attack") / F.col("defense"), 2))
    .otherwise(F.lit(None).cast("double"))
    .alias("attack_defense_ratio"),
)

pokemon_battle_stats.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{catalog_name}.gold.pokemon_battle_stats"
)

# COMMAND ----------

# --- gold.pokemon_type_matchups ---
# Fuente de verdad: damage_relations que PokeAPI ya calcula por tipo
# (bronze.pokemon_types_raw) -- no se hardcodea una tabla de tipos a mano,
# se deriva de la misma fuente estructurada que el resto de Bronze. Grain:
# (attacking_type, defending_type) -> damage_multiplier, para las 21x21
# combinaciones (incluye "unknown"/"shadow", que quedan neutras porque no
# tienen damage_relations jugables).
type_schema = """
    name STRING,
    damage_relations STRUCT<
        double_damage_to: ARRAY<STRUCT<name: STRING>>,
        half_damage_to: ARRAY<STRUCT<name: STRING>>,
        no_damage_to: ARRAY<STRUCT<name: STRING>>
    >
"""

types_raw = spark.table(f"{catalog_name}.bronze.pokemon_types_raw").withColumn(
    "payload", F.from_json("raw_json", type_schema)
)

real_types = types_raw.select(F.col("payload.name").alias("attacking_type"), "payload").filter(
    F.col("payload.damage_relations").isNotNull()
)

all_type_names = [r["attacking_type"] for r in real_types.select("attacking_type").distinct().collect()]

base_grid = spark.createDataFrame(
    [(a, d) for a in all_type_names for d in all_type_names],
    ["attacking_type", "defending_type"],
).withColumn("damage_multiplier", F.lit(1.0))


def relation_overrides(field_name, multiplier):
    return (
        real_types.select("attacking_type", F.explode(f"payload.damage_relations.{field_name}").alias("d"))
        .select("attacking_type", F.col("d.name").alias("defending_type"))
        .withColumn("override_multiplier", F.lit(multiplier))
    )


overrides = (
    relation_overrides("double_damage_to", 2.0)
    .unionByName(relation_overrides("half_damage_to", 0.5))
    .unionByName(relation_overrides("no_damage_to", 0.0))
)

pokemon_type_matchups = (
    base_grid.join(overrides, on=["attacking_type", "defending_type"], how="left")
    .withColumn("damage_multiplier", F.coalesce("override_multiplier", "damage_multiplier"))
    .drop("override_multiplier")
    .withColumn(
        "effectiveness",
        F.when(F.col("damage_multiplier") == 0.0, "no_effect")
        .when(F.col("damage_multiplier") < 1.0, "not_very_effective")
        .when(F.col("damage_multiplier") > 1.0, "super_effective")
        .otherwise("neutral"),
    )
)

pokemon_type_matchups.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{catalog_name}.gold.pokemon_type_matchups"
)

# COMMAND ----------

# --- gold.pokemon_generation_summary --- agregados por generación
pokemon_generation_summary = (
    pokemon.join(stats, "pokemon_id", "left")
    .groupBy("generation")
    .agg(
        F.count("*").alias("pokemon_count"),
        F.round(F.avg("hp"), 2).alias("avg_hp"),
        F.round(F.avg("attack"), 2).alias("avg_attack"),
        F.round(F.avg("defense"), 2).alias("avg_defense"),
        F.round(F.avg("special_attack"), 2).alias("avg_special_attack"),
        F.round(F.avg("special_defense"), 2).alias("avg_special_defense"),
        F.round(F.avg("speed"), 2).alias("avg_speed"),
        F.round(
            F.avg(
                F.col("hp")
                + F.col("attack")
                + F.col("defense")
                + F.col("special_attack")
                + F.col("special_defense")
                + F.col("speed")
            ),
            2,
        ).alias("avg_total_stats"),
    )
    .orderBy("generation")
)

pokemon_generation_summary.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{catalog_name}.gold.pokemon_generation_summary"
)
