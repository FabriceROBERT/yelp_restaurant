"""Transformation Bronze -> Silver (Apache Spark, cluster non-local).

Pour chaque entité :
    1. Lecture depuis bronze (JSON/CSV brut)
    2. Validation de schéma + conversions de type
    3. Filtrage des records invalides (champs obligatoires manquants)
    4. Déduplication exacte (ligne entière) puis approchée (clé métier)
    5. Écriture Parquet partitionné dans silver (indexation / perf de requête)
    6. Rapport qualité (nulls, invalides, doublons) -> silver/_quality/

Exécution (cluster Spark via spark-submit, pas en local) :
    docker exec --user root spark-master /opt/bitnami/spark/bin/spark-submit \\
        --master spark://spark-master:7077 \\
        --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \\
        --conf spark.hadoop.fs.s3a.access.key=$MINIO_ROOT_USER \\
        --conf spark.hadoop.fs.s3a.secret.key=$MINIO_ROOT_PASSWORD \\
        --conf spark.hadoop.fs.s3a.path.style.access=true \\
        --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \\
        --conf spark.hadoop.fs.s3a.connection.ssl.enabled=false \\
        /opt/spark-apps/transform_silver.py --entity business

--user root : contourne un bug Hadoop/JAAS quand l'UID du container bitnami
(1001) n'a pas d'entrée /etc/passwd (UserGroupInformation plante sinon).
"""
import argparse
import json
import time
from datetime import datetime, timezone

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    DoubleType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

BRONZE = "s3a://bronze"
SILVER = "s3a://silver"


def log(msg: str) -> None:
    print(msg, flush=True)


def clean(df: DataFrame, entity: str, required_cols: list[str], key_cols: list[str]) -> tuple[DataFrame, dict]:
    """Filtre les records invalides, déduplique (exact puis approché), et
    renvoie le DataFrame nettoyé + les métriques qualité."""
    df = df.cache()
    total_in = df.count()

    null_counts = df.select(
        [F.count(F.when(F.col(c).isNull(), c)).alias(c) for c in required_cols]
    ).collect()[0].asDict()

    valid = df.dropna(subset=required_cols).cache()
    valid_count = valid.count()
    invalid_count = total_in - valid_count
    df.unpersist()

    exact_deduped = valid.dropDuplicates().cache()
    exact_deduped_count = exact_deduped.count()
    exact_duplicates_found = valid_count - exact_deduped_count
    valid.unpersist()

    business_deduped = exact_deduped.dropDuplicates(key_cols).cache()
    total_out = business_deduped.count()
    business_duplicates_found = exact_deduped_count - total_out
    exact_deduped.unpersist()

    metrics = {
        "entity": entity,
        "total_input_records": total_in,
        "null_counts": null_counts,
        "invalid_records_dropped": invalid_count,
        "exact_duplicates_found": exact_duplicates_found,
        "business_key_duplicates_found": business_duplicates_found,
        "total_output_records": total_out,
    }
    return business_deduped, metrics


def write_silver(df: DataFrame, entity: str, partition_by: str | None) -> None:
    writer = df.write.mode("overwrite")
    if partition_by:
        writer = writer.partitionBy(partition_by)
    writer.parquet(f"{SILVER}/{entity}")


def save_quality_report(spark: SparkSession, metrics: dict) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = f"{SILVER}/_quality/{metrics['entity']}_{timestamp}.json"
    body = json.dumps(metrics, indent=2)
    spark.sparkContext.parallelize([body], 1).saveAsTextFile(path)
    log(f"[quality] rapport -> {path}")


# ---------------------------------------------------------------- business
def transform_business(spark: SparkSession) -> tuple[DataFrame, dict]:
    df = spark.read.json(f"{BRONZE}/yelp/json/yelp_academic_dataset_business.json")
    df = (
        df.withColumn("is_open", F.col("is_open").cast("boolean"))
        .withColumn("categories", F.split(F.col("categories"), ", "))
        .withColumn("review_count", F.col("review_count").cast(LongType()))
        .withColumn("stars", F.col("stars").cast(DoubleType()))
    )
    clean_df, metrics = clean(
        df, "business", required_cols=["business_id", "name", "city", "state", "stars"], key_cols=["business_id"]
    )

    cost_of_living = spark.read.option("header", True).csv(f"{BRONZE}/internal/cost_of_living_by_state.csv")
    enriched = clean_df.join(
        cost_of_living.select("state_code", "cost_of_living_index"),
        clean_df.state == cost_of_living.state_code,
        "left",
    ).drop("state_code")
    metrics["enriched_with_cost_of_living"] = enriched.filter(F.col("cost_of_living_index").isNotNull()).count()
    return enriched, metrics


# ------------------------------------------------------------------ review
def transform_review(spark: SparkSession) -> tuple[DataFrame, dict]:
    df = spark.read.json(f"{BRONZE}/yelp/json/yelp_academic_dataset_review.json")
    df = (
        df.withColumn("date", F.col("date").cast(TimestampType()))
        .withColumn("year", F.year("date"))
        .withColumn("stars", F.col("stars").cast(DoubleType()))
        .withColumn("useful", F.col("useful").cast(LongType()))
        .withColumn("funny", F.col("funny").cast(LongType()))
        .withColumn("cool", F.col("cool").cast(LongType()))
    )
    return clean(
        df,
        "review",
        required_cols=["review_id", "user_id", "business_id", "stars"],
        key_cols=["review_id"],
    )


