from pathlib import Path

import pandas as pd
import yaml


def load_schema(schema_path: str | Path) -> dict:
    """
    Load YAML schema file.
    """
    schema_path = Path(schema_path)

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with schema_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def validate_dataset(df: pd.DataFrame, schema: dict) -> None:
    """
    Validate dataset columns, target, nulls and numeric types.

    Raises
    ------
    ValueError
        If validation fails.
    """
    expected_columns = schema["expected_columns"]
    target_column = schema["dataset"]["target_column"]
    features = schema["features"]

    missing_columns = [col for col in expected_columns if col not in df.columns]
    extra_columns = [col for col in df.columns if col not in expected_columns]

    if missing_columns:
        raise ValueError(f"Missing columns: {missing_columns}")

    if extra_columns:
        raise ValueError(f"Extra columns: {extra_columns}")

    if target_column not in df.columns:
        raise ValueError(f"Target column not found: {target_column}")

    if len(features) != 20:
        raise ValueError(f"Expected 20 features, got {len(features)}")

    if df.isna().sum().sum() > 0:
        raise ValueError("Dataset contains missing values")

    non_numeric_columns = [
        col for col in expected_columns if not pd.api.types.is_numeric_dtype(df[col])
    ]

    if non_numeric_columns:
        raise ValueError(f"Non-numeric columns found: {non_numeric_columns}")


def validate_prediction_dataset(df: pd.DataFrame, schema: dict) -> None:
    """
    Validate prediction dataset.

    Prediction files should contain only feature columns.
    """
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
