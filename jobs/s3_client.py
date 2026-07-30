"""Client MinIO partagé entre les scripts jobs/."""
import os

import boto3
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()


def get_client():
    endpoint = f"http://localhost:{os.environ.get('MINIO_API_PORT', '9000')}"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
