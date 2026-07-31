"""Transformation Silver -> Gold (KPIs métier, chargés dans PostgreSQL).

Scope : A1-A4 du dashboard gérant/analyste (cf. README_fonctionnalites.md).

- A1 kpi_business             : note moyenne / volume d'avis par catégorie, ville, prix
- A2 kpi_meteo_frequentation  : check-ins moyens/jour, pluie vs beau temps (villes météo uniquement)
- A3 kpi_cout_vie_prix        : positionnement prix/note vs coût de la vie, par état
- A4 score_valeur_percue      : note ajustée par le prix normalisé au coût de vie local
- dim_business_photos         : photos (non-structuré) liées à leur établissement

Écrit dans les tables gold.* définies par postgres/init/01-init.sql (le
script ne fait que TRUNCATE + INSERT dans des tables déjà créées - il ne
recrée jamais le schéma, pour préserver contraintes/index/PK).

Exécution :
    docker exec --user root spark-master /opt/bitnami/spark/bin/spark-submit \\
        --master spark://spark-master:7077 \\
        --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \\
        --conf spark.hadoop.fs.s3a.access.key=$MINIO_ROOT_USER \\
        --conf spark.hadoop.fs.s3a.secret.key=$MINIO_ROOT_PASSWORD \\
        --conf spark.hadoop.fs.s3a.path.style.access=true \\
        --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \\
        --conf spark.hadoop.fs.s3a.connection.ssl.enabled=false \\
        /opt/spark-apps/transform_gold.py
"""
import os
import time

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

