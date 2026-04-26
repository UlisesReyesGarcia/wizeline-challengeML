from __future__ import annotations

import json
import os

import boto3


s3 = boto3.client("s3")


def response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "OPTIONS,GET",
        },
        "body": json.dumps(body),
    }


def read_json_from_s3(bucket: str, key: str) -> dict | None:
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        content = obj["Body"].read().decode("utf-8")
        return json.loads(content)

    except s3.exceptions.NoSuchKey:
        return None


def lambda_handler(event, context):
    try:
        bucket_name = os.environ["S3_BUCKET_NAME"]
        champion_prefix = os.environ.get("CHAMPION_PREFIX", "models/champion")

        metadata_key = f"{champion_prefix}/metadata.json"
        metrics_key = f"{champion_prefix}/metrics.json"
        promotion_key = f"{champion_prefix}/promotion_decision.json"

        metadata = read_json_from_s3(bucket_name, metadata_key)
        metrics = read_json_from_s3(bucket_name, metrics_key)
        promotion_decision = read_json_from_s3(bucket_name, promotion_key)

        if metadata is None and metrics is None:
            return response(
                404,
                {
                    "message": "Champion model metadata was not found",
                    "bucket": bucket_name,
                    "champion_prefix": champion_prefix,
                },
            )

        return response(
            200,
            {
                "bucket": bucket_name,
                "champion_prefix": champion_prefix,
                "model_uri": f"s3://{bucket_name}/{champion_prefix}/model.pkl",
                "metadata_uri": f"s3://{bucket_name}/{metadata_key}",
                "metrics_uri": f"s3://{bucket_name}/{metrics_key}",
                "promotion_decision_uri": f"s3://{bucket_name}/{promotion_key}",
                "metadata": metadata,
                "metrics": metrics,
                "promotion_decision": promotion_decision,
            },
        )

    except Exception as exc:
        print(f"Unexpected error: {exc}")
        return response(500, {"message": "Internal server error"})
