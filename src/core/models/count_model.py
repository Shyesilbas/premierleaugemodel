"""Blocks shared by the five count-model trainers (corners, throws, saves, cards, offsides).

Each trainer keeps what makes it different (curated features, candidate models, thresholds and
the metric keys the API and benchmark report read); the identical plumbing lives here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any, Dict, Sequence, Set, Tuple

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.linear_model import ElasticNet, PoissonRegressor, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.core.models.model_utils import (
    chronological_regression_evaluation,
    estimate_count_dispersion,
    evaluate_count_threshold,
    final_estimator,
    incomplete_seasons,
    make_regression_pipeline,
)


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
        "count_dispersion_alpha": float(
            metrics.get("count_dispersion_alpha_dev", estimate_count_dispersion(y_all))
        ),
        "metrics": metrics,
        "top_features": top_features,
        **extra,
    }
    Path(model_output_dir).mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, Path(model_output_dir) / filename)
    return artifact


@dataclass(frozen=True)
class CountModelSpec:
    """Declarative specification for a match-level count regression model."""

    name: str
    label: str
    target_col: str
    artifact_filename: str
    features: Tuple[str, ...]
    thresholds: Tuple[int, ...] = ()
    primary_threshold: int | None = None
    ridge_alphas: Tuple[float, ...] = (0.1, 1.0, 10.0, 50.0, 100.0, 250.0, 500.0)
    poisson_alphas: Tuple[float, ...] = (1.0, 10.0, 50.0, 200.0)
    include_elastic: bool = True
    lgbm_params: Dict[str, Any] = field(default_factory=dict)
    top_features_as_records: bool = False
    round_top_features: bool = False
    include_target_col_in_artifact: bool = False
    legacy_metric_aliases: Dict[str, str] = field(default_factory=dict)


def build_count_candidates(spec: CountModelSpec) -> Dict[str, Any]:
    """Construct the candidate regression pipeline grid for a ``CountModelSpec``."""
    default_lgbm = {
        "max_depth": 3,
        "num_leaves": 7,
        "learning_rate": 0.02,
        "n_estimators": 55,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "verbosity": -1,
    }
    default_lgbm.update(spec.lgbm_params)

    candidates: Dict[str, Any] = {
        "lgbm_shallow": make_regression_pipeline(LGBMRegressor(**default_lgbm)),
        **{
            f"ridge_{alpha:g}": make_regression_pipeline(Ridge(alpha=alpha), scale=True)
            for alpha in spec.ridge_alphas
        },
        **{
            f"poisson_{alpha:g}": make_regression_pipeline(
                PoissonRegressor(alpha=alpha, max_iter=2000), scale=True
            )
            for alpha in spec.poisson_alphas
        },
    }
    if spec.include_elastic:
        candidates.update({
            f"elastic_{alpha}_{l1}": make_regression_pipeline(
                ElasticNet(alpha=alpha, l1_ratio=l1, max_iter=2000), scale=True
            )
            for alpha in (0.05, 0.1, 0.5)
            for l1 in (0.2, 0.5, 0.8)
        })
    return candidates


def train_count_model(
    spec: CountModelSpec,
    data_path: str,
    model_output_dir: str,
    logger: logging.Logger,
) -> Dict[str, Any]:
    """Execute the full chronological CV, threshold evaluation, and artifact save for ``spec``."""
    df, X_all, y_all, partial_seasons = load_count_dataset(
        data_path, spec.target_col, spec.features, spec.label, logger
    )
    feature_cols = list(spec.features)
    candidates = build_count_candidates(spec)

    best_name, eval_model, prod_model, metrics, preds_test, y_test = chronological_regression_evaluation(
        X_all, y_all, candidates, df.get("season"), partial_seasons
    )
    split_idx = metrics["train_samples"]
    X_train, y_train = X_all.iloc[:split_idx], y_all.iloc[:split_idx]
    logger.info("Selected %s by development-period time-series CV", best_name)

    alpha_dev = metrics["count_dispersion_alpha_dev"]
    threshold_results = {
        threshold: evaluate_count_threshold(y_train, y_test, preds_test, threshold, alpha_dev)
        for threshold in spec.thresholds
    }

    top_features = top_features_of(
        prod_model, feature_cols, as_records=spec.top_features_as_records
    )
    metrics_top_features = (
        {k: round(float(v), 4) for k, v in top_features.items()}
        if spec.round_top_features and isinstance(top_features, dict)
        else top_features
    )

    metrics.update({
        "model_type": f"Chronological CV-selected {best_name} ({spec.name})",
        **train_errors(y_train, eval_model, X_train),
        "top_features": metrics_top_features,
    })

    if threshold_results:
        metrics["count_threshold_metrics"] = {
            f"over_{threshold}_5": result for threshold, result in threshold_results.items()
        }
        primary = spec.primary_threshold if spec.primary_threshold is not None else spec.thresholds[0]
        if primary in threshold_results:
            primary_res = threshold_results[primary]
            acc = round(primary_res["negative_binomial"]["accuracy_pct"], 2)
            maj = round(primary_res["majority_accuracy_pct"], 2)
            metrics[f"over_{primary}_5_accuracy_pct"] = acc
            metrics["majority_baseline_pct"] = maj

        for threshold, result in threshold_results.items():
            metrics[f"over_{threshold}_5_accuracy_pct"] = round(
                result["negative_binomial"]["accuracy_pct"], 2
            )

        for alias_key, source_key in spec.legacy_metric_aliases.items():
            if source_key in metrics:
                metrics[alias_key] = metrics[source_key]

    extra = {"target_col": spec.target_col} if spec.include_target_col_in_artifact else {}
    save_count_artifact(
        model_output_dir,
        spec.artifact_filename,
        prod_model,
        feature_cols,
        metrics,
        y_all,
        top_features,
        **extra,
    )
    logger.info("Model saved to %s", Path(model_output_dir) / spec.artifact_filename)
    return metrics
