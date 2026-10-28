"""
modeling.py
===========
Model training, comparison, evaluation and (optional) MLflow tracking.

* Classification  -> "Is this a Good Investment?"   (Good_Investment)
* Regression      -> "Price after 5 years (Lakhs)"  (Future_Price_5Y_Lakhs)

Every candidate model is wrapped in the same preprocessing pipeline
(scaling for numbers + one-hot for categories) so comparisons are fair.
MLflow is optional: if it is not installed, training still works.
"""
from __future__ import annotations

import json
import time
from contextlib import nullcontext

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (HistGradientBoostingClassifier, HistGradientBoostingRegressor,
                              RandomForestClassifier, RandomForestRegressor)
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, mean_absolute_error,
                             mean_squared_error, precision_score, r2_score, recall_score,
                             roc_auc_score, roc_curve)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from . import config as C

try:  # MLflow is optional
    import mlflow
    import mlflow.sklearn
    HAS_MLFLOW = True
except Exception:  # pragma: no cover
    HAS_MLFLOW = False

FEATURES = C.NUMERIC_FEATURES + C.CATEGORICAL_FEATURES


# ------------------------------------------------------------ pipelines
def make_preprocessor() -> ColumnTransformer:
    """Scale numeric columns, one-hot encode categoricals."""
    return ColumnTransformer([
        ("num", StandardScaler(), C.NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), C.CATEGORICAL_FEATURES),
    ])


def classifier_candidates() -> dict:
    """Candidate classifiers: (estimator, max training rows or None)."""
    rs = C.RANDOM_STATE
    return {
        "Logistic Regression": (LogisticRegression(max_iter=300), None),
        "Random Forest": (RandomForestClassifier(n_estimators=80, max_depth=14, n_jobs=-1,
                                                 random_state=rs), 60_000),
        "Gradient Boosting": (HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1,
                                                             random_state=rs), None),
    }


def regressor_candidates() -> dict:
    """Candidate regressors: (estimator, max training rows or None)."""
    rs = C.RANDOM_STATE
    return {
        "Ridge Regression": (Ridge(alpha=1.0), None),
        "Random Forest": (RandomForestRegressor(n_estimators=80, max_depth=16, n_jobs=-1,
                                                random_state=rs), 60_000),
        "Gradient Boosting": (HistGradientBoostingRegressor(max_iter=300, learning_rate=0.1,
                                                            random_state=rs), None),
    }


# -------------------------------------------------------- MLflow helpers
def _run(name: str):
    """Disable MLflow runs during deployment."""
    return nullcontext()

def _log(params: dict, metrics: dict, model=None, name: str = "model"):
    """Log to MLflow when available; never let tracking break training."""
    if not HAS_MLFLOW:
        return
    try:
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        if model is not None:
            mlflow.sklearn.log_model(model, name)
    except Exception as exc:  # pragma: no cover
        print(f"[mlflow] logging skipped: {exc}")


# ------------------------------------------------------------- training
def _fit(estimator, X_tr, y_tr, max_rows):
    """Fit a pipeline, optionally on a random subsample (for slow models)."""
    if max_rows and len(X_tr) > max_rows:
        idx = X_tr.sample(max_rows, random_state=C.RANDOM_STATE).index
        X_tr, y_tr = X_tr.loc[idx], y_tr.loc[idx]
    pipe = Pipeline([("prep", make_preprocessor()), ("model", estimator)])
    t0 = time.time()
    pipe.fit(X_tr, y_tr)
    return pipe, time.time() - t0


