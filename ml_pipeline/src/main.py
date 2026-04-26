from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ml_pipeline.src.artifacts import make_run_id, save_model_artifacts
from ml_pipeline.src.extract import load_csv_data
from ml_pipeline.src.preprocess import split_features_target
from ml_pipeline.src.promote_model import promote_to_champion
from ml_pipeline.src.storage import (
    download_s3_file,
    download_s3_prefix,
    get_default_s3_uris,
    is_s3_uri,
    upload_directory_to_s3,
)
from ml_pipeline.src.train import train_challenger_models
from ml_pipeline.src.validate import load_schema, validate_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ML training pipeline for wizeline-challengeML."
    )

    parser.add_argument(
        "--data-path",
        type=str,
        default=None,
        help="Local path or S3 URI to training CSV file.",
    )

    parser.add_argument(
        "--schema-path",
        type=str,
        default="ml_pipeline/configs/data_schema.yaml",
        help="Path to data schema YAML file.",
    )

    parser.add_argument(
        "--config-path",
        type=str,
        default="ml_pipeline/configs/model_grids.yaml",
        help="Path to model grid configuration YAML file.",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Local directory or S3 URI where candidate model artifacts will be saved.",
    )

    parser.add_argument(
        "--champion-dir",
        type=str,
        default=None,
        help="Local directory or S3 URI where champion model artifacts are stored.",
    )

    parser.add_argument(
        "--models",
        type=str,
        nargs="*",
        default=None,
        help="Optional list of model names to train. If omitted, all enabled models are trained.",
    )

    return parser.parse_args()


def resolve_runtime_paths(args: argparse.Namespace) -> dict[str, str]:
    """
    Resolve runtime paths.

    Priority:
    1. CLI arguments.
    2. Explicit environment variables:
       - TRAINING_DATA_URI
       - OUTPUT_URI
       - CHAMPION_URI
    3. S3 defaults if S3_BUCKET_NAME is present.
    4. Local defaults.
    """
    env_data_uri = os.getenv("TRAINING_DATA_URI")
    env_output_uri = os.getenv("OUTPUT_URI")
    env_champion_uri = os.getenv("CHAMPION_URI")

    if args.data_path and args.output_dir and args.champion_dir:
        return {
            "data_path": args.data_path,
            "output_dir": args.output_dir,
            "champion_dir": args.champion_dir,
        }

    if env_data_uri and env_output_uri and env_champion_uri:
        return {
            "data_path": args.data_path or env_data_uri,
            "output_dir": args.output_dir or env_output_uri,
            "champion_dir": args.champion_dir or env_champion_uri,
        }

    if os.getenv("S3_BUCKET_NAME"):
        default_s3_uris = get_default_s3_uris()
        return {
            "data_path": args.data_path or env_data_uri or default_s3_uris["data_uri"],
            "output_dir": args.output_dir or env_output_uri or default_s3_uris["output_uri"],
            "champion_dir": args.champion_dir or env_champion_uri or default_s3_uris["champion_uri"],
        }

    return {
        "data_path": args.data_path or "ml_pipeline/data/training_data.csv",
        "output_dir": args.output_dir or "ml_pipeline/artifacts",
        "champion_dir": args.champion_dir or "ml_pipeline/artifacts/champion",
    }


def prepare_data_path(data_path: str) -> Path:
    """
    Prepare local data path.

    If data_path is S3, download it to /tmp.
    """
    if is_s3_uri(data_path):
        local_data_path = Path("/tmp/ml_pipeline/data/training_data.csv")
        print(f"Downloading training data from S3: {data_path}")
        download_s3_file(data_path, local_data_path)
        return local_data_path

    return Path(data_path)


def prepare_champion_dir(champion_dir: str) -> Path:
    """
    Prepare local champion directory.

    If champion_dir is S3, download existing champion artifacts to /tmp.
    If the prefix does not exist yet, return an empty local directory.
    """
    if is_s3_uri(champion_dir):
        local_champion_dir = Path("/tmp/ml_pipeline/artifacts/champion")
        print(f"Checking existing champion artifacts from S3: {champion_dir}")
        downloaded = download_s3_prefix(champion_dir, local_champion_dir)

        if downloaded:
            print(f"Downloaded existing champion artifacts to: {local_champion_dir}")
        else:
            print("No existing champion artifacts found in S3")

        return local_champion_dir

    return Path(champion_dir)


