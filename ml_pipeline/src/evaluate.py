from __future__ import annotations

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def calculate_regression_metrics(y_true, y_pred) -> dict:
    """
    Calculate standard regression metrics.
    """
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))

    return {
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
    }


def select_best_model(results: list[dict], primary_metric: str = "rmse") -> dict:
    """
    Select the best model based on the primary metric.

    For RMSE and MAE, lower is better.
    For R2, higher is better.
    """
    if not results:
        raise ValueError("No model results were provided")

    if primary_metric in {"rmse", "mae"}:
        return min(results, key=lambda item: item["metrics"][primary_metric])

    if primary_metric == "r2":
        return max(results, key=lambda item: item["metrics"][primary_metric])

    raise ValueError(f"Unsupported primary metric: {primary_metric}")