def train_classification(df: pd.DataFrame, X_tr, X_te, y_tr, y_te):
    """Train + compare classifiers; return (best_pipeline, results, details)."""
    results, fitted = [], {}
    for name, (est, cap) in classifier_candidates().items():
        with _run(f"clf_{name}"):
            pipe, secs = _fit(est, X_tr, y_tr, cap)
            pred, proba = pipe.predict(X_te), pipe.predict_proba(X_te)[:, 1]
            m = {"accuracy": accuracy_score(y_te, pred), "precision": precision_score(y_te, pred),
                 "recall": recall_score(y_te, pred), "f1": f1_score(y_te, pred),
                 "roc_auc": roc_auc_score(y_te, proba), "train_seconds": secs}
            _log({"model": name, "task": "classification"}, m, pipe, "classifier")
        results.append({"model": name, **{k: round(float(v), 4) for k, v in m.items()}})
        fitted[name] = (pipe, proba)
        print(f"  [clf] {name:<20} acc={m['accuracy']:.3f} auc={m['roc_auc']:.3f}")
    best = max(results, key=lambda r: r["roc_auc"])["model"]
    pipe, proba = fitted[best]
    pred = (proba >= 0.5).astype(int)
    fpr, tpr, _ = roc_curve(y_te, proba)
    step = max(1, len(fpr) // 200)  # thin the curve for compact JSON
    details = {
        "best_model": best,
        "confusion_matrix": confusion_matrix(y_te, pred).tolist(),
        "roc_curve": {"fpr": fpr[::step].round(4).tolist(), "tpr": tpr[::step].round(4).tolist()},
        "positive_rate": float(y_te.mean()),
    }
    return pipe, results, details


def train_regression(df: pd.DataFrame, X_tr, X_te, y_tr, y_te):
    """Train + compare regressors; return (best_pipeline, results, details)."""
    results, fitted = [], {}
    # Naive baseline: every property grows at the dataset-average rate
    avg_rate = float(df["Annual_Appreciation"].mean())
    base_pred = X_te["Price_in_Lakhs"] * (1 + avg_rate) ** C.FORECAST_YEARS
    baseline_rmse = float(np.sqrt(mean_squared_error(y_te, base_pred)))
    for name, (est, cap) in regressor_candidates().items():
        with _run(f"reg_{name}"):
            pipe, secs = _fit(est, X_tr, y_tr, cap)
            pred = pipe.predict(X_te)
            m = {"rmse": float(np.sqrt(mean_squared_error(y_te, pred))),
                 "mae": mean_absolute_error(y_te, pred), "r2": r2_score(y_te, pred),
                 "train_seconds": secs}
            _log({"model": name, "task": "regression"}, m, pipe, "regressor")
        results.append({"model": name, **{k: round(float(v), 4) for k, v in m.items()}})
        fitted[name] = (pipe, pred)
        print(f"  [reg] {name:<20} rmse={m['rmse']:.2f} r2={m['r2']:.4f}")
    best = min(results, key=lambda r: r["rmse"])["model"]
    pipe, pred = fitted[best]
    sample = pd.DataFrame({"actual": y_te.values, "pred": pred}).sample(1500, random_state=1)
    details = {"best_model": best, "baseline_rmse": round(baseline_rmse, 4),
               "avg_appreciation": round(avg_rate, 4),
               "scatter": sample.round(2).to_dict(orient="list")}
    return pipe, results, details


def compute_importance(pipe, X_te, y_te, scoring: str, n: int = 500) -> dict:
    """Permutation importance on ORIGINAL columns (model-agnostic, readable)."""
    idx = X_te.sample(min(n, len(X_te)), random_state=C.RANDOM_STATE).index
    res = permutation_importance(pipe, X_te.loc[idx], y_te.loc[idx], n_repeats=1,
                                 random_state=C.RANDOM_STATE, scoring=scoring, n_jobs=1)
    imp = pd.Series(res.importances_mean, index=X_te.columns).clip(lower=0)
    imp = (imp / imp.sum()).sort_values(ascending=False)
    return imp.round(4).to_dict()


def build_lookup(df: pd.DataFrame) -> dict:
    """Option lists + city medians the Streamlit form needs at runtime."""
    return {
        "state_cities": df.groupby("State")["City"].unique().apply(sorted).to_dict(),
        "city_median_ppsf": df.groupby("City")["Price_per_SqFt_INR"].median().to_dict(),
        "options": {c: sorted(df[c].unique().tolist()) for c in
                    ["Property_Type", "Furnished_Status", "Facing", "Owner_Type",
                     "Availability_Status", "Public_Transport_Accessibility"]},
        "amenities": sorted({a.strip() for s in df["Amenities"].unique() for a in s.split(",")}),
        "ranges": {"Size_in_SqFt": [500, 5000], "Price_in_Lakhs": [10, 500]},
    }


def train_all(df: pd.DataFrame) -> dict:
    """Full training run: split, compare models, save artefacts + metrics."""
    C.MODEL_DIR.mkdir(exist_ok=True)
    X, y_c, y_r = df[FEATURES], df[C.CLASSIFICATION_TARGET], df[C.REGRESSION_TARGET]
    X_tr, X_te, yc_tr, yc_te, yr_tr, yr_te = train_test_split(
        X, y_c, y_r, test_size=0.2, random_state=C.RANDOM_STATE, stratify=y_c)

    # if HAS_MLFLOW:
    #     mlflow.set_tracking_uri(f"sqlite:///{C.ROOT / 'mlflow.db'}")
    #     mlflow.set_experiment("Real_Estate_Investment_Advisor")

    print("Training classifiers ...")
    clf, clf_res, clf_det = train_classification(df, X_tr, X_te, yc_tr, yc_te)
    print("Training regressors ...")
    reg, reg_res, reg_det = train_regression(df, X_tr, X_te, yr_tr, yr_te)

    print("Computing feature importance ...")
    clf_det["importance"] = compute_importance(clf, X_te, yc_te, "roc_auc")
    reg_det["importance"] = compute_importance(reg, X_te, yr_te, "r2")

    joblib.dump(clf, C.CLASSIFIER_PATH, compress=3)
    joblib.dump(reg, C.REGRESSOR_PATH, compress=3)
    (C.LOOKUP_PATH).write_text(json.dumps(build_lookup(df)))
    metrics = {"classification": {"results": clf_res, **clf_det},
               "regression": {"results": reg_res, **reg_det},
               "rows": {"train": len(X_tr), "test": len(X_te)},
               "mlflow_used": HAS_MLFLOW}
    C.METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    return metrics
