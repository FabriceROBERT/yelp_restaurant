"""Ingestion Bronze : source INTERNE (pas de téléchargement réseau).

Contrairement à ingest_bronze_yelp.py (source externe, fetch HTTP), ce script
upload un fichier de référence maintenu dans le repo (data/internal/) vers
bronze/internal/. C'est ça qui distingue une source interne d'une source
externe : le fichier est committé dans le projet, pas récupéré à l'exécution.

data/internal/cost_of_living_by_state.csv : indice du coût de la vie par État
US (base 100 = moyenne nationale), utilisé pour normaliser le "budget perçu"
(price range Yelp) par le coût de la vie réel local.
Source : agrégat MERIC / BEA Regional Price Parities.

Idempotent : skip si déjà présent dans bronze. Métriques loggées et
sauvegardées dans bronze/_metrics/, comme pour la source externe.
"""
import io
import json
import os
import sys
import time
from datetime import datetime, timezone

from botocore.exceptions import ClientError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "conf"))
from s3_client import get_client  # noqa: E402

BUCKET = "bronze"
INTERNAL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "internal")


def log(msg: str) -> None:
    print(msg, flush=True)


def object_exists(client, key: str) -> bool:
    try:
        client.head_object(Bucket=BUCKET, Key=key)
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return False
        raise


def upload_internal_file(client, filename: str, metrics: list) -> None:
    key = f"internal/{filename}"
    if object_exists(client, key):
        log(f"[internal] skip {key} (déjà présent dans bronze)")
        return

    local_path = os.path.join(INTERNAL_DIR, filename)
    t0 = time.time()
    with open(local_path, "rb") as f:
        body = f.read()
    record_count = body.count(b"\n")  # CSV : une ligne par record (header inclus)
    client.upload_fileobj(io.BytesIO(body), BUCKET, key)
    duration = time.time() - t0
    log(f"[internal] {key} -> {len(body) / 1024:.1f} KB, {record_count} lignes, {duration:.2f}s")
    metrics.append(
        {
            "file": key,
            "bytes": len(body),
            "records": record_count,
            "duration_seconds": round(duration, 2),
        }
    )


def save_metrics_report(client, metrics: list) -> None:
    if not metrics:
        log("[metrics] rien de nouveau ingéré, pas de rapport")
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {"source": "internal_reference_data", "ingested_at": timestamp, "files": metrics}
    body = json.dumps(report, indent=2).encode("utf-8")
    key = f"_metrics/ingest_internal_{timestamp}.json"
    client.upload_fileobj(io.BytesIO(body), BUCKET, key)
    log(f"[metrics] rapport sauvegardé -> s3://{BUCKET}/{key}")


def main() -> None:
    log("=== INGESTION BRONZE - Source interne : DEBUT ===")
    client = get_client()
    metrics: list = []
    upload_internal_file(client, "cost_of_living_by_state.csv", metrics)
    save_metrics_report(client, metrics)
    log(f"=== INGESTION BRONZE - Source interne : TERMINEE === {len(metrics)} fichier(s) traité(s)")


if __name__ == "__main__":
    main()