# -------------------------------------------------------------------- user
def transform_user(spark: SparkSession) -> tuple[DataFrame, dict]:
    df = spark.read.json(f"{BRONZE}/yelp/json/yelp_academic_dataset_user.json")
    df = (
        df.withColumn("yelping_since", F.col("yelping_since").cast(TimestampType()))
        .withColumn("friends", F.split(F.col("friends"), ", "))
        .withColumn("elite", F.split(F.col("elite"), ","))
        .withColumn("review_count", F.col("review_count").cast(LongType()))
    )
    return clean(df, "user", required_cols=["user_id"], key_cols=["user_id"])


# --------------------------------------------------------------------- tip
def transform_tip(spark: SparkSession) -> tuple[DataFrame, dict]:
    df = spark.read.json(f"{BRONZE}/yelp/json/yelp_academic_dataset_tip.json")
    df = (
        df.withColumn("date", F.col("date").cast(TimestampType()))
        .withColumn("year", F.year("date"))
        .withColumn("compliment_count", F.col("compliment_count").cast(LongType()))
    )
    return clean(
        df,
        "tip",
        required_cols=["user_id", "business_id", "text"],
        key_cols=["user_id", "business_id", "text"],
    )


# ----------------------------------------------------------------- checkin
def transform_checkin(spark: SparkSession) -> tuple[DataFrame, dict]:
    """Explose la liste de dates concaténées en une ligne par check-in
    (format long, indexable par date) - optimise pour les requêtes
    temporelles, contrairement au champ brut ('date1, date2, ...')."""
    df = spark.read.json(f"{BRONZE}/yelp/json/yelp_academic_dataset_checkin.json").cache()
    total_in = df.count()
    null_business_id = df.filter(F.col("business_id").isNull()).count()
    valid = df.dropna(subset=["business_id"])
    df.unpersist()

    exploded = (
        valid.withColumn("checkin_time", F.explode(F.split(F.col("date"), ", ")))
        .select("business_id", F.col("checkin_time").cast(TimestampType()).alias("checkin_time"))
        .cache()
    )
    before_dedup = exploded.count()
    invalid_timestamps = exploded.filter(F.col("checkin_time").isNull()).count()
    exploded = exploded.dropna(subset=["checkin_time"]).withColumn("year", F.year("checkin_time"))

    deduped = exploded.dropDuplicates().cache()
    total_out = deduped.count()
    exact_duplicates_found = (before_dedup - invalid_timestamps) - total_out
    exploded.unpersist()

    metrics = {
        "entity": "checkin",
        "total_input_records": total_in,
        "null_counts": {"business_id": null_business_id},
        "invalid_records_dropped": null_business_id + invalid_timestamps,
        "exact_duplicates_found": exact_duplicates_found,
        "business_key_duplicates_found": 0,
        "total_output_records": total_out,
        "note": "1 record en entrée = 1 business ; explosé en 1 ligne par check-in individuel en sortie",
    }
    return deduped, metrics


# --------------------------------------------------------------- internal
def transform_internal(spark: SparkSession) -> tuple[DataFrame, dict]:
    df = spark.read.option("header", True).csv(f"{BRONZE}/internal/cost_of_living_by_state.csv")
    df = df.withColumn("cost_of_living_index", F.col("cost_of_living_index").cast(DoubleType()))
    return clean(df, "internal_cost_of_living", required_cols=["state_code", "cost_of_living_index"], key_cols=["state_code"])


# ---------------------------------------------------------------- weather
def transform_weather(spark: SparkSession) -> tuple[DataFrame, dict]:
    df = spark.read.option("header", True).csv(f"{BRONZE}/weather/daily_weather_by_city.csv")
    df = (
        df.withColumn("date", F.to_date(F.col("date")))
        .withColumn("temp_max_c", F.col("temp_max_c").cast(DoubleType()))
        .withColumn("temp_min_c", F.col("temp_min_c").cast(DoubleType()))
        .withColumn("precipitation_mm", F.col("precipitation_mm").cast(DoubleType()))
    )
    return clean(
        df,
        "weather",
        required_cols=["city", "state", "date"],
        key_cols=["city", "state", "date"],
    )


# ---------------------------------------------------------- photos_metadata
def transform_photos_metadata(spark: SparkSession) -> tuple[DataFrame, dict]:
    """photo_id -> business_id -> caption -> label, extrait de l'archive
    photos (photos.json), pour relier les photos aux établissements."""
    df = spark.read.json(f"{BRONZE}/yelp/photos_metadata.json")
    return clean(
        df,
        "photos_metadata",
        required_cols=["photo_id", "business_id"],
        key_cols=["photo_id"],
    )


ENTITIES = {
    "business": (transform_business, "state"),
    "review": (transform_review, "year"),
    "user": (transform_user, None),
    "tip": (transform_tip, "year"),
    "checkin": (transform_checkin, "year"),
    "internal": (transform_internal, None),
    "weather": (transform_weather, "state"),
    "photos_metadata": (transform_photos_metadata, None),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity", default="all", choices=list(ENTITIES) + ["all"])
    args = parser.parse_args()

    spark = SparkSession.builder.appName("silver-transform").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    targets = list(ENTITIES) if args.entity == "all" else [args.entity]
    for name in targets:
        transform_fn, partition_col = ENTITIES[name]
        log(f"=== SILVER {name} : DEBUT ===")
        t0 = time.time()
        df, metrics = transform_fn(spark)
        write_silver(df, "internal_cost_of_living" if name == "internal" else name, partition_col)
        metrics["duration_seconds"] = round(time.time() - t0, 2)
        save_quality_report(spark, metrics)
        log(f"=== SILVER {name} : TERMINE === {json.dumps(metrics)}")

    spark.stop()


if __name__ == "__main__":
    main()
