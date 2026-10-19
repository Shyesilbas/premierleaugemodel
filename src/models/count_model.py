"""Blocks shared by the five count-model trainers (corners, throws, saves, cards, offsides).

Each trainer keeps what makes it different (curated features, candidate models, thresholds and
the metric keys the API and benchmark report read); the identical plumbing lives here.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Sequence, Set, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.models.model_utils import estimate_count_dispersion, final_estimator, incomplete_seasons


def load_count_dataset(
    data_path: str,
    target_col: str,
    features: Sequence[str],
    label: str,
    logger: logging.Logger,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, Set[str]]:
    """Played matches with a target, in kickoff order: (frame, X, y, partially-covered seasons)."""
    if not Path(data_path).exists():
        raise FileNotFoundError(f"Feature dataset not found: {data_path}. Run the full pipeline to rebuild it.")

    df = pd.read_parquet(data_path)
    logger.info(f"Loaded featured dataset with {len(df)} matches.")
    partial_seasons = incomplete_seasons(df)  # judged on every row, before the played-match filter

    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset!")

    df = df[df[target_col].notnull()].copy()
    if "is_played" in df.columns:
        df = df[df["is_played"]].copy()

    if "kickoff_millis" in df.columns:
        df = df.sort_values(by=["kickoff_millis", "match_id"]).reset_index(drop=True)
    logger.info(f"Filtered {len(df)} completed matches with {label.lower()} data.")

    missing_features = [c for c in features if c not in df.columns]
    if missing_features:
        raise ValueError(f"{label} model features missing from dataset: {missing_features}")
    logger.info(f"Selected {len(features)} curated features for {label} model.")

    return df, df[list(features)].copy(), df[target_col].astype(float), partial_seasons


def top_features_of(prod_model: Any, feature_cols: Sequence[str], as_records: bool = False, limit: int = 10):
    """Largest importances (tree models) or absolute coefficients (linear models) of the fitted estimator.

    ``{feature: value}`` by default; ``[{"feature", "importance"}, ...]`` with ``as_records`` (cards).
    """
    estimator = final_estimator(prod_model)
    if hasattr(estimator, "feature_importances_"):
        values = estimator.feature_importances_
    elif hasattr(estimator, "coef_"):
        values = np.abs(estimator.coef_)
    else:
        return [] if as_records else {}
    order = np.argsort(values)[::-1][:limit]
    if as_records:
        return [{"feature": feature_cols[i], "importance": float(values[i])} for i in order]
    return {feature_cols[i]: float(values[i]) for i in order}


def train_errors(y_train: pd.Series, eval_model: Any, X_train: pd.DataFrame) -> Dict[str, float]:
    """In-sample RMSE and MAE of the development model."""
    predictions = eval_model.predict(X_train)
    return {
        "train_rmse": round(float(mean_squared_error(y_train, predictions) ** 0.5), 4),
        "train_mae": round(float(mean_absolute_error(y_train, predictions)), 4),
    }


def save_count_artifact(
    model_output_dir: str,
    filename: str,
    prod_model: Any,
    feature_cols: Sequence[str],
    metrics: Dict[str, Any],
    y_all: pd.Series,
    top_features: Any,
    **extra: Any,
) -> Dict[str, Any]:
    """Write the production artifact the API loads and return it."""
    artifact = {
        "model": prod_model,
        "feature_names": list(feature_cols),
        "feature_cols": list(feature_cols),
        "baseline_mean": metrics["baseline_mean"],
        "count_dispersion_alpha": estimate_count_dispersion(y_all),
        "metrics": metrics,
        "top_features": top_features,
        **extra,
    }
    Path(model_output_dir).mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, Path(model_output_dir) / filename)
    return artifact
