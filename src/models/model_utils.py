"""Shared chronological evaluation helpers for match-level models."""

from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.impute import SimpleImputer
from scipy.stats import nbinom, poisson
from sklearn.metrics import brier_score_loss, log_loss, mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


HOLDOUT_FRACTION = 0.20
CV_SPLITS = 4


def safe_feature_frame(
    frame: pd.DataFrame,
    features: list[str],
    fill_value: float = 0.0,
) -> pd.DataFrame:
    """Build a model input frame and apply the caller's missing-value policy."""
    selected = pd.DataFrame(
        {
            column: (
                frame[column]
                if column in frame.columns
                else pd.Series(fill_value, index=frame.index)
            )
            for column in features
        },
        index=frame.index,
    )
    return selected.fillna(fill_value)


def estimate_count_dispersion(y: pd.Series) -> float:
    """Estimate NB2 overdispersion alpha from the training targets only."""
    values = pd.to_numeric(y, errors="coerce").dropna().to_numpy(dtype=float)
    if len(values) < 2:
        return 0.0
    mean = float(values.mean())
    if mean <= 0:
        return 0.0
    return max(0.0, float(values.var(ddof=1) - mean) / (mean * mean))


def count_tail_probability(mean: float, alpha: float, threshold: int) -> float:
    """Return P(count > threshold) under Poisson or NB2(mean, alpha)."""
    mu = max(0.0, float(mean))
    dispersion = max(0.0, float(alpha))
    if dispersion < 1e-8:
        return float(poisson.sf(threshold, mu))
    size = 1.0 / dispersion
    probability = size / (size + mu)
    return float(nbinom.sf(threshold, size, probability))


def apply_probability_calibrator(probabilities: np.ndarray, calibrator: Dict[str, Any]) -> np.ndarray:
    """Apply stored temperature scaling and class offsets to class probabilities."""
    temperature = max(0.05, float(calibrator.get("temperature", 1.0)))
    biases = np.asarray(calibrator.get("bias", np.zeros(probabilities.shape[1])), dtype=float)
    logits = np.log(np.clip(probabilities, 1e-12, 1.0)) / temperature + biases
    logits -= logits.max(axis=1, keepdims=True)
    calibrated = np.exp(logits)
    return calibrated / calibrated.sum(axis=1, keepdims=True)


def blend_log(p_a: np.ndarray, p_b: np.ndarray, weight_a: float) -> np.ndarray:
    """Blend two class-probability matrices in log space and normalize rows."""
    first = np.asarray(p_a, dtype=float)
    second = np.asarray(p_b, dtype=float)
    if first.shape != second.shape or first.ndim != 2:
        raise ValueError("Probability matrices must have the same two-dimensional shape")
    weight = float(weight_a)
    if not np.isfinite(weight) or not 0.0 <= weight <= 1.0:
        raise ValueError("Blend weight must be finite and between 0 and 1")
    logits = weight * np.log(np.clip(first, 1e-12, 1.0))
    logits += (1.0 - weight) * np.log(np.clip(second, 1e-12, 1.0))
    logits -= logits.max(axis=1, keepdims=True)
    probabilities = np.exp(logits)
    return probabilities / probabilities.sum(axis=1, keepdims=True)


def evaluate_count_threshold(
    y_train: pd.Series,
    y_test: pd.Series,
    predicted_means: np.ndarray,
    threshold: int,
    alpha: float,
) -> Dict[str, Any]:
    """Compare NB2, Poisson, and training-rate baseline threshold probabilities."""
    actual = (np.asarray(y_test, dtype=float) > threshold).astype(int)
    nb_probs = np.asarray([count_tail_probability(mu, alpha, threshold) for mu in predicted_means])
    poisson_probs = np.asarray([count_tail_probability(mu, 0.0, threshold) for mu in predicted_means])
    prior_rate = float((np.asarray(y_train, dtype=float) > threshold).mean())
    prior_probs = np.full(len(actual), prior_rate, dtype=float)

    def scores(probs: np.ndarray) -> Dict[str, float]:
        clipped = np.clip(probs, 1e-12, 1.0 - 1e-12)
        return {
            "log_loss": float(log_loss(actual, clipped, labels=[0, 1])),
            "brier": float(brier_score_loss(actual, clipped)),
            "accuracy_pct": float(np.mean((clipped >= 0.5) == actual) * 100.0),
        }

    return {
        "threshold": int(threshold),
        "development_rate": prior_rate,
        "dispersion_alpha": float(alpha),
        "negative_binomial": scores(nb_probs),
        "poisson": scores(poisson_probs),
        "prior": scores(prior_probs),
        "majority_accuracy_pct": float(max(actual.mean(), 1.0 - actual.mean()) * 100.0),
    }


