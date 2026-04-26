from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

import boto3


def is_s3_uri(uri: str | Path) -> bool:
    """
    Check whether a path is an S3 URI.
    """
    return str(uri).startswith("s3://")


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """
    Parse S3 URI into bucket and key.

    Example:
        s3://my-bucket/path/file.csv
        -> ("my-bucket", "path/file.csv")
    """
    parsed = urlparse(uri)

    if parsed.scheme != "s3":
        raise ValueError(f"Invalid S3 URI: {uri}")

    bucket = parsed.netloc
    key = parsed.path.lstrip("/")

    if not bucket:
        raise ValueError(f"S3 URI missing bucket: {uri}")

    return bucket, key


def get_default_s3_uris() -> dict[str, str]:
    """
    Build default S3 URIs from environment variables.

    Required env var:
        S3_BUCKET_NAME
    """
    bucket = os.getenv("S3_BUCKET_NAME")

    if not bucket:
        raise ValueError("S3_BUCKET_NAME environment variable is required for S3 mode")

    return {
        "data_uri": f"s3://{bucket}/training/raw/training_data.csv",
        "output_uri": f"s3://{bucket}/models/candidates",
        "champion_uri": f"s3://{bucket}/models/champion",
    }


def download_s3_file(s3_uri: str, local_path: str | Path) -> Path:
    """
    Download a single S3 object to a local path.
    """
    bucket, key = parse_s3_uri(s3_uri)
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    s3 = boto3.client("s3")
    s3.download_file(bucket, key, str(local_path))

    return local_path


def upload_file_to_s3(local_path: str | Path, s3_uri: str) -> None:
    """
    Upload a single local file to S3.
    """
    bucket, key = parse_s3_uri(s3_uri)
    local_path = Path(local_path)

    if not local_path.exists():
        raise FileNotFoundError(f"Local file not found: {local_path}")

    s3 = boto3.client("s3")
    s3.upload_file(str(local_path), bucket, key)


def upload_directory_to_s3(local_dir: str | Path, s3_uri: str) -> None:
    """
    Upload all files in a local directory recursively to an S3 prefix.
    """
    local_dir = Path(local_dir)

    if not local_dir.exists():
        raise FileNotFoundError(f"Local directory not found: {local_dir}")

    bucket, prefix = parse_s3_uri(s3_uri)
    prefix = prefix.rstrip("/")

    s3 = boto3.client("s3")

    for file_path in local_dir.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(local_dir).as_posix()
            key = f"{prefix}/{relative_path}" if prefix else relative_path
            s3.upload_file(str(file_path), bucket, key)


def download_s3_prefix(s3_uri: str, local_dir: str | Path) -> bool:
    """
    Download an S3 prefix into a local directory.

    Returns
    -------
    bool
        True if at least one object was downloaded, False otherwise.
    """
    bucket, prefix = parse_s3_uri(s3_uri)
    prefix = prefix.rstrip("/") + "/"

    local_dir = Path(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)

    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")

    downloaded_any = False

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            if key.endswith("/"):
                continue

            relative_key = key[len(prefix):]
            local_path = local_dir / relative_key
            local_path.parent.mkdir(parents=True, exist_ok=True)

            s3.download_file(bucket, key, str(local_path))
            downloaded_any = True

    return downloaded_any
