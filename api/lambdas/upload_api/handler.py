from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path

import boto3


s3 = boto3.client("s3")


ALLOWED_UPLOAD_TYPES = {
    "prediction": "inference/input",
    "training": "training/raw",
}


def response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "body": json.dumps(body),
    }


def sanitize_file_name(file_name: str) -> str:
    """
    Keep filename safe for S3 key usage.
    """
    base_name = Path(file_name).name
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", base_name)
    return safe_name


def lambda_handler(event, context):
    bucket_name = os.environ["S3_BUCKET_NAME"]

    try:
        body = event.get("body") or "{}"

        if isinstance(body, str):
            payload = json.loads(body)
        else:
            payload = body

        upload_type = payload.get("upload_type")
        file_name = payload.get("file_name")

        if upload_type not in ALLOWED_UPLOAD_TYPES:
            return response(
                400,
                {
                    "message": "Invalid upload_type",
                    "allowed_values": list(ALLOWED_UPLOAD_TYPES.keys()),
                },
            )

        if not file_name:
            return response(400, {"message": "file_name is required"})

        safe_file_name = sanitize_file_name(file_name)

        if not safe_file_name.lower().endswith(".csv"):
            return response(400, {"message": "Only .csv files are allowed"})

        prefix = ALLOWED_UPLOAD_TYPES[upload_type]
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]

        key = f"{prefix}/{timestamp}_{unique_id}_{safe_file_name}"

        upload_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": bucket_name,
                "Key": key,
                "ContentType": "text/csv",
            },
            ExpiresIn=900,
        )

        return response(
            200,
            {
                "bucket": bucket_name,
                "key": key,
                "s3_uri": f"s3://{bucket_name}/{key}",
                "upload_url": upload_url,
                "expires_in_seconds": 900,
                "upload_type": upload_type,
                "content_type": "text/csv",
            },
        )

    except json.JSONDecodeError:
        return response(400, {"message": "Invalid JSON body"})

    except Exception as exc:
        print(f"Unexpected error: {exc}")
        return response(500, {"message": "Internal server error"})