def prepare_output_base_dir(output_dir: str) -> Path:
    """
    Prepare local candidate output base directory.

    If output_dir is S3, use /tmp as local staging area.
    """
    if is_s3_uri(output_dir):
        return Path("/tmp/ml_pipeline/artifacts/candidates")

    return Path(output_dir)


def sync_artifacts_if_needed(
    output_dir: str,
    champion_dir: str,
    artifact_dir: Path,
    local_champion_dir: Path,
    run_id: str,
) -> dict[str, str | None]:
    """
    Upload candidate and champion artifacts to S3 when running in S3 mode.
    """
    uploaded_paths = {
        "candidate_s3_uri": None,
        "champion_s3_uri": None,
    }

    if is_s3_uri(output_dir):
        candidate_s3_uri = f"{output_dir.rstrip('/')}/{run_id}"
        print(f"Uploading candidate artifacts to S3: {candidate_s3_uri}")
        upload_directory_to_s3(artifact_dir, candidate_s3_uri)
        uploaded_paths["candidate_s3_uri"] = candidate_s3_uri

    if is_s3_uri(champion_dir):
        print(f"Uploading champion artifacts to S3: {champion_dir}")
        upload_directory_to_s3(local_champion_dir, champion_dir)
        uploaded_paths["champion_s3_uri"] = champion_dir

    return uploaded_paths


def main() -> None:
    args = parse_args()
    runtime_paths = resolve_runtime_paths(args)

    raw_data_path = runtime_paths["data_path"]
    raw_output_dir = runtime_paths["output_dir"]
    raw_champion_dir = runtime_paths["champion_dir"]

    data_path = prepare_data_path(raw_data_path)
    output_base_dir = prepare_output_base_dir(raw_output_dir)
    champion_dir = prepare_champion_dir(raw_champion_dir)

    schema_path = Path(args.schema_path)
    config_path = Path(args.config_path)

    print("Starting ML training pipeline")
    print(f"Raw data path: {raw_data_path}")
    print(f"Resolved data path: {data_path}")
    print(f"Schema path: {schema_path}")
    print(f"Config path: {config_path}")
    print(f"Raw output dir: {raw_output_dir}")
    print(f"Local output base dir: {output_base_dir}")
    print(f"Raw champion dir: {raw_champion_dir}")
    print(f"Local champion dir: {champion_dir}")

    df = load_csv_data(data_path)
    schema = load_schema(schema_path)
    config = load_schema(config_path)

    validate_dataset(df, schema)
    X, y = split_features_target(df, schema)

    print("Dataset validation passed")
    print(f"Dataset shape: {df.shape}")
    print(f"Feature matrix shape: {X.shape}")
    print(f"Target shape: {y.shape}")

    training_output = train_challenger_models(
        X=X,
        y=y,
        config=config,
        enabled_model_names=args.models,
    )

    best_model = training_output["best_model"]
    run_id = make_run_id()
    artifact_dir = output_base_dir / run_id

    artifact_paths = save_model_artifacts(
        best_model_result=best_model,
        output_dir=artifact_dir,
        run_id=run_id,
        extra_metadata={
            "dataset_path": str(raw_data_path),
            "schema_path": str(schema_path),
            "config_path": str(config_path),
            "target_column": schema["dataset"]["target_column"],
            "feature_count": len(schema["features"]),
            "primary_metric": training_output["primary_metric"],
            "train_size": training_output["train_size"],
            "test_size": training_output["test_size"],
            "candidate_models": [
                result["model_name"] for result in training_output["results"]
            ],
        },
    )

    promotion_config = config.get("promotion", {})
    min_improvement_pct = float(promotion_config.get("min_improvement_pct", 0.0))

    promotion_decision = promote_to_champion(
        challenger_artifact_dir=artifact_dir,
        champion_dir=champion_dir,
        primary_metric=training_output["primary_metric"],
        min_improvement_pct=min_improvement_pct,
    )

    uploaded_paths = sync_artifacts_if_needed(
        output_dir=raw_output_dir,
        champion_dir=raw_champion_dir,
        artifact_dir=artifact_dir,
        local_champion_dir=champion_dir,
        run_id=run_id,
    )

    summary = {
        "run_id": run_id,
        "best_challenger_model": best_model["model_name"],
        "best_challenger_params": best_model["best_params"],
        "best_challenger_metrics": best_model["metrics"],
        "artifact_paths": artifact_paths,
        "uploaded_paths": uploaded_paths,
        "promotion_decision": promotion_decision,
    }

    print("\nTraining pipeline completed successfully")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
