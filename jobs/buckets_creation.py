"""Crée les buckets MinIO bronze/silver/gold s'ils n'existent pas."""
import os
import sys

from botocore.exceptions import ClientError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "conf"))
from s3_client import get_client  # noqa: E402

BUCKETS = ["bronze", "silver", "gold"]


def ensure_bucket(client, name: str) -> None:
    try:
        client.head_bucket(Bucket=name)
        print(f"[skip] bucket '{name}' already exists")
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "404":
            raise
        client.create_bucket(Bucket=name)
        print(f"[ok] bucket '{name}' created")


def main() -> None:
    client = get_client()
    for bucket in BUCKETS:
        ensure_bucket(client, bucket)


if __name__ == "__main__":
    main()
