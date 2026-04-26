from __future__ import annotations

import json
import os
import time
import uuid
from urllib.parse import unquote_plus

import boto3


stepfunctions = boto3.client("stepfunctions")


def build_s3_uri(bucket: str, key: str) -> str:
    return f"s3://{bucket}/{key}"


def lambda_handler(event, context):
    """
    Trigger Step Functions training pipeline when a CSV file is uploaded to S3.

    Expected S3 event source:
        s3://<bucket>/training/raw/*.csv
    """
    state_machine_arn = os.environ["STATE_MACHINE_ARN"]
    output_uri = os.environ["OUTPUT_URI"]
    champion_uri = os.environ["CHAMPION_URI"]

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

        execution_input = {
            "training_data_uri": training_data_uri,
            "output_uri": output_uri,
            "champion_uri": champion_uri,
            "source": {
                "bucket": bucket,
                "key": key,
                "event_name": record.get("eventName"),
                "event_time": record.get("eventTime"),
            },
        }

        execution_name = (
            f"s3-training-trigger-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        )

        print(f"Starting Step Functions execution: {execution_name}")
        print(json.dumps(execution_input))

        response = stepfunctions.start_execution(
            stateMachineArn=state_machine_arn,
            name=execution_name,
            input=json.dumps(execution_input),
        )

        executions.append(
            {
                "training_data_uri": training_data_uri,
                "execution_arn": response["executionArn"],
                "start_date": response["startDate"].isoformat(),
            }
        )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Training trigger processed",
                "executions": executions,
            }
        ),
    }
