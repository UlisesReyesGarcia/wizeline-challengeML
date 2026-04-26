from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib


def make_run_id() -> str:
    """
    Create a timestamp-based run id.
    """
    return datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")


def save_model_artifacts(
    best_model_result: dict[str, Any],
    output_dir: str | Path,
    run_id: str,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, str]:
    """
    Save model artifact, metrics and metadata locally.

    Parameters
    ----------
    best_model_result:
        Best model dictionary returned by train_challenger_models.
    output_dir:
        Directory where artifacts will be stored.
    run_id:
        Training run identifier.
    extra_metadata:
        Optional metadata to enrich metadata.json.

    Returns
    -------
    dict
        Paths of saved artifacts.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = output_dir / "model.pkl"
    metrics_path = output_dir / "metrics.json"
    metadata_path = output_dir / "metadata.json"

    best_estimator = best_model_result["best_estimator"]

    joblib.dump(best_estimator, model_path)

    metrics = best_model_result["metrics"]

    metrics_payload = {
        "run_id": run_id,
        "model_name": best_model_result["model_name"],
        "model_type": best_model_result["model_type"],
        "best_params": best_model_result["best_params"],
        "best_cv_score_rmse": best_model_result["best_cv_score_rmse"],
        "metrics": metrics,
    }

    metadata_payload = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_name": best_model_result["model_name"],
        "model_type": best_model_result["model_type"],
        "artifact_file": "model.pkl",
        "metrics_file": "metrics.json",
        "metadata_file": "metadata.json",
    }

    if extra_metadata:
        metadata_payload.update(extra_metadata)

    with metrics_path.open("w", encoding="utf-8") as file:
        json.dump(metrics_payload, file, indent=2)

    with metadata_path.open("w", encoding="utf-8") as file:
        json.dump(metadata_payload, file, indent=2)

    return {
        "model_path": str(model_path),
        "metrics_path": str(metrics_path),
        "metadata_path": str(metadata_path),
    }


def load_model(model_path: str | Path):
    """
    Load a serialized model artifact.
    """
    model_path = Path(model_path)

    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {model_path}")

    return joblib.load(model_path)