SILVER = "s3a://silver"
GOLD = "s3a://gold"
JDBC_URL = f"jdbc:postgresql://postgres:5432/{os.environ.get('POSTGRES_DB', 'gold_warehouse')}"
JDBC_PROPS = {
    "user": os.environ.get("POSTGRES_USER", "datalake_admin"),
    "password": os.environ.get("POSTGRES_PASSWORD", ""),
    "driver": "org.postgresql.Driver",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def write_gold(df, table: str) -> int:
    """Écrit la table Gold à deux endroits :
    - bronze/silver/gold restent tous les trois dans le data lake (MinIO,
      Parquet) - c'est la convention standard de l'architecture Medallion ;
    - en plus, chargement dans PostgreSQL pour l'exposition en SQL/BI/API
      (exigence explicite du sujet)."""
    count = df.count()
    df = df.cache()

    table_name = table.split(".", 1)[-1]
    df.write.mode("overwrite").parquet(f"{GOLD}/{table_name}")

    # truncate=true : TRUNCATE + INSERT plutôt que DROP/CREATE - préserve le
    # schéma (PK, FK, index) défini dans postgres/init/01-init.sql.
    df.write.option("truncate", "true").jdbc(url=JDBC_URL, table=table, mode="overwrite", properties=JDBC_PROPS)
    df.unpersist()
    log(f"[gold] {table} <- {count} lignes (MinIO gold/{table_name} + Postgres {table})")
    return count


def load_business(spark) -> "DataFrame":
    df = spark.read.parquet(f"{SILVER}/business")
    # `state` contient quelques valeurs aberrantes dans le dataset Yelp brut
    # (ex: codes à 3+ caractères) - state_code est un CHAR(2) côté Gold
    # (vrais codes d'état US), donc on filtre plutôt que d'élargir la colonne.
    df = df.filter(F.length(F.col("state")) == 2)
    return df.withColumn("cost_of_living_index", F.col("cost_of_living_index").cast("double")).withColumn(
        "gamme_prix_num", F.col("attributes.RestaurantsPriceRange2").cast("double")
    )


def build_kpi_business(business):
    exploded = business.withColumn("categorie", F.explode_outer("categories"))
    return (
        exploded.groupBy(
            F.col("categorie"),
            F.col("city").alias("ville"),
            F.col("state").alias("state_code"),
            F.col("attributes.RestaurantsPriceRange2").alias("gamme_prix"),
        )
        .agg(
            F.round(F.avg("stars"), 2).alias("note_moyenne"),
            F.sum("review_count").alias("nb_avis_total"),
            F.countDistinct("business_id").alias("nb_etablissements"),
        )
        .filter(F.col("categorie").isNotNull())
    )


def build_kpi_cout_vie_prix(business):
    return (
        business.filter(F.col("cost_of_living_index").isNotNull())
        .groupBy(F.col("state").alias("state_code"))
        .agg(
            F.first("cost_of_living_index").alias("cost_of_living_index"),
            F.round(F.avg("gamme_prix_num"), 2).alias("gamme_prix_moyenne"),
            F.round(F.avg("stars"), 2).alias("note_moyenne_etat"),
            F.countDistinct("business_id").alias("nb_etablissements"),
        )
    )


def build_score_valeur_percue(business):
    # prix normalisé par le coût de la vie local : un $$$ dans un état cher
    # "coûte" relativement moins qu'un $$$ dans un état bon marché.
    valid = business.filter(F.col("cost_of_living_index").isNotNull() & F.col("gamme_prix_num").isNotNull())
    prix_normalise = F.col("gamme_prix_num") * (F.lit(100.0) / F.col("cost_of_living_index"))
    return valid.select(
        F.col("business_id"),
        F.col("name").alias("nom"),
        F.col("state").alias("state_code"),
        F.col("city").alias("ville"),
        F.col("attributes.RestaurantsPriceRange2").alias("gamme_prix"),
        F.round(F.col("stars"), 2).alias("note_moyenne"),
        F.col("cost_of_living_index"),
        F.round(F.col("stars") / prix_normalise, 4).alias("score_valeur_ajuste"),
    )


def build_summary(business):
    """Une seule ligne de synthèse (page d'accueil) - comptages non exposés
    aux doublons de l'explosion par catégorie dans kpi_business."""
    return business.agg(
        F.countDistinct("business_id").alias("nb_etablissements"),
        F.sum("review_count").alias("nb_avis"),
        F.round(F.avg("stars"), 2).alias("note_moyenne"),
        F.countDistinct("city").alias("nb_villes"),
    )


def build_dim_business(business):
    """Une ligne par établissement, infos brutes (pas d'agrégation) - couvre
    TOUS les établissements, contrairement à kpi_business (agrégé) et
    score_valeur_percue (filtré aux prix + coût de vie connus)."""
    return business.select(
        "business_id",
        F.col("name").alias("nom"),
        F.col("address").alias("adresse"),
        F.col("city").alias("ville"),
        F.col("state").alias("state_code"),
        F.col("postal_code").alias("code_postal"),
        F.col("attributes.RestaurantsPriceRange2").alias("gamme_prix"),
        F.round(F.col("stars"), 2).alias("note_moyenne"),
        F.col("review_count").alias("nb_avis"),
        F.col("is_open").alias("ouvert"),
    )


def build_dim_review(spark):
    """Avis détaillés (texte, note, votes) - table complète (6.99M lignes),
    indexée par business_id côté Postgres pour une consultation rapide par
    établissement (ex: clic sur le nombre d'avis dans la galerie)."""
    review = spark.read.parquet(f"{SILVER}/review")
    return review.select(
        "review_id",
        "business_id",
        "user_id",
        F.col("stars").alias("note"),
        F.col("text").alias("texte"),
        F.to_date("date").alias("date_avis"),
        F.col("useful").alias("utile"),
        F.col("funny").alias("drole"),
        F.col("cool").alias("sympa"),
    )


def build_dim_business_photos(spark):
    """Photos (non-structuré) liées à leur établissement, via photo_id ->
    business_id (photos.json). Limité à l'échantillon Silver (5000 photos)."""
    photos = spark.read.parquet(f"{SILVER}/photos_index")
    return photos.filter(F.col("business_id").isNotNull()).select(
        "photo_id", "business_id", "caption", "label"
    )


def build_kpi_meteo_frequentation(spark, business):
    """Nb moyen de check-ins/jour par ville, jour de pluie vs beau temps.
    Limité aux villes couvertes par l'ingestion météo (échantillon, cf.
    jobs/ingest_bronze_weather.py)."""
    checkin = spark.read.parquet(f"{SILVER}/checkin")  # business_id, checkin_time, year
    weather = spark.read.parquet(f"{SILVER}/weather")  # city, state, date, ..., precipitation_mm

    checkin_city = checkin.join(business.select("business_id", "city", "state"), "business_id").withColumn(
        "date", F.to_date("checkin_time")
    )
    daily_checkins = checkin_city.groupBy("city", "state", "date").agg(F.count("*").alias("nb_checkins"))

    joined = daily_checkins.join(
        weather.select(
            F.col("city").alias("w_city"), F.col("state").alias("w_state"), "date", "precipitation_mm"
        ),
        (daily_checkins.city == F.col("w_city"))
        & (daily_checkins.state == F.col("w_state"))
        & (daily_checkins.date == weather["date"]),
        "inner",
    ).withColumn(
        "condition_meteo", F.when(F.col("precipitation_mm") > 1.0, "pluie").otherwise("beau_temps")
    )

    return joined.groupBy(F.col("city").alias("ville"), "condition_meteo").agg(
        F.round(F.avg("nb_checkins"), 2).alias("nb_checkins_moyen_jour")
    )


def main() -> None:
    spark = SparkSession.builder.appName("gold-transform").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    log("=== GOLD : DEBUT ===")
    t0 = time.time()

    business = load_business(spark).cache()
    business.count()  # matérialise le cache avant les agrégations qui le réutilisent

    # Dimension d'abord : kpi_cout_vie_prix a une contrainte FK dessus.
    dim_cost_of_living = spark.read.parquet(f"{SILVER}/internal_cost_of_living")
    write_gold(dim_cost_of_living, "gold.dim_cost_of_living")

    write_gold(build_summary(business), "gold.dim_summary")
    write_gold(build_dim_business(business), "gold.dim_business")
    write_gold(build_kpi_business(business), "gold.kpi_business")
    write_gold(build_kpi_cout_vie_prix(business), "gold.kpi_cout_vie_prix")
    write_gold(build_score_valeur_percue(business), "gold.score_valeur_percue")
    write_gold(build_kpi_meteo_frequentation(spark, business), "gold.kpi_meteo_frequentation")
    write_gold(build_dim_business_photos(spark), "gold.dim_business_photos")
    write_gold(build_dim_review(spark), "gold.dim_review")  # la plus grosse (6.99M lignes), en dernier

    business.unpersist()
    log(f"=== GOLD : TERMINE === {time.time() - t0:.1f}s")
    spark.stop()


if __name__ == "__main__":
    main()
