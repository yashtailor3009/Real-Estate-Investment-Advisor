"""
predict.py
==========
Inference helpers: load the trained pipelines and score one property.

`predict_property` returns everything the Advisor page displays:
classification label + probability (model confidence), 5-year price,
implied annual growth and the city benchmark.
"""
from __future__ import annotations

import json

import joblib
import numpy as np

from . import config as C
from .data_processing import build_inference_row
from .modeling import FEATURES


def load_models():
    """Return (classifier, regressor, lookup, metrics)."""
    clf = joblib.load(C.CLASSIFIER_PATH)
    reg = joblib.load(C.REGRESSOR_PATH)
    lookup = json.loads(C.LOOKUP_PATH.read_text())
    metrics = json.loads(C.METRICS_PATH.read_text())
    return clf, reg, lookup, metrics


def predict_property(clf, reg, lookup: dict, inputs: dict) -> dict:
    """Score a single property described by raw-dataset-style `inputs`."""
    city_med = lookup["city_median_ppsf"][inputs["City"]]
    row = build_inference_row(inputs, city_med)
    X = row[FEATURES]
    prob = float(clf.predict_proba(X)[0, 1])
    future = float(reg.predict(X)[0])
    price = float(inputs["Price_in_Lakhs"])
    cagr = (max(future, 1e-6) / price) ** (1 / C.FORECAST_YEARS) - 1
    return {
        "prob_good": prob,
        "is_good": prob >= 0.5,
        "confidence": max(prob, 1 - prob),
        "future_price": future,
        "gain": future - price,
        "cagr": cagr,
        "ppsf": float(row["Price_per_SqFt_INR"].iloc[0]),
        "city_median_ppsf": float(city_med),
        "value_ratio": float(row["Value_Ratio"].iloc[0]),
        "infra_score": float(row["Infra_Score"].iloc[0]),
    }


def find_good_price(clf, lookup: dict, inputs: dict, steps: int = 24):
    """
    Negotiation helper: the highest asking price (<= current) at which the
    classifier turns 'Good Investment'. Returns None if already good or
    if no tested price gets there.
    """
    city_med = lookup["city_median_ppsf"][inputs["City"]]
    for pct in np.linspace(1.0, 0.3, steps):
        trial = dict(inputs, Price_in_Lakhs=max(10.0, inputs["Price_in_Lakhs"] * pct))
        X = build_inference_row(trial, city_med)[FEATURES]
        if clf.predict_proba(X)[0, 1] >= 0.5:
            return None if pct == 1.0 else trial["Price_in_Lakhs"]
    return None
