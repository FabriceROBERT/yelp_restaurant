"""Extrait quelques photos d'exemple depuis bronze/yelp/photos.zip sans
télécharger l'archive entière (6.9 Go).

Structure réelle de l'archive (comme pour le JSON) : le zip contient un
yelp_photos.tar, qui contient lui-même les .jpg. On lit uniquement le début
du flux décompressé du tar (quelques Mo, via une URL pré-signée MinIO en
streaming) - largement assez pour y trouver les premières photos - au lieu
de tout télécharger.

Usage:
    python utils/peek_photo.py                  # extrait 3 photos par défaut
    python utils/peek_photo.py --count 5
"""
import argparse
import os
import sys
import tarfile
import tempfile

from remotezip import RemoteZip

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "conf"))
from s3_client import get_client  # noqa: E402

BUCKET = "bronze"
KEY = "yelp/photos.zip"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "out", "sample_photos")
PARTIAL_TAR_BYTES = 20 * 1024 * 1024  # large marge pour trouver `count` photos


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=3, help="Nombre de photos à extraire")
    args = parser.parse_args()

    client = get_client()
    url = client.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": KEY}, ExpiresIn=600)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with RemoteZip(url) as zf:
        tar_member = next(n for n in zf.namelist() if n.endswith(".tar"))
        print(f"lecture partielle de {tar_member} (max {PARTIAL_TAR_BYTES / (1024**2):.0f} MB)...")

        tmp = tempfile.NamedTemporaryFile(suffix=".tar", delete=False)
        tmp_path = tmp.name
        try:
            with zf.open(tar_member) as tar_stream:
                remaining = PARTIAL_TAR_BYTES
                while remaining > 0:
                    chunk = tar_stream.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    tmp.write(chunk)
                    remaining -= len(chunk)
            tmp.close()

            saved = 0
            tf = tarfile.open(tmp_path)
            while saved < args.count:
                try:
                    member = tf.next()
                except Exception:
                    break  # coupure normale : on s'est arrêté en plein milieu d'une entrée
                if member is None:
                    break
                if not member.name.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue
                data = tf.extractfile(member).read()
                out_path = os.path.join(OUTPUT_DIR, os.path.basename(member.name))
                with open(out_path, "wb") as f:
                    f.write(data)
                print(f"[ok] {member.name} -> {out_path} ({len(data) / 1024:.1f} KB)")
                saved += 1
            tf.close()
        finally:
            os.remove(tmp_path)


if __name__ == "__main__":
    main()
