from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml_pipeline.src.artifacts import make_run_id, save_model_artifacts
from ml_pipeline.src.extract import load_csv_data
from ml_pipeline.src.preprocess import split_features_target
from ml_pipeline.src.promote_model import promote_to_champion
from ml_pipeline.src.train import train_challenger_models
from ml_pipeline.src.validate import load_schema, validate_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local ML training pipeline for wizeline-challengeML."
    )

    parser.add_argument(
        "--data-path",
        type=str,
        default="ml_pipeline/data/training_data.csv",
        help="Path to training CSV file.",
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
        default="ml_pipeline/artifacts",
        help="Base directory where model artifacts will be saved.",
    )

    parser.add_argument(
        "--champion-dir",
        type=str,
        default="ml_pipeline/artifacts/champion",
        help="Directory where champion model artifacts are stored.",
    )

    parser.add_argument(
        "--models",
        type=str,
        nargs="*",
        default=None,
        help="Optional list of model names to train. If omitted, all enabled models are trained.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    data_path = Path(args.data_path)
    schema_path = Path(args.schema_path)
    config_path = Path(args.config_path)
    output_base_dir = Path(args.output_dir)
    champion_dir = Path(args.champion_dir)

    print("Starting ML training pipeline")
    print(f"Data path: {data_path}")
    print(f"Schema path: {schema_path}")
    print(f"Config path: {config_path}")
    print(f"Output base dir: {output_base_dir}")
    print(f"Champion dir: {champion_dir}")

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
            "dataset_path": str(data_path),
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

    summary = {
        "run_id": run_id,
        "best_challenger_model": best_model["model_name"],
        "best_challenger_params": best_model["best_params"],
        "best_challenger_metrics": best_model["metrics"],
        "artifact_paths": artifact_paths,
        "promotion_decision": promotion_decision,
    }

    print("\nTraining pipeline completed successfully")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
