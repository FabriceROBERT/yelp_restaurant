"""Ingestion Bronze : métadonnées photos (photo_id -> business_id -> caption
-> label), extraites de bronze/yelp/photos.zip -> yelp_photos.tar.

Le fichier photos.json est positionné tout à la fin de l'archive (après les
200 100 photos), donc il faut streamer presque tout le tar pour l'atteindre -
~7-8 minutes, mais un seul passage, et on s'arrête dès qu'on l'a trouvé.

Idempotent : si déjà présent dans bronze, le script skip.
"""
import io
import sys
import tarfile
import tempfile
import time
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "conf"))
from s3_client import get_client  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402
from remotezip import RemoteZip  # noqa: E402

BUCKET = "bronze"
SOURCE_KEY = "yelp/photos.zip"
OUTPUT_KEY = "yelp/photos_metadata.json"


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


def main() -> None:
    client = get_client()
    if object_exists(client, OUTPUT_KEY):
        log(f"[photos-meta] skip {OUTPUT_KEY} (déjà présent dans bronze)")
        return

    log("=== INGESTION BRONZE - Métadonnées photos : DEBUT ===")
    t0 = time.time()

    url = client.generate_presigned_url(
        "get_object", Params={"Bucket": BUCKET, "Key": SOURCE_KEY}, ExpiresIn=3600
    )

    with RemoteZip(url) as zf:
        tar_member = next(n for n in zf.namelist() if n.endswith(".tar"))
        with zf.open(tar_member) as tar_stream:
            tmp = tempfile.NamedTemporaryFile(suffix=".tar", delete=False)
            tmp_path = tmp.name
            try:
                while True:
                    chunk = tar_stream.read(16 * 1024 * 1024)
                    if not chunk:
                        break
                    tmp.write(chunk)
                tmp.close()
                log(f"[photos-meta] tar téléchargé en {time.time() - t0:.1f}s, recherche de photos.json...")

                with tarfile.open(tmp_path) as tf:
                    member = tf.getmember("photos.json")
                    data = tf.extractfile(member).read()
            finally:
                os.remove(tmp_path)

    client.upload_fileobj(io.BytesIO(data), BUCKET, OUTPUT_KEY)
    duration = time.time() - t0
    log(f"[photos-meta] {OUTPUT_KEY} -> {len(data) / (1024**2):.1f} MB en {duration:.1f}s")
    log("=== INGESTION BRONZE - Métadonnées photos : TERMINEE ===")


if __name__ == "__main__":
    main()