def apply_skill_gate(
    fold_scores: Dict[str, list[float]],
    raw_selected: str,
    baseline: str = "training_mean",
    min_relative_gain: float = 0.005,
    min_fold_wins: int = 3,
) -> Tuple[str, Dict[str, Any]]:
    """Keep a feature model only when it clears the fold-wise mean-baseline gate."""
    if baseline not in fold_scores:
        raise KeyError(f"Skill-gate baseline '{baseline}' is missing from fold scores")
    if raw_selected not in fold_scores:
        raise KeyError(f"Selected candidate '{raw_selected}' is missing from fold scores")

    base = np.asarray(fold_scores[baseline], dtype=float)
    candidate = np.asarray(fold_scores[raw_selected], dtype=float)
    if base.size == 0 or candidate.size != base.size:
        raise ValueError("Skill-gate candidates must have the same non-empty fold scores")

    fold_wins = int(np.sum(candidate < base))
    base_mean = float(base.mean())
    relative_gain = (
        float((base_mean - candidate.mean()) / base_mean)
        if base_mean > 0.0
        else 0.0
    )
    if raw_selected == baseline:
        passed = True
        selected = baseline
        reason = "training_mean_was_cv_winner"
    else:
        passed = bool(relative_gain >= min_relative_gain and fold_wins >= min_fold_wins)
        selected = raw_selected if passed else baseline
        reason = "model_cleared_skill_gate" if passed else "model_failed_skill_gate"

    return selected, {
        "raw_selected_model": raw_selected,
        "selected_model": selected,
        "skill_gate_applied": bool(selected != raw_selected),
        "skill_gate_passed": passed,
        "reason": reason,
        "baseline": baseline,
        "relative_rmse_gain": round(relative_gain, 6),
        "fold_wins": fold_wins,
        "fold_count": int(base.size),
        "minimum_relative_gain": float(min_relative_gain),
        "minimum_fold_wins": int(min_fold_wins),
    }


def select_regression_candidate(
    X: pd.DataFrame,
    y: pd.Series,
    candidates: Dict[str, Any],
) -> Tuple[str, Dict[str, float], Dict[str, Any]]:
    """Select by expanding-window CV, then require repeatable skill over the mean."""
    if len(X) < CV_SPLITS + 2:
        raise ValueError(f"Too few rows for time-series CV: {len(X)}")
    candidates = _include_training_mean(candidates)
    splitter = TimeSeriesSplit(n_splits=CV_SPLITS)
    scores: Dict[str, float] = {}
    fold_scores_by_model: Dict[str, list[float]] = {}
    for name, candidate in candidates.items():
        fold_scores = []
        for train_idx, valid_idx in splitter.split(X):
            model = clone(candidate)
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            pred = model.predict(X.iloc[valid_idx])
            fold_scores.append(float(mean_squared_error(y.iloc[valid_idx], pred) ** 0.5))
        fold_scores_by_model[name] = fold_scores
        scores[name] = float(np.mean(fold_scores))
    raw_selected = min(scores, key=scores.get)
    selected, gate = apply_skill_gate(fold_scores_by_model, raw_selected)
    return selected, {name: round(score, 4) for name, score in scores.items()}, gate


def _include_training_mean(candidates: Dict[str, Any]) -> Dict[str, Any]:
    """Add a fold-fitted constant baseline so weak models cannot win by default."""
    if "training_mean" in candidates:
        return candidates
    baseline = make_regression_pipeline(DummyRegressor(strategy="mean"))
    return {**candidates, "training_mean": baseline}


def incomplete_seasons(df: pd.DataFrame) -> set[str]:
    """Identify seasons with fewer than 300 completed league fixtures."""
    if "season" not in df or not {"home_score", "away_score"}.issubset(df.columns):
        return set()
    played = df[df["home_score"].notna() & df["away_score"].notna()]
    counts = played.groupby(played["season"].astype(str)).size()
    return {season for season, count in counts.items() if int(count) < 300}


def evaluate_season_holdouts(
    X: pd.DataFrame,
    y: pd.Series,
    seasons: pd.Series,
    candidates: Dict[str, Any],
    partial_seasons: set[str] | None = None,
) -> list[Dict[str, Any]]:
    """Evaluate each season using only earlier seasons for selection and fitting."""
    ordered = list(pd.unique(seasons.astype(str)))
    results: list[Dict[str, Any]] = []
    for season_idx, season in enumerate(ordered):
        valid_mask = seasons.astype(str).eq(season).to_numpy()
        valid_positions = np.flatnonzero(valid_mask)
        if season_idx == 0 or len(valid_positions) == 0:
            continue
        valid_start = int(valid_positions[0])
        train_idx = np.arange(valid_start)
        if len(train_idx) < CV_SPLITS + 2:
            continue
        X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
        X_valid, y_valid = X.iloc[valid_positions], y.iloc[valid_positions]
        candidate_set = _include_training_mean(candidates)
        selected, cv_scores, gate = select_regression_candidate(X_train, y_train, candidate_set)
        model = clone(candidate_set[selected]).fit(X_train, y_train)
        pred = np.asarray(model.predict(X_valid), dtype=float)
        baseline = np.full(len(y_valid), float(y_train.mean()))
        rmse = float(mean_squared_error(y_valid, pred) ** 0.5)
        baseline_rmse = float(mean_squared_error(y_valid, baseline) ** 0.5)
        results.append({
            "season": season,
            "partial_season": season in (partial_seasons or set()),
            "train_samples": int(len(train_idx)),
            "test_samples": int(len(valid_positions)),
            "selected_model": selected,
            "raw_selected_model": gate["raw_selected_model"],
            "skill_gate_applied": gate["skill_gate_applied"],
            "skill_gate_passed": gate["skill_gate_passed"],
            "skill_gate_relative_rmse_gain": gate["relative_rmse_gain"],
            "skill_gate_fold_wins": gate["fold_wins"],
            "cv_rmse": cv_scores[selected],
            "rmse": round(rmse, 4),
            "baseline_rmse": round(baseline_rmse, 4),
            "mae": round(float(mean_absolute_error(y_valid, pred)), 4),
            "baseline_mae": round(float(mean_absolute_error(y_valid, baseline)), 4),
            "r2": round(float(r2_score(y_valid, pred)), 4),
            "beats_baseline_rmse": bool(rmse < baseline_rmse),
        })
    return results


