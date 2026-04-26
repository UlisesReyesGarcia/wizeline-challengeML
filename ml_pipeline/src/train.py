from __future__ import annotations

import importlib
from typing import Any

from sklearn.model_selection import GridSearchCV, train_test_split

from ml_pipeline.src.evaluate import calculate_regression_metrics, select_best_model


def load_class(class_path: str):
    """
    Dynamically load a class from a string path.

    Example:
        sklearn.linear_model.Ridge
        xgboost.XGBRegressor
    """
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def build_model(model_config: dict):
    """
    Build a model instance from model configuration.
    """
    model_class = load_class(model_config["type"])
    return model_class()


def train_single_model(
    model_name: str,
    model_config: dict,
    X_train,
    y_train,
    X_test,
    y_test,
    cv_folds: int,
) -> dict[str, Any]:
    """
    Train one model using GridSearchCV and evaluate it on the test set.
    """
    model = build_model(model_config)

    grid_search = GridSearchCV(
        estimator=model,
        param_grid=model_config["param_grid"],
        scoring="neg_root_mean_squared_error",
        cv=cv_folds,
        n_jobs=-1,
        refit=True,
    )

    grid_search.fit(X_train, y_train)

    best_estimator = grid_search.best_estimator_
    y_pred = best_estimator.predict(X_test)

    metrics = calculate_regression_metrics(y_test, y_pred)

    return {
        "model_name": model_name,
        "model_type": model_config["type"],
        "best_estimator": best_estimator,
        "best_params": grid_search.best_params_,
        "best_cv_score_rmse": float(-grid_search.best_score_),
        "metrics": metrics,
    }


def train_challenger_models(
    X,
    y,
    config: dict,
    enabled_model_names: list[str] | None = None,
) -> dict[str, Any]:
    """
    Train all enabled challenger models and select the best one.

    Parameters
    ----------
    X:
        Feature matrix.
    y:
        Target vector.
    config:
        Model configuration loaded from model_grids.yaml.
    enabled_model_names:
        Optional list of model names to train. Useful for smoke tests.

    Returns
    -------
    dict
        Dictionary with all model results and best model result.
    """
    test_size = config["test_size"]
    random_state = config["random_state"]
    cv_folds = config["cv_folds"]
    primary_metric = config["primary_metric"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
    )

    results = []

    for model_name, model_config in config["models"].items():
        if not model_config.get("enabled", False):
            continue

        if enabled_model_names is not None and model_name not in enabled_model_names:
            continue

        print(f"Training model: {model_name}")

        result = train_single_model(
            model_name=model_name,
            model_config=model_config,
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
            cv_folds=cv_folds,
        )

        print(
            f"Finished {model_name} | "
            f"RMSE={result['metrics']['rmse']:.6f} | "
            f"MAE={result['metrics']['mae']:.6f} | "
            f"R2={result['metrics']['r2']:.6f}"
        )

        results.append(result)

    best_model = select_best_model(results, primary_metric=primary_metric)

    return {
        "results": results,
        "best_model": best_model,
        "primary_metric": primary_metric,
        "train_size": len(X_train),
        "test_size": len(X_test),
    }
