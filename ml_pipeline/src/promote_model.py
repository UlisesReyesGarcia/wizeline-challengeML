from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def load_json(file_path: str | Path) -> dict[str, Any]:
    """
    Load a JSON file.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_metric_from_metrics_payload(metrics_payload: dict[str, Any], metric_name: str) -> float:
    """
    Extract metric value from metrics.json payload.
    """
    return float(metrics_payload["metrics"][metric_name])


def should_promote_challenger(
    challenger_metrics: dict[str, Any],
    champion_metrics: dict[str, Any] | None,
    primary_metric: str = "rmse",
    min_improvement_pct: float = 0.0,
) -> tuple[bool, str]:
    """
    Decide whether challenger should be promoted.

    For RMSE and MAE, lower is better.
    For R2, higher is better.
    """
    if champion_metrics is None:
        return True, "No existing champion found"

    challenger_value = get_metric_from_metrics_payload(challenger_metrics, primary_metric)
    champion_value = get_metric_from_metrics_payload(champion_metrics, primary_metric)

    if primary_metric in {"rmse", "mae"}:
        required_value = champion_value * (1 - min_improvement_pct / 100)

        if challenger_value < required_value:
            return (
                True,
                f"Challenger improved {primary_metric}: "
                f"{challenger_value:.6f} < required threshold {required_value:.6f}",
            )

        return (
            False,
            f"Challenger did not improve {primary_metric}: "
            f"{challenger_value:.6f} >= required threshold {required_value:.6f}",
        )

    if primary_metric == "r2":
        required_value = champion_value * (1 + min_improvement_pct / 100)

        if challenger_value > required_value:
            return (
                True,
                f"Challenger improved {primary_metric}: "
                f"{challenger_value:.6f} > required threshold {required_value:.6f}",
            )

        return (
            False,
            f"Challenger did not improve {primary_metric}: "
            f"{challenger_value:.6f} <= required threshold {required_value:.6f}",
        )

    raise ValueError(f"Unsupported primary metric: {primary_metric}")


def promote_to_champion(
    challenger_artifact_dir: str | Path,
    champion_dir: str | Path,
    primary_metric: str = "rmse",
    min_improvement_pct: float = 0.0,
) -> dict[str, Any]:
    """
    Promote a challenger artifact directory to champion if it improves the current champion.

    Parameters
    ----------
    challenger_artifact_dir:
        Directory containing challenger model.pkl, metrics.json and metadata.json.
    champion_dir:
        Directory where current champion artifacts are stored.
    primary_metric:
        Metric used for promotion decision.
    min_improvement_pct:
        Minimum percentage improvement required to promote.

    Returns
    -------
    dict
        Promotion decision payload.
    """
    challenger_artifact_dir = Path(challenger_artifact_dir)
    champion_dir = Path(champion_dir)

    challenger_metrics_path = challenger_artifact_dir / "metrics.json"
    challenger_metadata_path = challenger_artifact_dir / "metadata.json"
    challenger_model_path = challenger_artifact_dir / "model.pkl"

    if not challenger_metrics_path.exists():
        raise FileNotFoundError(f"Challenger metrics not found: {challenger_metrics_path}")

    if not challenger_metadata_path.exists():
        raise FileNotFoundError(f"Challenger metadata not found: {challenger_metadata_path}")

    if not challenger_model_path.exists():
        raise FileNotFoundError(f"Challenger model not found: {challenger_model_path}")

    challenger_metrics = load_json(challenger_metrics_path)
    challenger_metadata = load_json(challenger_metadata_path)

    champion_metrics_path = champion_dir / "metrics.json"

    champion_metrics = None
    if champion_metrics_path.exists():
        champion_metrics = load_json(champion_metrics_path)

    promote, reason = should_promote_challenger(
        challenger_metrics=challenger_metrics,
        champion_metrics=champion_metrics,
        primary_metric=primary_metric,
        min_improvement_pct=min_improvement_pct,
    )

    decision = {
        "promoted": promote,
        "reason": reason,
        "primary_metric": primary_metric,
        "min_improvement_pct": min_improvement_pct,
        "challenger_run_id": challenger_metrics["run_id"],
        "challenger_model_name": challenger_metrics["model_name"],
        "challenger_metrics": challenger_metrics["metrics"],
        "previous_champion_run_id": (
            champion_metrics["run_id"] if champion_metrics is not None else None
        ),
        "previous_champion_model_name": (
            champion_metrics["model_name"] if champion_metrics is not None else None
        ),
        "previous_champion_metrics": (
            champion_metrics["metrics"] if champion_metrics is not None else None
        ),
    }

    if promote:
        champion_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(challenger_model_path, champion_dir / "model.pkl")
        shutil.copy2(challenger_metrics_path, champion_dir / "metrics.json")
        shutil.copy2(challenger_metadata_path, champion_dir / "metadata.json")

        decision_path = champion_dir / "promotion_decision.json"
        with decision_path.open("w", encoding="utf-8") as file:
            json.dump(decision, file, indent=2)

        decision["champion_dir"] = str(champion_dir)
        decision["decision_path"] = str(decision_path)

    return decision