def make_regression_pipeline(estimator: Any, *, scale: bool = False) -> Pipeline:
    """Fit imputation/scaling inside each training fold, never across the full timeline."""
    steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale:
        steps.append(("scaler", StandardScaler()))
    steps.append(("estimator", estimator))
    return Pipeline(steps)


def final_estimator(model: Any) -> Any:
    """Return the predictive estimator inside a sklearn pipeline."""
    return model.steps[-1][1] if isinstance(model, Pipeline) else model


def chronological_regression_evaluation(
    X: pd.DataFrame,
    y: pd.Series,
    candidates: Dict[str, Any],
    seasons: pd.Series | None = None,
    partial_seasons: set[str] | None = None,
) -> Tuple[str, Any, Any, Dict[str, Any], np.ndarray, pd.Series]:
    """Select by expanding-window CV on the first 80%, score once on the last 20%.

    Returns the selected name, holdout-fitted estimator, all-data production estimator,
    metrics, holdout predictions, and holdout target values.
    """
    if len(X) != len(y):
        raise ValueError("Feature and target rows must remain aligned")
    if len(X) < 10:
        raise ValueError(f"Too few rows for chronological evaluation: {len(X)}")
    if not candidates:
        raise ValueError("At least one regression candidate is required")
    candidates = _include_training_mean(candidates)

    split_idx = int(len(X) * (1.0 - HOLDOUT_FRACTION))
    if split_idx <= CV_SPLITS or len(X) - split_idx == 0:
        raise ValueError(f"Invalid chronological split for {len(X)} rows")

    X_dev, y_dev = X.iloc[:split_idx], y.iloc[:split_idx]
    X_test, y_test = X.iloc[split_idx:], y.iloc[split_idx:]
    selected_name, cv_scores, skill_gate = select_regression_candidate(X_dev, y_dev, candidates)
    raw_selected_name = skill_gate["raw_selected_model"]
    holdout_model = clone(candidates[selected_name])
    holdout_model.fit(X_dev, y_dev)
    test_pred = np.asarray(holdout_model.predict(X_test), dtype=float)

    baseline_mean = float(y_dev.mean())
    baseline_pred = np.full(len(y_test), baseline_mean, dtype=float)
    test_rmse = float(mean_squared_error(y_test, test_pred) ** 0.5)
    test_mae = float(mean_absolute_error(y_test, test_pred))
    baseline_rmse = float(mean_squared_error(y_test, baseline_pred) ** 0.5)
    baseline_mae = float(mean_absolute_error(y_test, baseline_pred))

    production_model = clone(candidates[selected_name])
    production_model.fit(X, y)

    metrics: Dict[str, Any] = {
        "selected_model": selected_name,
        "raw_selected_model": raw_selected_name,
        "skill_gate_applied": skill_gate["skill_gate_applied"],
        "skill_gate_passed": skill_gate["skill_gate_passed"],
        "skill_gate": skill_gate,
        "selection_metric": "mean RMSE across 4 expanding-window folds; feature model must beat training_mean by >=0.5% and win >=3 folds",
        "cv_rmse": cv_scores,
        "train_samples": int(len(X_dev)),
        "test_samples": int(len(X_test)),
        "test_rmse": round(test_rmse, 4),
        "test_mae": round(test_mae, 4),
        "test_r2": round(float(r2_score(y_test, test_pred)), 4),
        "baseline_mean": round(baseline_mean, 4),
        "baseline_test_rmse": round(baseline_rmse, 4),
        "baseline_test_mae": round(baseline_mae, 4),
        "beats_baseline_rmse": bool(test_rmse < baseline_rmse),
        "beats_baseline_mae": bool(test_mae < baseline_mae),
        "n_features": int(X.shape[1]),
        "count_dispersion_alpha_dev": round(estimate_count_dispersion(y_dev), 6),
    }
    if seasons is not None:
        metrics["season_holdouts"] = evaluate_season_holdouts(
            X, y, seasons.reset_index(drop=True), candidates, partial_seasons
        )
    return selected_name, holdout_model, production_model, metrics, test_pred, y_test
