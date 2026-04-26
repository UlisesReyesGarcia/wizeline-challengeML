from pathlib import Path

import pandas as pd


def load_csv_data(file_path: str | Path) -> pd.DataFrame:
    """
    Load a CSV file into a pandas DataFrame.

    Parameters
    ----------
    file_path : str | Path
        Local path to the CSV file.

    Returns
    -------
    pd.DataFrame
        Loaded dataset.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    if file_path.suffix.lower() != ".csv":
        raise ValueError(f"Expected a CSV file, got: {file_path.suffix}")

    return pd.read_csv(file_path)
