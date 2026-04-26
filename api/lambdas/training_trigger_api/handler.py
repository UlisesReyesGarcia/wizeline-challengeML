from __future__ import annotations

import json
import os
import time
import uuid
from urllib.parse import unquote_plus

import boto3


stepfunctions = boto3.client("stepfunctions")


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


def build_s3_uri(bucket: str, key: str) -> str:
    return f"s3://{bucket}/{key}"


def parse_event_body(event) -> dict:
    body = event.get("body") or "{}"

    if isinstance(body, str):
        return json.loads(body)

    return body


def validate_training_data_uri(training_data_uri: str, bucket_name: str) -> None:
    expected_prefix = f"s3://{bucket_name}/training/raw/"

    if not training_data_uri.startswith(expected_prefix):
        raise ValueError(
            f"training_data_uri must be under {expected_prefix}"
        )

    if not training_data_uri.endswith(".csv"):
        raise ValueError("Only .csv training files are allowed")


def start_training_execution(
    training_data_uri: str,
    source: dict,
) -> dict:
    state_machine_arn = os.environ["STATE_MACHINE_ARN"]
    output_uri = os.environ["OUTPUT_URI"]
    champion_uri = os.environ["CHAMPION_URI"]

    execution_input = {
        "training_data_uri": training_data_uri,
        "output_uri": output_uri,
        "champion_uri": champion_uri,
        "source": source,
    }

    execution_name = (
        f"training-trigger-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    )

    print(f"Starting Step Functions execution: {execution_name}")
    print(json.dumps(execution_input))

    stepfunctions_response = stepfunctions.start_execution(
        stateMachineArn=state_machine_arn,
        name=execution_name,
        input=json.dumps(execution_input),
    )

    return {
        "training_data_uri": training_data_uri,
        "execution_name": execution_name,
        "execution_arn": stepfunctions_response["executionArn"],
        "start_date": stepfunctions_response["startDate"].isoformat(),
    }


def handle_s3_event(event) -> dict:
    bucket_name = os.environ["S3_BUCKET_NAME"]
    executions = []

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        if key.endswith("/"):
            print(f"Skipping folder-like object: s3://{bucket}/{key}")
            continue

        if not key.endswith(".csv"):
            print(f"Skipping non-CSV object: s3://{bucket}/{key}")
            continue

        training_data_uri = build_s3_uri(bucket, key)
        validate_training_data_uri(training_data_uri, bucket_name)

        execution = start_training_execution(
            training_data_uri=training_data_uri,
            source={
                "trigger_type": "s3",
                "bucket": bucket,
                "key": key,
                "event_name": record.get("eventName"),
                "event_time": record.get("eventTime"),
            },
        )

        executions.append(execution)

    return response(
        200,
        {
            "message": "S3 training trigger processed",
            "executions": executions,
        },
    )


def handle_api_event(event) -> dict:
    bucket_name = os.environ["S3_BUCKET_NAME"]
    payload = parse_event_body(event)

    default_training_data_uri = (
        f"s3://{bucket_name}/training/raw/training_data.csv"
    )

    training_data_uri = (
        payload.get("training_data_uri")
        or payload.get("input_s3_uri")
        or default_training_data_uri
    )

    validate_training_data_uri(training_data_uri, bucket_name)

    execution = start_training_execution(
        training_data_uri=training_data_uri,
        source={
            "trigger_type": "api",
            "requested_training_data_uri": training_data_uri,
        },
    )

    return response(
        200,
        {
            "message": "Manual retraining started",
            "execution": execution,
        },
    )


def lambda_handler(event, context):
    try:
        if event.get("Records"):
            return handle_s3_event(event)

        return handle_api_event(event)

    except json.JSONDecodeError:
        return response(400, {"message": "Invalid JSON body"})

    except ValueError as exc:
        print(f"Validation error: {exc}")
        return response(400, {"message": str(exc)})

    except Exception as exc:
        print(f"Unexpected error: {exc}")
        return response(500, {"message": "Internal server error"})
