"""Étape de préparation pour Silver/photos : extrait un échantillon de photos
individuelles depuis bronze/yelp/photos.zip (zip -> tar imbriqué) et les
uploade une par une dans bronze/yelp/photos_sample/.

Nécessaire car Spark (binaryFile format) lit des fichiers individuels dans un
chemin, pas une archive tar imbriquée dans un zip - cette étape "déballe"
juste un échantillon gérable (le zip complet fait 200k photos / 6.9 Go, trop
pour nos 2 workers à 2 Go de RAM chacun).

Usage:
    python jobs/prepare_silver_photos_sample.py --count 5000
"""
import argparse
import io
import os
import sys
import tarfile
import tempfile
import time

from remotezip import RemoteZip

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "conf"))
from s3_client import get_client  # noqa: E402

BUCKET = "bronze"
SOURCE_KEY = "yelp/photos.zip"
SAMPLE_PREFIX = "yelp/photos_sample/"


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5000, help="Nombre de photos à extraire")
    args = parser.parse_args()

    client = get_client()

    existing = client.list_objects_v2(Bucket=BUCKET, Prefix=SAMPLE_PREFIX, MaxKeys=1)
    if existing.get("KeyCount"):
        log(f"[photos-sample] skip : {SAMPLE_PREFIX} contient déjà des fichiers")
        return

    log(f"=== PREPARATION Silver/photos : échantillon de {args.count} photos ===")
    t0 = time.time()

    url = client.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": SOURCE_KEY}, ExpiresIn=1800)
    saved = 0
    with RemoteZip(url) as zf:
        tar_member = next(n for n in zf.namelist() if n.endswith(".tar"))
        with zf.open(tar_member) as tar_stream:
            tmp = tempfile.NamedTemporaryFile(suffix=".tar", delete=False)
            tmp_path = tmp.name
            try:
                # Lecture séquentielle limitée : largement assez d'octets pour
                # couvrir `count` photos (taille moyenne ~35 Ko/photo).
                target_bytes = args.count * 60 * 1024
                remaining = target_bytes
                while remaining > 0:
                    chunk = tar_stream.read(min(4 * 1024 * 1024, remaining))
                    if not chunk:
                        break
                    tmp.write(chunk)
                    remaining -= len(chunk)
                tmp.close()

                tf = tarfile.open(tmp_path)
                while saved < args.count:
                    try:
                        member = tf.next()
                    except Exception:
                        break
                    if member is None:
                        break
                    if not member.name.lower().endswith((".jpg", ".jpeg", ".png")):
                        continue
                    data = tf.extractfile(member).read()
                    key = f"{SAMPLE_PREFIX}{os.path.basename(member.name)}"
                    client.upload_fileobj(io.BytesIO(data), BUCKET, key)
                    saved += 1
                    if saved % 500 == 0:
                        log(f"[photos-sample] {saved}/{args.count} extraites...")
                tf.close()
            finally:
                os.remove(tmp_path)

    duration = time.time() - t0
    log(f"[photos-sample] {saved} photos uploadées dans s3://{BUCKET}/{SAMPLE_PREFIX} en {duration:.1f}s")


if __name__ == "__main__":
    main()
