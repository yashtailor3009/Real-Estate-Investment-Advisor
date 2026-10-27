"""
data_processing.py
==================
Cleaning + feature engineering + target creation.

The raw file has no "Good Investment" label and no future price, so the
brief asks us to create them from *domain rules*. Those rules live in
`projected_appreciation` / `add_investment_targets` and are documented
inline so they can be audited and tuned (thresholds are in config.py).

Public API
----------
load_raw(path)                 -> raw DataFrame
clean_data(df)                 -> de-duplicated, imputed, validated frame
engineer_features(df)          -> adds scores / ratios
add_investment_targets(df)     -> adds appreciation, 5-year price, label
build_processed_dataset()      -> end-to-end convenience wrapper
build_inference_row(...)       -> one-row frame for the Streamlit predictor
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

TRANSPORT_MAP = {"Low": 1 / 3, "Medium": 2 / 3, "High": 1.0}
MAX_AMENITIES = 5  # Gym, Pool, Garden, Clubhouse, Playground


# --------------------------------------------------------------- loading
def load_raw(path=C.RAW_CSV) -> pd.DataFrame:
    """Read the raw CSV exactly as provided."""
    return pd.read_csv(path)


# -------------------------------------------------------------- cleaning
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Handle duplicates, missing values, text hygiene and sanity flags."""
    df = df.copy()

    # 1) Text hygiene: trim whitespace on every string column
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].astype(str).str.strip()

    # 2) Duplicates (ignore the surrogate ID when comparing rows)
    df = df.drop_duplicates(subset=[c for c in df.columns if c != "ID"])

    # 3) Missing values: median for numbers, mode for categories
    for col in df.columns:
        if df[col].isna().any():
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(df[col].median())
            else:
                df[col] = df[col].fillna(df[col].mode().iloc[0])

    # 4) Canonical amenity string (sorted) so "Gym, Pool" == "Pool, Gym"
    df["Amenities"] = df["Amenities"].apply(
        lambda s: ", ".join(sorted({a.strip() for a in s.split(",") if a.strip()}))
    )

    # 5) Data-quality flag: a floor number above the building height is
    #    physically impossible. We keep the row but flag it (see Floor_Ratio).
    df["Floor_Inconsistent"] = (df["Floor_No"] > df["Total_Floors"]).astype(int)
    return df.reset_index(drop=True)


