"""
utils.py
========
Small, dependency-free helpers shared by the app, PDF and slide builders:
number formatting, data access and plain-English insight sentences.
"""
from __future__ import annotations

import pandas as pd

from . import config as C


# ------------------------------------------------------------ formatting
def fmt_money(lakhs: float) -> str:
    """Format INR lakhs the way Indian buyers read prices (L / Cr)."""
    if lakhs is None or pd.isna(lakhs):
        return "-"
    return f"₹{lakhs / 100:.2f} Cr" if abs(lakhs) >= 100 else f"₹{lakhs:.1f} L"


def fmt_int(n: float) -> str:
    """Thousands separators: 250000 -> '250,000'."""
    return f"{int(round(n)):,}"


def fmt_pct(x: float, digits: int = 1) -> str:
    """Format a 0-1 fraction as a percentage string."""
    return f"{x * 100:.{digits}f}%"


# ---------------------------------------------------------- data access
def ensure_artifacts() -> None:
    """Build processed data, SQLite DB and models if they are missing."""
    from .data_processing import build_processed_dataset
    from .database import build_database
    from .modeling import train_all

    df = None
    if not C.PROCESSED_CSV.exists():
        df = build_processed_dataset()
    if not C.DB_PATH.exists():
        df = df if df is not None else pd.read_csv(C.PROCESSED_CSV)
        build_database(df)
    if not (C.CLASSIFIER_PATH.exists() and C.REGRESSOR_PATH.exists() and C.METRICS_PATH.exists()):
        df = df if df is not None else pd.read_csv(C.PROCESSED_CSV)
        train_all(df)


def read_processed() -> pd.DataFrame:
    """Load the processed dataset with memory-friendly dtypes."""
    df = pd.read_csv(C.PROCESSED_CSV)
    for col in ["State", "City", "Locality", "Property_Type", "Furnished_Status", "Facing",
                "Owner_Type", "Availability_Status", "Public_Transport_Accessibility",
                "Parking_Space", "Security", "Age_Band", "Price_Band"]:
        df[col] = df[col].astype("category")
    return df


# ------------------------------------------------- insight sentence helpers
def spread_pct(values: pd.Series) -> float:
    """(max - min) / mean as a percentage: how far apart group averages are."""
    return float((values.max() - values.min()) / values.mean() * 100)


def describe_spread(group_means: pd.Series, what: str) -> str:
    """One honest sentence about whether group averages differ meaningfully."""
    sp = spread_pct(group_means)
    hi, lo = group_means.idxmax(), group_means.idxmin()
    if sp < 5:
        return (f"{what} differs by only {sp:.1f}% between the highest ({hi}) and lowest ({lo}) "
                f"group - effectively no pricing power.")
    return f"{what} is highest for {hi} and lowest for {lo}, a {sp:.1f}% gap."
