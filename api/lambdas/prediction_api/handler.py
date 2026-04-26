from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

import boto3
import joblib
import pandas as pd
import yaml


s3 = boto3.client("s3")


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


def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {s3_uri}")

    without_scheme = s3_uri.replace("s3://", "", 1)
    bucket, key = without_scheme.split("/", 1)

    return bucket, key


def download_s3_file(s3_uri: str, local_path: str | Path) -> Path:
    bucket, key = parse_s3_uri(s3_uri)
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    s3.download_file(bucket, key, str(local_path))

    return local_path


def upload_file_to_s3(local_path: str | Path, s3_uri: str) -> None:
    bucket, key = parse_s3_uri(s3_uri)
    s3.upload_file(str(local_path), bucket, key)


def load_schema(schema_path: str | Path) -> dict:
    with Path(schema_path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def validate_prediction_dataset(df: pd.DataFrame, schema: dict) -> None:
    features = schema["features"]

    missing_columns = [col for col in features if col not in df.columns]
    extra_columns = [col for col in df.columns if col not in features]

    if missing_columns:
        raise ValueError(f"Missing feature columns: {missing_columns}")

    if extra_columns:
        raise ValueError(f"Extra columns in prediction dataset: {extra_columns}")

    if df.isna().sum().sum() > 0:
        raise ValueError("Prediction dataset contains missing values")

    non_numeric_columns = [
        col for col in features if not pd.api.types.is_numeric_dtype(df[col])
    ]

    if non_numeric_columns:
        raise ValueError(f"Non-numeric feature columns found: {non_numeric_columns}")


def lambda_handler(event, context):
    try:
        body = event.get("body") or "{}"

        if isinstance(body, str):
            payload = json.loads(body)
        else:
            payload = body

        input_s3_uri = payload.get("input_s3_uri") or payload.get("s3_uri")

        if not input_s3_uri:
            return response(400, {"message": "input_s3_uri is required"})

        if not input_s3_uri.endswith(".csv"):
            return response(400, {"message": "Only .csv input files are allowed"})

        bucket_name = os.environ["S3_BUCKET_NAME"]
        champion_model_uri = os.environ.get(
            "CHAMPION_MODEL_URI",
            f"s3://{bucket_name}/models/champion/model.pkl",
        )
        output_prefix_uri = os.environ.get(
            "PREDICTION_OUTPUT_URI",
            f"s3://{bucket_name}/inference/output",
        )

        job_id = f"prediction_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        local_input_path = Path(f"/tmp/{job_id}_input.csv")
        local_model_path = Path(f"/tmp/{job_id}_model.pkl")
        local_output_path = Path(f"/tmp/{job_id}_predictions.csv")

        schema_path = Path("ml_pipeline/configs/data_schema.yaml")
        schema = load_schema(schema_path)
        features = schema["features"]

        print(f"Downloading input CSV: {input_s3_uri}")
        download_s3_file(input_s3_uri, local_input_path)

        print(f"Downloading champion model: {champion_model_uri}")
        download_s3_file(champion_model_uri, local_model_path)

        df = pd.read_csv(local_input_path)
        validate_prediction_dataset(df, schema)

        X = df[features].copy()

        model = joblib.load(local_model_path)
        predictions = model.predict(X)

        output_df = df.copy()
        output_df["prediction"] = predictions

        output_df.to_csv(local_output_path, index=False)

        output_s3_uri = f"{output_prefix_uri.rstrip('/')}/{job_id}_predictions.csv"

        print(f"Uploading predictions to: {output_s3_uri}")
        upload_file_to_s3(local_output_path, output_s3_uri)

        return response(
            200,
            {
                "message": "Batch prediction completed successfully",
                "job_id": job_id,
                "input_s3_uri": input_s3_uri,
                "output_s3_uri": output_s3_uri,
                "champion_model_uri": champion_model_uri,
                "rows_scored": int(len(output_df)),
                "prediction_column": "prediction",
            },
        )

    except ValueError as exc:
        print(f"Validation error: {exc}")
        return response(400, {"message": str(exc)})

    except Exception as exc:
        print(f"Unexpected error: {exc}")
        return response(500, {"message": "Internal server error"})
