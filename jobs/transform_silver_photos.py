"""Transformation Silver pour les photos (données non-structurées).

Lit l'échantillon extrait par prepare_silver_photos_sample.py
(bronze/yelp/photos_sample/*.jpg) via le format binaryFile de Spark,
valide chaque image (décodable ou corrompue), déduplique (hash exact +
hash perceptif pour les quasi-doublons), et écrit un index Parquet dans
silver/photos_index/ (pas les images elles-mêmes, juste leurs métadonnées -
les binaires bruts restent consultables dans bronze si besoin).

Nécessite Pillow, ajouté à l'image Spark du projet via docker/spark/Dockerfile
(absent de l'image Bitnami de base).
"""
import hashlib
import io
import time

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import BooleanType, IntegerType, StringType, StructField, StructType

BRONZE = "s3a://bronze"
SILVER = "s3a://silver"


def log(msg: str) -> None:
    print(msg, flush=True)


def sha256_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def average_hash(data: bytes) -> str:
    """Hash perceptif simple (aHash, 8x8) : deux images visuellement proches
    donnent le même hash même si leurs octets diffèrent (recompression,
    léger recadrage...) - c'est ça qui permet la dédup "approchée"."""
    from PIL import Image

    img = Image.open(io.BytesIO(data)).convert("L").resize((8, 8))
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if p >= avg else "0" for p in pixels)
    return f"{int(bits, 2):016x}"


IMAGE_SCHEMA = StructType(
    [
        StructField("valid", BooleanType(), True),
        StructField("width", IntegerType(), True),
        StructField("height", IntegerType(), True),
        StructField("sha256", StringType(), True),
        StructField("phash", StringType(), True),
    ]
)


def analyze_image(data: bytes):
    from PIL import Image, UnidentifiedImageError

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img2 = Image.open(io.BytesIO(data))  # verify() invalide l'objet, on ré-ouvre
        width, height = img2.size
        return (True, width, height, sha256_hash(data), average_hash(data))
    except (UnidentifiedImageError, OSError, ValueError):
        return (False, None, None, sha256_hash(data), None)


def main() -> None:
    spark = SparkSession.builder.appName("silver-photos-transform").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    analyze_udf = F.udf(analyze_image, IMAGE_SCHEMA)

    log("=== SILVER photos : DEBUT ===")
    t0 = time.time()

    raw = spark.read.format("binaryFile").load(f"{BRONZE}/yelp/photos_sample/*")
    raw = raw.select(F.element_at(F.split(F.col("path"), "/"), -1).alias("filename"), "content").cache()
    total_in = raw.count()

    analyzed = raw.withColumn("info", analyze_udf(F.col("content"))).select(
        "filename",
        "content",
        F.col("info.valid").alias("valid"),
        F.col("info.width").alias("width"),
        F.col("info.height").alias("height"),
        F.col("info.sha256").alias("sha256"),
        F.col("info.phash").alias("phash"),
    ).cache()
    raw.unpersist()

    invalid_count = analyzed.filter(~F.col("valid")).count()
    valid = analyzed.filter(F.col("valid")).cache()
    analyzed.unpersist()

    # Doublons exacts : même sha256 (contenu binaire identique)
    exact_deduped = valid.dropDuplicates(["sha256"]).cache()
    exact_dup_count = valid.count() - exact_deduped.count()

    # Doublons approchés : même hash perceptif mais sha256 différent
    # (recompression, ré-upload... visuellement identique, pas bit-à-bit)
    approx_deduped = exact_deduped.dropDuplicates(["phash"]).cache()
    approx_dup_count = exact_deduped.count() - approx_deduped.count()
    exact_deduped.unpersist()

    total_out = approx_deduped.count()

    index = approx_deduped.select("filename", "width", "height", "sha256", "phash")
    index.write.mode("overwrite").parquet(f"{SILVER}/photos_index")
    valid.unpersist()

    metrics = {
        "entity": "photos",
        "total_input_records": total_in,
        "invalid_records_dropped": invalid_count,
        "exact_duplicates_found": exact_dup_count,
        "approx_duplicates_found": approx_dup_count,
        "total_output_records": total_out,
        "duration_seconds": round(time.time() - t0, 2),
    }
    log(f"=== SILVER photos : TERMINE === {metrics}")

    import json as _json
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    spark.sparkContext.parallelize([_json.dumps(metrics, indent=2)], 1).saveAsTextFile(
        f"{SILVER}/_quality/photos_{timestamp}.json"
    )

    spark.stop()


if __name__ == "__main__":
    main()
