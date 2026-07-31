"""Ingestion Bronze : historique météo journalier (source externe, API Open-Meteo).

Pour les villes les plus représentées dans business.json (Bronze), récupère
l'historique météo journalier (températures, précipitations) via l'API
gratuite Open-Meteo (archive-api.open-meteo.com, pas de clé requise), sur la
plage de dates couvrant les avis Yelp.

Les villes sont regroupées par lots (BATCH_SIZE) : l'API accepte des
coordonnées multiples séparées par des virgules et renvoie une liste de
résultats en une seule réponse.

Limité au TOP_N_CITIES par nombre de commerces (pas les 1467 villes
distinctes) : mesuré empiriquement, le quota horaire d'Open-Meteo ne tient
que ~60-100 localisations/heure, donc les 1467 villes prendraient plusieurs
jours. Le top 150 couvre déjà ~87% des commerces du dataset.

Idempotent : si le fichier combiné existe déjà dans bronze, le script skip.
"""
import argparse
import csv
import io
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone

import requests
from botocore.exceptions import ClientError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "conf"))
from s3_client import get_client  # noqa: E402

BUCKET = "bronze"
OUTPUT_KEY = "weather/daily_weather_by_city.csv"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
START_DATE = os.environ.get("WEATHER_START_DATE")
END_DATE = os.environ.get("WEATHER_END_DATE")
DAILY_VARS = "temperature_2m_max,temperature_2m_min,precipitation_sum"
TOP_N_CITIES = int(os.environ.get("WEATHER_TOP_N_CITIES", "150"))
BATCH_SIZE = 10  # mesuré empiriquement : le quota "minutely" d'Open-Meteo compte les
# localisations du lot, pas le nombre de requêtes HTTP - 10 loc. consomme déjà tout
# le budget de la minute en cours.
REQUEST_DELAY_SECONDS = 65.0  # une marge au-delà de la fenêtre d'1 minute
MAX_RETRY_WAIT_SECONDS = 90.0  # si Retry-After demande plus (quota horaire), on
# abandonne le lot plutôt que de bloquer tout le run pendant potentiellement 1h


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


def get_top_cities(client, top_n: int) -> dict:
    """Les `top_n` villes avec le plus de commerces (coordonnées prises au
    premier commerce rencontré), triées par nombre de commerces décroissant."""
    obj = client.get_object(Bucket=BUCKET, Key="yelp/json/yelp_academic_dataset_business.json")
    coords: dict = {}
    counts: Counter = Counter()
    for line in obj["Body"].iter_lines():
        try:
            d = json.loads(line)
            key = (d["city"], d["state"])
            if not (d.get("latitude") and d.get("longitude")):
                continue
            counts[key] += 1
            if key not in coords:
                coords[key] = (d["latitude"], d["longitude"])
        except (json.JSONDecodeError, KeyError):
            continue

    top_keys = [key for key, _ in counts.most_common(top_n)]
    return {key: coords[key] for key in top_keys}


def chunked(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def fetch_batch_weather(session: requests.Session, batch: list, retries: int = 3) -> list[list]:
    """batch : liste de ((city, state), (lat, lon))."""
    lats = ",".join(str(lat) for (_, (lat, _)) in batch)
    lons = ",".join(str(lon) for (_, (_, lon)) in batch)
    params = {
        "latitude": lats,
        "longitude": lons,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": DAILY_VARS,
        "timezone": "auto",
    }

    last_exc = None
    resp = None
    for attempt in range(retries + 1):
        try:
            resp = session.get(ARCHIVE_URL, params=params, timeout=60)
            if resp.status_code == 429:
                wait = float(resp.headers.get("Retry-After", 60 * (attempt + 1)))
                if wait > MAX_RETRY_WAIT_SECONDS:
                    log(f"[weather] 429, Retry-After={wait:.0f}s > max autorisé, on abandonne ce lot")
                    raise requests.HTTPError(f"429 quota probablement horaire (Retry-After={wait:.0f}s)")
                log(f"[weather] 429, pause {wait:.0f}s avant retry...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            break
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(3.0 * (attempt + 1))
    else:
        raise last_exc or RuntimeError("429 Too Many Requests (retries épuisés)")

    data = resp.json()
    # Une seule localisation -> dict simple ; plusieurs -> liste de dicts (même ordre que la requête)
    results = data if isinstance(data, list) else [data]

    rows = []
    for (city, state), result in zip([k for k, _ in batch], results):
        daily = result.get("daily", {})
        dates = daily.get("time", [])
        tmax = daily.get("temperature_2m_max", [])
        tmin = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])
        for i, date in enumerate(dates):
            rows.append(
                [
                    city,
                    state,
                    date,
                    tmax[i] if i < len(tmax) else "",
                    tmin[i] if i < len(tmin) else "",
                    precip[i] if i < len(precip) else "",
                ]
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limiter à N villes (tests)")
    args = parser.parse_args()

    client = get_client()
    if object_exists(client, OUTPUT_KEY):
        log(f"[weather] skip {OUTPUT_KEY} (déjà présent dans bronze)")
        return

    log("=== INGESTION BRONZE - Météo (Open-Meteo API) : DEBUT ===")
    t0 = time.time()
    cities = get_top_cities(client, TOP_N_CITIES)
    items = list(cities.items())
    if args.limit:
        items = items[: args.limit]
    batches = list(chunked(items, BATCH_SIZE))
    log(f"[weather] top {len(items)} ville(s) (sur {TOP_N_CITIES} demandées) à traiter en {len(batches)} lot(s) de {BATCH_SIZE}")

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["city", "state", "date", "temp_max_c", "temp_min_c", "precipitation_mm"])

    record_count = 0
    cities_failed = 0
    session = requests.Session()
    for i, batch in enumerate(batches, start=1):
        try:
            rows = fetch_batch_weather(session, batch)
            writer.writerows(rows)
            record_count += len(rows)
        except Exception as exc:
            cities_failed += len(batch)
            log(f"[weather] erreur sur le lot {i} ({len(batch)} villes): {exc}")
        log(f"[weather] lot {i}/{len(batches)} traité ({record_count} records cumulés)")
        time.sleep(REQUEST_DELAY_SECONDS)

    body = buffer.getvalue().encode("utf-8")
    client.upload_fileobj(io.BytesIO(body), BUCKET, OUTPUT_KEY)
    duration = time.time() - t0
    log(f"[weather] {OUTPUT_KEY} -> {len(body) / (1024**2):.1f} MB, {record_count} records, {duration:.1f}s")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "source": "open_meteo_api",
        "ingested_at": timestamp,
        "files": [
            {
                "file": OUTPUT_KEY,
                "bytes": len(body),
                "records": record_count,
                "cities_processed": len(items) - cities_failed,
                "cities_failed": cities_failed,
                "duration_seconds": round(duration, 2),
            }
        ],
    }
    report_key = f"_metrics/ingest_weather_{timestamp}.json"
    client.upload_fileobj(io.BytesIO(json.dumps(report, indent=2).encode("utf-8")), BUCKET, report_key)
    log(f"[metrics] rapport sauvegardé -> s3://{BUCKET}/{report_key}")
    log(f"=== INGESTION BRONZE - Météo : TERMINEE === {record_count} records, {cities_failed} villes en erreur")


if __name__ == "__main__":
    main()
