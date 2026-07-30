"""Ingestion Bronze : télécharge le Yelp Open Dataset (source externe) et le
stocke brut dans MinIO, sans copie locale permanente du contenu décompressé.

- Package JSON   : Yelp-JSON.zip contient un yelp_dataset.tar, qui contient
                   lui-même les 5 fichiers JSON. Le zip est téléchargé dans un
                   fichier temporaire (nécessaire pour l'accès aléatoire du
                   zip), puis le tar est lu et uploadé en streaming pur
                   (aucune écriture disque du tar ni des JSON).
- Package Photos : streamé directement depuis la requête HTTP vers S3, sans
                   jamais toucher le disque (bronze/yelp/photos.zip).

Idempotent : un fichier déjà présent dans bronze est skip (pas de
re-téléchargement inutile). Métriques (débit, durée, nb de records) loggées
et sauvegardées dans bronze/_metrics/ pour le monitoring.
"""
import io
import json
import os
import tarfile
import tempfile
import time
import zipfile
from datetime import datetime, timezone

import requests
from botocore.exceptions import ClientError

from s3_client import get_client

BUCKET = "bronze"

# Le CDN (CloudFront) renvoie 403 pour le user-agent par défaut de `requests`.
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) yelp-datalake-ingest/1.0"}


class CountingReader:
    """Wrappe un fichier-objet pour compter les octets et lignes lus au fil de l'upload."""

    def __init__(self, fileobj):
        self._fileobj = fileobj
        self.bytes_read = 0
        self.record_count = 0

    def read(self, size=-1):
        chunk = self._fileobj.read(size)
        if chunk:
            self.bytes_read += len(chunk)
            self.record_count += chunk.count(b"\n")
        return chunk


def object_exists(client, key: str) -> bool:
    try:
        client.head_object(Bucket=BUCKET, Key=key)
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return False
        raise


def log(msg: str) -> None:
    print(msg, flush=True)


def _extract_member_to_tempfile(fileobj, suffix: str) -> str:
    """Copie un fichier-objet (zip member) vers un fichier temporaire réel.

    tarfile en mode streaming ("r|") s'est révélé instable au-dessus d'un
    zipfile.ZipExtFile sur cette plateforme (ReadError: invalid header). On
    passe donc par un fichier temporaire avec accès aléatoire, plus robuste.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        while True:
            chunk = fileobj.read(16 * 1024 * 1024)
            if not chunk:
                break
            tmp.write(chunk)
    finally:
        tmp.close()
    return tmp.name


def upload_json_package(client, url: str, metrics: list) -> None:
    log(f"[json] téléchargement {url}")
    t0 = time.time()
    # delete=False + fermeture explicite : sur Windows, un NamedTemporaryFile encore
    # ouvert ne peut pas être ré-ouvert par son nom (erreur de partage), même dans le
    # même processus.
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    zip_path = tmp.name
    tar_path = None
    try:
        try:
            with requests.get(url, stream=True, timeout=60, headers=HEADERS) as resp:
                resp.raise_for_status()
                for chunk in resp.iter_content(chunk_size=8 * 1024 * 1024):
                    tmp.write(chunk)
        finally:
            tmp.close()

        download_seconds = time.time() - t0
        log(f"[json] téléchargé en {download_seconds:.1f}s, extraction du tar imbriqué...")

        with zipfile.ZipFile(zip_path) as zf:
            tar_member = next(n for n in zf.namelist() if n.endswith(".tar"))
            t_extract = time.time()
            with zf.open(tar_member) as tar_stream:
                tar_path = _extract_member_to_tempfile(tar_stream, ".tar")
            log(f"[json] tar extrait en {time.time() - t_extract:.1f}s, upload des JSON...")

        with tarfile.open(tar_path) as tf:
            for member in tf.getmembers():
                if not member.name.endswith(".json"):
                    continue
                key = f"yelp/json/{os.path.basename(member.name)}"
                if object_exists(client, key):
                    log(f"[json] skip {key} (déjà présent dans bronze)")
                    continue
                t1 = time.time()
                reader = CountingReader(tf.extractfile(member))
                client.upload_fileobj(reader, BUCKET, key)
                duration = time.time() - t1
                throughput_mb_s = (reader.bytes_read / (1024 * 1024)) / duration if duration else 0
                log(
                    f"[json] {key} -> {reader.bytes_read / (1024**2):.1f} MB, "
                    f"{reader.record_count} records, {throughput_mb_s:.1f} MB/s"
                )
                metrics.append(
                    {
                        "file": key,
                        "bytes": reader.bytes_read,
                        "records": reader.record_count,
                        "duration_seconds": round(duration, 2),
                        "throughput_mb_s": round(throughput_mb_s, 2),
                    }
                )
    finally:
        os.remove(zip_path)
        if tar_path:
            os.remove(tar_path)


def upload_photos_package(client, url: str, metrics: list) -> None:
    key = "yelp/photos.zip"
    if object_exists(client, key):
        log(f"[photos] skip {key} (déjà présent dans bronze)")
        return
    log(f"[photos] streaming {url} -> s3://{BUCKET}/{key}")
    t0 = time.time()
    with requests.get(url, stream=True, timeout=60, headers=HEADERS) as resp:
        resp.raise_for_status()
        resp.raw.decode_content = True
        reader = CountingReader(resp.raw)
        client.upload_fileobj(reader, BUCKET, key)
    duration = time.time() - t0
    throughput_mb_s = (reader.bytes_read / (1024 * 1024)) / duration if duration else 0
    log(f"[photos] {reader.bytes_read / (1024**2):.1f} MB en {duration:.1f}s, {throughput_mb_s:.1f} MB/s")
    metrics.append(
        {
            "file": key,
            "bytes": reader.bytes_read,
            "records": None,  # ~200 100 photos d'après la doc Yelp, non dénombré (zip stocké brut)
            "duration_seconds": round(duration, 2),
            "throughput_mb_s": round(throughput_mb_s, 2),
        }
    )


def save_metrics_report(client, metrics: list) -> None:
    if not metrics:
        log("[metrics] rien de nouveau ingéré, pas de rapport")
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {"source": "yelp_open_dataset", "ingested_at": timestamp, "files": metrics}
    body = json.dumps(report, indent=2).encode("utf-8")
    key = f"_metrics/ingest_yelp_{timestamp}.json"
    client.upload_fileobj(io.BytesIO(body), BUCKET, key)
    log(f"[metrics] rapport sauvegardé -> s3://{BUCKET}/{key}")


def main() -> None:
    log("=== INGESTION BRONZE - Yelp Open Dataset : DEBUT ===")
    t0 = time.time()
    client = get_client()
    metrics: list = []
    upload_json_package(client, os.environ["YELP_JSON_URL"], metrics)
    upload_photos_package(client, os.environ["YELP_PHOTOS_URL"], metrics)
    save_metrics_report(client, metrics)

    total_bytes = sum(m["bytes"] for m in metrics)
    total_records = sum(m["records"] for m in metrics if m["records"] is not None)
    elapsed = time.time() - t0
    log(
        "=== INGESTION BRONZE : TERMINEE === "
        f"{len(metrics)} fichier(s) traité(s), {total_bytes / (1024**3):.2f} GiB, "
        f"{total_records} records, {elapsed:.1f}s au total"
    )


if __name__ == "__main__":
    main()
