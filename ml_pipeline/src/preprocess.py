import pandas as pd


def split_features_target(df: pd.DataFrame, schema: dict) -> tuple[pd.DataFrame, pd.Series]:
    """
    Split dataset into features X and target y.
    """
    features = schema["features"]
    target_column = schema["dataset"]["target_column"]

    X = df[features].copy()
    y = df[target_column].copy()

    return X, y


def get_feature_matrix(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """
    Return feature matrix for prediction.
    """
    features = schema["features"]
    return df[features].copy()