# ----------------------------------------------------- feature engineering
def _iqr_flag(s: pd.Series) -> pd.Series:
    """1 if the value lies outside the 1.5 x IQR fences, else 0."""
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    return ((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).astype(int)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create analysis- and model-ready features."""
    df = df.copy()

    # Price per sq ft in rupees (source column is lakhs/sqft: hard to read)
    df["Price_per_SqFt_INR"] = (df["Price_in_Lakhs"] * C.LAKH / df["Size_in_SqFt"]).round(0)

    # Binary flags & counts
    df["Parking_Flag"] = (df["Parking_Space"] == "Yes").astype(int)
    df["Security_Flag"] = (df["Security"] == "Yes").astype(int)
    df["Amenity_Count"] = df["Amenities"].str.count(",") + 1

    # Neighbourhood scores
    df["Transport_Score"] = df["Public_Transport_Accessibility"].map(TRANSPORT_MAP).round(3)
    df["School_Density_Score"] = (df["Nearby_Schools"] / 10).round(2)          # 0-1
    df["Infra_Score"] = (
        (df["Nearby_Schools"] / 10 + df["Nearby_Hospitals"] / 10 + df["Transport_Score"]) / 3 * 100
    ).round(1)                                                                   # 0-100

    # Floor ratio, clipped so inconsistent rows never exceed 1
    df["Floor_Ratio"] = (df["Floor_No"] / df["Total_Floors"]).clip(upper=1).round(3)

    # Relative valuation: how expensive vs the city median (1.0 = at median)
    df["City_Median_PPSF"] = df.groupby("City")["Price_per_SqFt_INR"].transform("median")
    df["Value_Ratio"] = (df["Price_per_SqFt_INR"] / df["City_Median_PPSF"]).round(3)

    # Outlier flags (kept, not dropped - the values are plausible)
    df["PPSF_Outlier"] = _iqr_flag(df["Price_per_SqFt_INR"])
    df["Size_Outlier"] = _iqr_flag(df["Size_in_SqFt"])

    # Bands used by the SQL analysis and charts
    df["Age_Band"] = pd.cut(df["Age_of_Property"], [0, 10, 20, 30, 100],
                            labels=["0-10 yrs", "11-20 yrs", "21-30 yrs", "30+ yrs"]).astype(str)
    df["Price_Band"] = pd.cut(df["Price_in_Lakhs"], [0, 100, 200, 300, 400, 600],
                              labels=["<100L", "100-200L", "200-300L", "300-400L", "400L+"]).astype(str)
    return df


# ------------------------------------------------------- target creation
def projected_appreciation(df: pd.DataFrame, seed: int = C.RANDOM_STATE) -> pd.Series:
    """
    Projected annual appreciation rate (decimal) from transparent domain rules.

        base                      4.5 %
        + infrastructure          up to +3.0 %   (schools, hospitals, transit)
        + amenities               up to +1.2 %
        + security / parking      +0.8 % / +0.6 %
        + under-construction      +1.0 %         (upside on completion)
        + newer building          up to +1.0 %
        + relative value          -2.0 % .. +2.0 %  (cheap vs city median)
        + market noise            N(0, 0.8 %)    (unobservable shocks)

    The noise term is deliberate: it stops the ML models from reproducing
    the rule perfectly, so reported accuracy is realistic rather than 100 %.
    """
    rng = np.random.default_rng(seed)
    rate = (
        0.045
        + 0.030 * df["Infra_Score"] / 100
        + 0.012 * df["Amenity_Count"] / MAX_AMENITIES
        + 0.008 * df["Security_Flag"]
        + 0.006 * df["Parking_Flag"]
        + 0.010 * (df["Availability_Status"] == "Under_Construction")
        + 0.010 * (1 - df["Age_of_Property"] / 35)
        + 0.020 * (1 - df["Value_Ratio"]).clip(-1, 1)
        + rng.normal(0, 0.008, len(df))
    )
    return rate.clip(0.02, 0.14)


def add_investment_targets(df: pd.DataFrame) -> pd.DataFrame:
    """Add appreciation, 5-year future price and the binary label."""
    df = df.copy()
    df["Annual_Appreciation"] = projected_appreciation(df).round(4)
    df[C.REGRESSION_TARGET] = (
        df["Price_in_Lakhs"] * (1 + df["Annual_Appreciation"]) ** C.FORECAST_YEARS
    ).round(2)
    df["Projected_Gain_Lakhs"] = (df[C.REGRESSION_TARGET] - df["Price_in_Lakhs"]).round(2)
    df[C.CLASSIFICATION_TARGET] = (
        (df["Annual_Appreciation"] >= C.GOOD_APPRECIATION_THRESHOLD)
        & (df["Value_Ratio"] <= C.MAX_VALUE_RATIO)
    ).astype(int)
    return df


def build_processed_dataset(raw_path=C.RAW_CSV, save_path=C.PROCESSED_CSV) -> pd.DataFrame:
    """Run the whole preprocessing chain and persist the result."""
    df = add_investment_targets(engineer_features(clean_data(load_raw(raw_path))))
    if save_path is not None:
        df.to_csv(save_path, index=False)
    return df


# --------------------------------------------------- single-row inference
def build_inference_row(inputs: dict, city_median_ppsf: float) -> pd.DataFrame:
    """
    Turn the Streamlit form values into the exact feature frame the trained
    pipelines expect. `inputs` keys mirror the raw dataset columns.
    """
    row = pd.DataFrame([inputs])
    row["Price_per_SqFt_INR"] = row["Price_in_Lakhs"] * C.LAKH / row["Size_in_SqFt"]
    row["Parking_Flag"] = (row["Parking_Space"] == "Yes").astype(int)
    row["Security_Flag"] = (row["Security"] == "Yes").astype(int)
    row["Amenity_Count"] = row["Amenities"].str.count(",") + 1
    row["Transport_Score"] = row["Public_Transport_Accessibility"].map(TRANSPORT_MAP)
    row["School_Density_Score"] = row["Nearby_Schools"] / 10
    row["Infra_Score"] = (row["Nearby_Schools"] / 10 + row["Nearby_Hospitals"] / 10
                          + row["Transport_Score"]) / 3 * 100
    row["Floor_Ratio"] = (row["Floor_No"] / row["Total_Floors"]).clip(upper=1)
    row["Value_Ratio"] = row["Price_per_SqFt_INR"] / city_median_ppsf
    return row
