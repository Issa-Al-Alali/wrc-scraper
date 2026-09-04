from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from common.config import get_settings


@lru_cache
def get_s3_client() -> BaseClient:
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint_url,
        aws_access_key_id=settings.minio_root_user,
        aws_secret_access_key=settings.minio_root_password,
    )


def ensure_bucket(bucket: str) -> None:
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)


def upload_bytes(bucket: str, key: str, data: bytes, content_type: str | None = None) -> None:
    client = get_s3_client()
    extra_args = {"ContentType": content_type} if content_type else {}
    client.put_object(Bucket=bucket, Key=key, Body=data, **extra_args)


def download_bytes(bucket: str, key: str) -> bytes:
    client = get_s3_client()
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def object_exists(bucket: str, key: str) -> bool:
    client = get_s3_client()
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False