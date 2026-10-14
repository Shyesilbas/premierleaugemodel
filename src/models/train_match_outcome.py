#!/usr/bin/env python3
"""
Match Outcome Prediction Models (1X2 & Over/Under 2.5 Goals)
Trains:
  1. Multi-class classifier for Match Outcome (H / D / A)
  2. Binary classifier for Over/Under 2.5 Goals

Methodology:
  - Curated feature sets (team strength + attacking/defensive form); noisy stats (throws, offsides, cards...) excluded.
  - Candidate models (regularised multinomial Logistic Regression vs. LightGBM) are selected by
    walk-forward (expanding window) time-series CV log-loss on the development set (first 80%).
  - The selected model is evaluated on the chronological hold-out (last 20%) against
    class-frequency baselines (accuracy AND log-loss).
  - The production model is finally re-fitted on ALL played matches.
"""

import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from lightgbm import LGBMClassifier
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
import joblib
from src.models.model_utils import apply_probability_calibrator, blend_log
from src.models.dixon_coles import DixonColesModel, model_summary
from src.models.eval_utils import (
    expected_calibration_error,
    paired_bootstrap_delta,
    per_match_log_loss,
    reliability_table,
)
from src.features.draw_features import DRAW_PROPENSITY_FEATURES, add_draw_features

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("train_match_outcome")

FORM_STATS = [
    "goals_for", "goals_against",
    "shots_ontarget_for", "shots_ontarget_against",
    "big_chances_for", "touches_in_opp_box", "possession",
]
FORM_SUFFIXES = ["roll_5", "roll_10", "ewma_02", "ewma_04"]
STRENGTH_FEATURES = [
    "elo_home", "elo_away", "elo_diff",
    "ppg_home", "ppg_away", "ppg_diff",
    "gdpg_home", "gdpg_away", "gdpg_diff",
]
DIFF_FEATURES = [f"sdiff_{t}_{s}" for t in ("goals", "sot") for s in ("e02", "r10")]
XG_FRESHNESS_FEATURES = []
EXTRA_1X2 = ["home_rest_days", "away_rest_days"]
EXTRA_O25 = EXTRA_1X2 + ["exp_match_shots_5"]
DRAW_BALANCE_FEATURES = [
    "abs_elo_diff", "abs_ppg_diff", "abs_gdpg_diff",
]

N_CV_SPLITS = 4
# Paired chronological holdouts showed that supervised 1X2 training on 2022-23
# consistently weakened draw probabilities and usually worsened proper scores.
# Keep those matches in feature history, but don't fit the 1X2 classifier on them.
EXCLUDED_1X2_TRAINING_SEASONS = {"2022_23"}
# This season is excluded from all evaluation, selection, and calibration.
# Played matches may still be used to fit the final production estimator.
LOCKED_SEASONS = {"2026_27"}


def _form_features() -> List[str]:
    return [f"{side}_{stat}_{suf}" for side in ("home", "away") for stat in FORM_STATS for suf in FORM_SUFFIXES]


def feature_set(kind: str, columns: List[str], include_draw_propensity: bool = False) -> List[str]:
    extra = EXTRA_1X2 if kind == "1x2" else EXTRA_O25
    draw_balance = DRAW_BALANCE_FEATURES if kind == "1x2" else []
    wanted = STRENGTH_FEATURES + DIFF_FEATURES + _form_features() + extra + draw_balance
    if kind == "1x2" and include_draw_propensity:
        wanted = wanted + list(DRAW_PROPENSITY_FEATURES)
    missing = [c for c in wanted if c not in columns]
    if missing:
        raise KeyError(f"Missing features (rebuild features first): {missing[:10]}")
    return wanted


def candidate_models() -> Dict[str, Any]:
    cands: Dict[str, Any] = {}
    for c in (0.001, 0.003, 0.01, 0.03, 0.1):
        cands[f"logreg_C{c}"] = make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(C=c, max_iter=5000),
        )
    for n in (100, 200, 400):
        cands[f"lgbm_n{n}"] = LGBMClassifier(
            n_estimators=n,
            learning_rate=0.02,
            num_leaves=7,
            min_child_samples=40,
            subsample=0.8,
            subsample_freq=1,  # Without this LightGBM silently ignores `subsample`
            colsample_bytree=0.6,
            reg_lambda=5.0,
            random_state=42,
            verbosity=-1,
        )
    return cands


def fit_model(model: Any, X: pd.DataFrame, y: pd.Series, sample_weight: np.ndarray | None = None) -> Any:
    model = clone(model)
    if sample_weight is None:
        model.fit(X, y)
    elif hasattr(model, "steps"):
        final_step = model.steps[-1][0]
        model.fit(X, y, **{f"{final_step}__sample_weight": sample_weight})
    else:
        model.fit(X, y, sample_weight=sample_weight)
    return model


def _ll(y: pd.Series, p: np.ndarray, labels: List[int]) -> float:
    return float(log_loss(y, p, labels=labels))


def ordered_probabilities(model: Any, X: pd.DataFrame, labels: List[int]) -> np.ndarray:
    """Return predict_proba columns in the explicit target-label order."""
    raw = model.predict_proba(X)
    classes = list(model.classes_)
    ordered = np.zeros((len(X), len(labels)), dtype=float)
    for idx, label in enumerate(labels):
        if label in classes:
            ordered[:, idx] = raw[:, classes.index(label)]
    ordered = np.clip(ordered, 1e-12, 1.0)
    return ordered / ordered.sum(axis=1, keepdims=True)


def fit_probability_calibrator(
    probabilities: np.ndarray,
    y: pd.Series,
    labels: List[int],
    sample_weight: np.ndarray | None = None,
) -> Dict[str, Any]:
    """Fit regularized temperature plus class intercepts on chronological OOF predictions."""
    log_probs = np.log(np.clip(probabilities, 1e-12, 1.0))
    y_values = np.asarray(y, dtype=int)
    class_count = len(labels)
    weights = None if sample_weight is None else np.asarray(sample_weight, dtype=float)
    if weights is not None and len(weights) != len(y_values):
        raise ValueError("Calibration sample weights must align with OOF targets")
    if weights is not None and weights.mean() > 0:
        weights = weights / weights.mean()

    def objective(params: np.ndarray) -> float:
        temperature = float(np.exp(params[0]))
        biases = params[1:]
        logits = log_probs / temperature + biases
        logits -= logits.max(axis=1, keepdims=True)
        probs = np.exp(logits)
        probs /= probs.sum(axis=1, keepdims=True)
        row_losses = -np.log(np.clip(probs[np.arange(len(y_values)), y_values], 1e-12, 1.0))
        mean_loss = float(np.average(row_losses, weights=weights)) if weights is not None else float(row_losses.mean())
        return mean_loss + 0.01 * float(np.sum(params * params))

    result = minimize(objective, np.zeros(class_count + 1), method="BFGS")
    params = result.x if np.isfinite(result.fun) and np.isfinite(result.x).all() else np.zeros(class_count + 1)
    return {"temperature": float(np.exp(params[0])), "bias": params[1:].astype(float).tolist()}


def recency_weights(n: int, half_life_rows: float = 300.0) -> np.ndarray:
    """Give newer forward-OOF rows more calibration weight."""
    if n < 1:
        raise ValueError("At least one OOF row is required for recency weights")
    if not np.isfinite(half_life_rows) or half_life_rows <= 0:
        raise ValueError("half_life_rows must be finite and positive")
    age = np.arange(n - 1, -1, -1, dtype=float)
    weights = 0.5 ** (age / float(half_life_rows))
    return weights / weights.mean()


def chronological_oof_predictions(
    model: Any,
    X: pd.DataFrame,
    y: pd.Series,
    labels: List[int],
    sample_weight: np.ndarray | None = None,
) -> Tuple[np.ndarray, np.ndarray]:
    splitter = TimeSeriesSplit(n_splits=N_CV_SPLITS)
    probability_rows = []
    target_rows = []
    for train_idx, valid_idx in splitter.split(X):
        fold_weight = None if sample_weight is None else sample_weight[train_idx]
        fold_model = fit_model(model, X.iloc[train_idx], y.iloc[train_idx], sample_weight=fold_weight)
        probability_rows.append(ordered_probabilities(fold_model, X.iloc[valid_idx], labels))
        target_rows.append(y.iloc[valid_idx].to_numpy(dtype=int))
    return np.vstack(probability_rows), np.concatenate(target_rows)


def dc_forward_for_blocks(
    df_all: pd.DataFrame,
    df_fit: pd.DataFrame,
    half_life_days: float | None = None,
) -> np.ndarray:
    """Predict the logistic OOF blocks using DC fits from all earlier matches.

    The validation blocks come from ``df_fit`` so their rows match the logistic
    OOF output. Each DC fit can also use earlier rows omitted from ``df_fit``.
    """
    if "kickoff_millis" not in df_all or "kickoff_millis" not in df_fit:
        raise KeyError("kickoff_millis is required to align Dixon-Coles OOF blocks")
    all_matches = df_all.sort_values("kickoff_millis", kind="mergesort")
    fit_matches = df_fit.sort_values("kickoff_millis", kind="mergesort")
    probabilities: List[np.ndarray] = []
    for _, valid_idx in TimeSeriesSplit(n_splits=N_CV_SPLITS).split(fit_matches):
        block = fit_matches.iloc[valid_idx]
        start = pd.to_numeric(block["kickoff_millis"], errors="coerce").min()
        earlier = pd.to_numeric(all_matches["kickoff_millis"], errors="coerce") < start
        dc_train = all_matches.loc[earlier]
        if dc_train.empty:
            raise ValueError("Dixon-Coles forward block has no earlier training matches")
        model = DixonColesModel(half_life_days=half_life_days).fit(dc_train)
        probabilities.append(model.predict_proba(block))
    return np.vstack(probabilities)


def choose_blend_weight(
    p_logreg: np.ndarray,
    p_dc: np.ndarray,
    y: pd.Series | np.ndarray,
    labels: List[int],
    grid: np.ndarray | None = None,
) -> Tuple[float, List[float]]:
    """Choose the log-probability blend weight from aligned forward OOF rows."""
    if p_logreg.shape != p_dc.shape or len(p_logreg) != len(y):
        raise ValueError("Blend probabilities and targets must have aligned rows")
    weights = np.linspace(0.0, 1.0, 21) if grid is None else np.asarray(grid, dtype=float)
    losses = [_ll(pd.Series(y), blend_log(p_logreg, p_dc, weight), labels) for weight in weights]
    best = int(np.argmin(losses))
    return float(weights[best]), [round(float(loss), 5) for loss in losses]


def evaluate_1x2_ensemble_outer_seasons(
    matches: pd.DataFrame,
    X: pd.DataFrame,
    y: pd.Series,
    seasons: pd.Series,
) -> Dict[str, Any]:
    """Choose blend weights before each full outer season and score once on it."""
    labels = [0, 1, 2]
    matches = matches.reset_index(drop=True)
    X = X.reset_index(drop=True)
    y = y.reset_index(drop=True)
    season_values = seasons.astype(str).reset_index(drop=True)
    results: List[Dict[str, Any]] = []
    ordered_seasons = list(pd.unique(season_values))

    for season_idx, season in enumerate(ordered_seasons):
        valid_positions = np.flatnonzero(season_values.eq(season).to_numpy())
        if season_idx == 0 or len(valid_positions) < 300:
            continue
        train_end = int(valid_positions[0])
        all_train = matches.iloc[:train_end].reset_index(drop=True)
        X_all_train = X.iloc[:train_end].reset_index(drop=True)
        y_all_train = y.iloc[:train_end].reset_index(drop=True)

        keep = ~season_values.iloc[:train_end].isin(EXCLUDED_1X2_TRAINING_SEASONS).to_numpy()
        # The first outer season has no older training history after applying
        # the production exclusion. Keep its sole prior season for this one
        # diagnostic so the planned third full season remains measurable.
        early_season_fallback = not bool(keep.any())
        if early_season_fallback:
            keep = np.ones(train_end, dtype=bool)
        fit_rows = np.flatnonzero(keep)
        fit_matches = all_train.iloc[fit_rows].reset_index(drop=True)
        X_fit = X_all_train.iloc[fit_rows].reset_index(drop=True)
        y_fit = y_all_train.iloc[fit_rows].reset_index(drop=True)
        if len(X_fit) < N_CV_SPLITS + 2:
            continue

        selected, cv_scores = select_model("1x2", X_fit, y_fit, labels)
        base_model = candidate_models()[selected]
        lr_oof, oof_targets = chronological_oof_predictions(base_model, X_fit, y_fit, labels)
        dc_oof = dc_forward_for_blocks(all_train, fit_matches)
        if len(lr_oof) != len(dc_oof) or not np.array_equal(oof_targets, np.concatenate([
            y_fit.iloc[valid_idx].to_numpy(dtype=int)
            for _, valid_idx in TimeSeriesSplit(n_splits=N_CV_SPLITS).split(X_fit)
        ])):
            raise ValueError(f"Outer-season OOF rows failed alignment for {season}")

        weight, weight_curve = choose_blend_weight(lr_oof, dc_oof, oof_targets, labels)
        blended_oof = blend_log(lr_oof, dc_oof, weight)
        ensemble_calibrator = fit_probability_calibrator(blended_oof, pd.Series(oof_targets), labels)
        lr_calibrator = fit_probability_calibrator(lr_oof, pd.Series(oof_targets), labels)

        fitted_lr = fit_model(base_model, X_fit, y_fit)
        valid_matches = matches.iloc[valid_positions]
        X_valid = X.iloc[valid_positions]
        lr_valid = ordered_probabilities(fitted_lr, X_valid, labels)
        dc_model = DixonColesModel().fit(all_train)
        dc_valid = dc_model.predict_proba(valid_matches)
        lr_calibrated = apply_probability_calibrator(lr_valid, lr_calibrator)
        ensemble = apply_probability_calibrator(blend_log(lr_valid, dc_valid, weight), ensemble_calibrator)
        y_valid = y.iloc[valid_positions].to_numpy(dtype=int)
        lr_losses = per_match_log_loss(lr_calibrated, y_valid)
        ensemble_losses = per_match_log_loss(ensemble, y_valid)
        results.append({
            "season": season,
            "partial_season": False,
            "train_samples_all_prior": int(len(all_train)),
            "train_samples_logreg": int(len(X_fit)),
            "test_samples": int(len(valid_positions)),
            "selected_model": selected,
            "cv_log_loss": cv_scores[selected],
            "early_season_fallback_included_excluded_history": early_season_fallback,
            "weight_logreg": weight,
            "weight_curve": weight_curve,
            "logreg_log_loss": round(_ll(pd.Series(y_valid), lr_calibrated, labels), 5),
            "ensemble_log_loss": round(_ll(pd.Series(y_valid), ensemble, labels), 5),
            "delta_log_loss": round(float(np.mean(ensemble_losses - lr_losses)), 5),
            "bootstrap_vs_logreg": paired_bootstrap_delta(ensemble_losses, lr_losses),
            "optimizer_converged": dc_model.fit_ok_,
        })

    full_seasons = [row for row in results if not row["partial_season"]]
    deltas = [float(row["delta_log_loss"]) for row in full_seasons]
    wins = sum(delta < 0.0 for delta in deltas)
    season_count = len(deltas)
    mean_delta = float(np.mean(deltas)) if deltas else float("nan")
    required_wins = int(np.ceil(2.0 * season_count / 3.0)) if season_count else None
    passed = bool(
        season_count >= 3
        and wins >= required_wins
        and mean_delta < -0.002
    )
    return {
        "season_holdouts": results,
        "full_seasons": season_count,
        "seasons_better_than_logreg": int(wins),
        "required_better_seasons": required_wins,
        "mean_delta_log_loss": round(mean_delta, 5) if np.isfinite(mean_delta) else None,
        "gate_passed": passed,
        "gate": "at least 2/3 full seasons with lower log-loss and mean delta below -0.002",
    }


def evaluate_season_holdouts(
    kind: str,
    X: pd.DataFrame,
    y: pd.Series,
    seasons: pd.Series,
    labels: List[int],
    excluded_training_seasons: set[str] | None = None,
) -> List[Dict[str, Any]]:
    ordered_seasons = list(pd.unique(seasons.astype(str)))
    results = []
    for season_idx, season in enumerate(ordered_seasons):
        valid_positions = np.flatnonzero(seasons.astype(str).eq(season).to_numpy())
        if season_idx == 0 or not len(valid_positions):
            continue
        train_end = int(valid_positions[0])
        X_train, y_train = X.iloc[:train_end], y.iloc[:train_end]
        if excluded_training_seasons:
            prior_seasons = seasons.iloc[:train_end].astype(str)
            keep = ~prior_seasons.isin(excluded_training_seasons).to_numpy()
            X_train = X_train.iloc[keep].reset_index(drop=True)
            y_train = y_train.iloc[keep].reset_index(drop=True)
        X_valid, y_valid = X.iloc[valid_positions], y.iloc[valid_positions]
        if len(X_train) < N_CV_SPLITS + 2:
            continue

        selected, cv_scores = select_model(kind, X_train, y_train, labels)
        model = candidate_models()[selected]
        oof_probs, oof_targets = chronological_oof_predictions(model, X_train, y_train, labels)
        calibrator = fit_probability_calibrator(oof_probs, pd.Series(oof_targets), labels)
        fitted = fit_model(model, X_train, y_train)
        raw_probs = ordered_probabilities(fitted, X_valid, labels)
        calibrated = apply_probability_calibrator(raw_probs, calibrator)
        prior = y_train.value_counts(normalize=True).reindex(labels, fill_value=0).to_numpy()
        prior_probs = np.tile(prior, (len(y_valid), 1))
        results.append({
            "season": season,
            "partial_season": bool(len(valid_positions) < 300),
            "train_samples": int(len(X_train)),
            "test_samples": int(len(valid_positions)),
            "selected_model": selected,
            "cv_log_loss": cv_scores[selected],
            "raw_log_loss": round(_ll(y_valid, raw_probs, labels), 4),
            "calibrated_log_loss": round(_ll(y_valid, calibrated, labels), 4),
            "prior_log_loss": round(_ll(y_valid, prior_probs, labels), 4),
            "raw_accuracy_pct": round(float(accuracy_score(y_valid, raw_probs.argmax(axis=1)) * 100), 2),
            "calibrated_accuracy_pct": round(float(accuracy_score(y_valid, calibrated.argmax(axis=1)) * 100), 2),
        })
    return results


def evaluate_1x2_training_variants(
    X: pd.DataFrame,
    y: pd.Series,
    seasons: pd.Series,
) -> List[Dict[str, Any]]:
    """Outer-season comparison of history windows, xG proxy, and draw-balance features.

    The estimator is fixed to the current CV winner (logreg_C0.003) so this
    diagnostic isolates data-window/feature choices. Each outer season is
    calibrated only from forward OOF predictions in its earlier training data.
    """
    labels = [0, 1, 2]
    season_values = seasons.astype(str).reset_index(drop=True)
    X = X.reset_index(drop=True)
    y = y.reset_index(drop=True)
    ordered_seasons = list(pd.unique(season_values))
    draw_propensity = set(DRAW_PROPENSITY_FEATURES)
    if not draw_propensity.issubset(X.columns):
        raise KeyError("Draw-propensity outer evaluation requires all DRAW_PROPENSITY_FEATURES")
    base_columns = [column for column in X.columns if column not in draw_propensity]
    feature_variants = {
        "all_features": base_columns,
        "without_xg_proxy": [column for column in base_columns if "xg" not in column.lower()],
        "without_draw_balance": [column for column in base_columns if column not in DRAW_BALANCE_FEATURES],
        "with_draw_propensity": list(X.columns),
        "without_draw_propensity": base_columns,
    }
    history_policies = ("all_prior", "exclude_2022_23", "latest_two_seasons", "recency_half_life_1_5")
    fixed_model = candidate_models()["logreg_C0.003"]
    results: List[Dict[str, Any]] = []

    for season_idx, season in enumerate(ordered_seasons):
        valid_positions = np.flatnonzero(season_values.eq(season).to_numpy())
        if season_idx == 0 or not len(valid_positions):
            continue
        train_end = int(valid_positions[0])
        prior_seasons = season_values.iloc[:train_end]
        X_prior, y_prior = X.iloc[:train_end], y.iloc[:train_end]

        for policy in history_policies:
            keep = np.ones(train_end, dtype=bool)
            early_season_fallback = False
            if policy == "exclude_2022_23":
                keep = ~prior_seasons.eq("2022_23").to_numpy()
                if not keep.any():
                    keep = np.ones(train_end, dtype=bool)
                    early_season_fallback = True
            elif policy == "latest_two_seasons":
                keep = prior_seasons.isin(list(pd.unique(prior_seasons))[-2:]).to_numpy()
            X_train = X_prior.iloc[keep].reset_index(drop=True)
            y_train = y_prior.iloc[keep].reset_index(drop=True)
            train_season_values = prior_seasons.iloc[keep].reset_index(drop=True)
            if len(X_train) < N_CV_SPLITS + 2:
                continue

            sample_weight = None
            if policy == "recency_half_life_1_5":
                train_order = list(pd.unique(train_season_values))
                season_rank = {name: idx for idx, name in enumerate(train_order)}
                latest_rank = len(train_order) - 1
                sample_weight = np.asarray([
                    0.5 ** ((latest_rank - season_rank[name]) / 1.5)
                    for name in train_season_values
                ], dtype=float)
                sample_weight /= sample_weight.mean()

            for feature_name, feature_columns in feature_variants.items():
                X_fit = X_train[feature_columns]
                X_valid = X.iloc[valid_positions][feature_columns]
                oof_probs, oof_targets = chronological_oof_predictions(
                    fixed_model, X_fit, y_train, labels, sample_weight=sample_weight
                )
                oof_weights = None
                if sample_weight is not None:
                    oof_weights = np.concatenate([
                        sample_weight[valid_idx]
                        for _, valid_idx in TimeSeriesSplit(n_splits=N_CV_SPLITS).split(X_fit)
                    ])
                calibrator = fit_probability_calibrator(
                    oof_probs,
                    pd.Series(oof_targets),
                    labels,
                    sample_weight=oof_weights,
                )
                fitted = fit_model(fixed_model, X_fit, y_train, sample_weight=sample_weight)
                probabilities = apply_probability_calibrator(
                    ordered_probabilities(fitted, X_valid, labels), calibrator
                )
                y_valid = y.iloc[valid_positions].to_numpy(dtype=int)
                draw_actual = (y_valid == 1).astype(int)
                results.append({
                    "season": season,
                    "partial_season": bool(len(valid_positions) < 300),
                    "policy": policy,
                    "features": feature_name,
                    "early_season_fallback_included_excluded_history": early_season_fallback,
                    "train_samples": int(len(X_train)),
                    "test_samples": int(len(valid_positions)),
                    "selected_model": "logreg_C0.003",
                    "log_loss": round(_ll(pd.Series(y_valid), probabilities, labels), 4),
                    "multiclass_brier": round(float(np.mean(np.sum(
                        (probabilities - np.eye(3)[y_valid]) ** 2, axis=1
                    ))), 4),
                    "draw_brier": round(float(np.mean((probabilities[:, 1] - draw_actual) ** 2)), 4),
                    "draw_auc": round(float(roc_auc_score(draw_actual, probabilities[:, 1])), 4),
                    "actual_draw_rate": round(float(draw_actual.mean()), 4),
                    "mean_draw_probability": round(float(probabilities[:, 1].mean()), 4),
                    "predicted_draws": int((probabilities.argmax(axis=1) == 1).sum()),
                })
    return results


def summarize_draw_propensity_gate(variant_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare propensity features with the same base features on three outer seasons."""
    selected = [
        row for row in variant_results
        if row["policy"] == "exclude_2022_23"
        and row["features"] in {"with_draw_propensity", "without_draw_propensity"}
        and not row["partial_season"]
    ]
    by_season: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for row in selected:
        by_season.setdefault(str(row["season"]), {})[row["features"]] = row

    comparisons = []
    for season, candidates in by_season.items():
        with_features = candidates.get("with_draw_propensity")
        without_features = candidates.get("without_draw_propensity")
        if with_features is None or without_features is None:
            continue
        comparisons.append({
            "season": season,
            "partial_season": False,
            "early_season_fallback_included_excluded_history": bool(
                with_features["early_season_fallback_included_excluded_history"]
            ),
            "test_samples": int(with_features["test_samples"]),
            "log_loss_with": float(with_features["log_loss"]),
            "log_loss_without": float(without_features["log_loss"]),
            "delta_log_loss": round(
                float(with_features["log_loss"] - without_features["log_loss"]), 5
            ),
            "draw_auc_with": float(with_features["draw_auc"]),
            "draw_auc_without": float(without_features["draw_auc"]),
            "delta_draw_auc": round(
                float(with_features["draw_auc"] - without_features["draw_auc"]), 5
            ),
        })

    log_loss_deltas = [row["delta_log_loss"] for row in comparisons]
    draw_auc_deltas = [row["delta_draw_auc"] for row in comparisons]
    mean_log_loss_delta = float(np.mean(log_loss_deltas)) if log_loss_deltas else float("nan")
    mean_draw_auc_delta = float(np.mean(draw_auc_deltas)) if draw_auc_deltas else float("nan")
    gate_passed = bool(
        len(comparisons) == 3
        and mean_log_loss_delta < -0.002
        and mean_draw_auc_delta >= 0.01
    )
    return {
        "policy": "exclude_2022_23; early 2023/24 outer season uses 2022/23 because otherwise no training rows remain",
        "outer_seasons": comparisons,
        "season_count": len(comparisons),
        "mean_delta_log_loss": round(mean_log_loss_delta, 5) if np.isfinite(mean_log_loss_delta) else None,
        "mean_delta_draw_auc": round(mean_draw_auc_delta, 5) if np.isfinite(mean_draw_auc_delta) else None,
        "gate_passed": gate_passed,
        "gate": "mean log-loss delta < -0.002 and mean draw-AUC delta >= +0.01 across three full seasons",
    }


def _dixon_coles_oof_predictions(matches: pd.DataFrame, y: pd.Series, labels: List[int]) -> Tuple[np.ndarray, np.ndarray]:
    """Generate strictly forward predictions for fitting the DC probability calibrator."""
    probabilities: List[np.ndarray] = []
    targets: List[np.ndarray] = []
    for train_idx, valid_idx in TimeSeriesSplit(n_splits=N_CV_SPLITS).split(matches):
        model = DixonColesModel().fit(matches.iloc[train_idx])
        probabilities.append(model.predict_proba(matches.iloc[valid_idx]))
        targets.append(y.iloc[valid_idx].to_numpy(dtype=int))
    return np.vstack(probabilities), np.concatenate(targets)


def evaluate_dixon_coles(matches: pd.DataFrame, y: pd.Series, seasons: pd.Series) -> Dict[str, Any]:
    """Compare a Dixon–Coles 1X2 baseline on the same temporal holdouts as the classifier."""
    labels = [0, 1, 2]
    split_idx = int(len(matches) * 0.8)
    dev, hold = matches.iloc[:split_idx], matches.iloc[split_idx:]
    y_dev, y_hold = y.iloc[:split_idx], y.iloc[split_idx:]
    oof_probs, oof_targets = _dixon_coles_oof_predictions(dev, y_dev, labels)
    calibrator = fit_probability_calibrator(oof_probs, pd.Series(oof_targets), labels)
    fitted = DixonColesModel().fit(dev)
    raw = fitted.predict_proba(hold)
    calibrated = apply_probability_calibrator(raw, calibrator)

    def scores(target: pd.Series, probabilities: np.ndarray) -> Dict[str, Any]:
        onehot = np.eye(3)[target.to_numpy(dtype=int)]
        predicted = probabilities.argmax(axis=1)
        return {
            "log_loss": round(_ll(target, probabilities, labels), 4),
            "accuracy_pct": round(float(accuracy_score(target, predicted) * 100), 2),
            "brier": round(float(np.mean(np.sum((probabilities - onehot) ** 2, axis=1))), 4),
            "pred_distribution": {int(k): int(v) for k, v in pd.Series(predicted).value_counts().sort_index().items()},
        }

    season_rows = []
    ordered_seasons = list(pd.unique(seasons.astype(str)))
    season_values = seasons.astype(str).to_numpy()
    for season_idx, season in enumerate(ordered_seasons):
        valid_positions = np.flatnonzero(season_values == season)
        if season_idx == 0 or not len(valid_positions):
            continue
        train_end = int(valid_positions[0])
        season_train, season_valid = matches.iloc[:train_end], matches.iloc[valid_positions]
        target_train, target_valid = y.iloc[:train_end], y.iloc[valid_positions]
        if len(season_train) < N_CV_SPLITS + 2:
            continue
        season_oof, season_oof_y = _dixon_coles_oof_predictions(season_train, target_train, labels)
        season_calibrator = fit_probability_calibrator(season_oof, pd.Series(season_oof_y), labels)
        season_model = DixonColesModel().fit(season_train)
        season_raw = season_model.predict_proba(season_valid)
        season_calibrated = apply_probability_calibrator(season_raw, season_calibrator)
        season_rows.append({
            "season": season,
            "partial_season": bool(len(valid_positions) < 300),
            "train_samples": int(train_end),
            "test_samples": int(len(valid_positions)),
            "raw": scores(target_valid, season_raw),
            "calibrated": scores(target_valid, season_calibrated),
            "prior_log_loss": round(_ll(
                target_valid,
                np.tile(target_train.value_counts(normalize=True).reindex(labels, fill_value=0).to_numpy(), (len(target_valid), 1)),
                labels,
            ), 4),
            "optimizer_converged": season_model.fit_ok_,
        })

    return {
        "development_samples": int(len(dev)),
        "test_samples": int(len(hold)),
        "raw": scores(y_hold, raw),
        "calibrated": scores(y_hold, calibrated),
        "prior_log_loss": round(_ll(
            y_hold,
            np.tile(y_dev.value_counts(normalize=True).reindex(labels, fill_value=0).to_numpy(), (len(y_hold), 1)),
            labels,
        ), 4),
        "calibrator": calibrator,
        "model_parameters": model_summary(fitted),
        "season_holdouts": season_rows,
    }


def select_model(
    kind: str,
    X: pd.DataFrame,
    y: pd.Series,
    labels: List[int],
) -> Tuple[str, Dict[str, float]]:
    """Walk-forward CV on the development set; returns best candidate name and all CV scores."""
    tscv = TimeSeriesSplit(n_splits=N_CV_SPLITS)
    scores: Dict[str, float] = {}
    for name, model in candidate_models().items():
        fold_ll = []
        for tr_idx, va_idx in tscv.split(X):
            m = fit_model(model, X.iloc[tr_idx], y.iloc[tr_idx])
            fold_ll.append(_ll(y.iloc[va_idx], ordered_probabilities(m, X.iloc[va_idx], labels), labels))
        scores[name] = round(float(np.mean(fold_ll)), 4)
    best = min(scores, key=scores.get)
    logger.info(f"[{kind}] CV log-loss: {scores} -> selected {best}")
    return best, scores


def evaluate_calibration_drift_outer_seasons(
    matches: pd.DataFrame,
    X: pd.DataFrame,
    y: pd.Series,
    seasons: pd.Series,
    half_lives: Tuple[float, ...] = (150.0, 300.0, 600.0),
) -> Dict[str, Any]:
    """Compare ordinary and recency-weighted calibration on prior-only seasons."""
    labels = [0, 1, 2]
    matches = matches.reset_index(drop=True)
    X = X.reset_index(drop=True)
    y = y.reset_index(drop=True)
    season_values = seasons.astype(str).reset_index(drop=True)
    results: List[Dict[str, Any]] = []

    for season_idx, season in enumerate(pd.unique(season_values)):
        valid_positions = np.flatnonzero(season_values.eq(season).to_numpy())
        if season_idx == 0 or len(valid_positions) < 300:
            continue
        train_end = int(valid_positions[0])
        train_matches = matches.iloc[:train_end].reset_index(drop=True)
        prior_seasons = season_values.iloc[:train_end]
        keep = ~prior_seasons.isin(EXCLUDED_1X2_TRAINING_SEASONS).to_numpy()
        early_season_fallback = not bool(keep.any())
        if early_season_fallback:
            keep = np.ones(train_end, dtype=bool)
        train_rows = np.flatnonzero(keep)
        X_train = X.iloc[:train_end].iloc[train_rows].reset_index(drop=True)
        y_train = y.iloc[:train_end].iloc[train_rows].reset_index(drop=True)
        if len(X_train) < N_CV_SPLITS + 2:
            continue

        selected, cv_scores = select_model("1x2", X_train, y_train, labels)
        base_model = candidate_models()[selected]
        oof_probs, oof_targets = chronological_oof_predictions(base_model, X_train, y_train, labels)
        standard_calibrator = fit_probability_calibrator(
            oof_probs, pd.Series(oof_targets), labels
        )
        fitted = fit_model(base_model, X_train, y_train)
        X_valid = X.iloc[valid_positions]
        y_valid = y.iloc[valid_positions].to_numpy(dtype=int)
        raw_valid = ordered_probabilities(fitted, X_valid, labels)
        standard_valid = apply_probability_calibrator(raw_valid, standard_calibrator)
        standard_losses = per_match_log_loss(standard_valid, y_valid)
        candidate_rows: Dict[str, Any] = {}

        for half_life in half_lives:
            weights = recency_weights(len(oof_targets), half_life_rows=half_life)
            calibrator = fit_probability_calibrator(
                oof_probs, pd.Series(oof_targets), labels, sample_weight=weights
            )
            calibrated = apply_probability_calibrator(raw_valid, calibrator)
            losses = per_match_log_loss(calibrated, y_valid)
            candidate_rows[str(int(half_life))] = {
                "log_loss": round(_ll(pd.Series(y_valid), calibrated, labels), 5),
                "delta_vs_standard": round(float(np.mean(losses - standard_losses)), 5),
                "bootstrap_vs_standard": paired_bootstrap_delta(losses, standard_losses),
            }

        results.append({
            "season": season,
            "partial_season": False,
            "train_samples": int(len(X_train)),
            "test_samples": int(len(valid_positions)),
            "selected_model": selected,
            "cv_log_loss": cv_scores[selected],
            "standard_log_loss": round(_ll(pd.Series(y_valid), standard_valid, labels), 5),
            "early_season_fallback_included_excluded_history": early_season_fallback,
            "calibration_candidates": candidate_rows,
        })

    full_seasons = [row for row in results if not row["partial_season"]]
    summaries: Dict[str, Any] = {}
    for half_life in half_lives:
        key = str(int(half_life))
        deltas = [float(row["calibration_candidates"][key]["delta_vs_standard"]) for row in full_seasons]
        mean_delta = float(np.mean(deltas)) if deltas else float("nan")
        worst_delta = max(deltas) if deltas else float("inf")
        summaries[key] = {
            "mean_delta_vs_standard": round(mean_delta, 5) if np.isfinite(mean_delta) else None,
            "worst_full_season_delta": round(float(worst_delta), 5) if np.isfinite(worst_delta) else None,
            "full_seasons_improved": int(sum(delta < 0.0 for delta in deltas)),
            "gate_passed": bool(
                len(full_seasons) >= 3 and mean_delta <= -0.002 and worst_delta <= 0.005
            ),
        }

    passing = [
        float(half_life) for half_life in half_lives
        if summaries[str(int(half_life))]["gate_passed"]
    ]
    selected_half_life = min(
        passing,
        key=lambda value: summaries[str(int(value))]["mean_delta_vs_standard"],
    ) if passing else None
    return {
        "season_holdouts": results,
        "full_seasons": len(full_seasons),
        "half_life_summaries": summaries,
        "selected_half_life_rows": selected_half_life,
        "gate_passed": selected_half_life is not None,
        "gate": "mean delta <= -0.002 and no full season delta > +0.005",
    }


def train_match_outcome_models(
    data_path: str = "data/processed/features_matches_all.parquet",
    model_output_dir: str = "models/production",
) -> Dict[str, Any]:
    if not Path(data_path).exists():
        raise FileNotFoundError(f"Feature dataset not found: {data_path}. Run the full pipeline to rebuild it.")

    df = pd.read_parquet(data_path)
    logger.info(f"Loaded featured dataset with {len(df)} matches.")
    # Rebuild these stateful features through the shared helper so standalone
    # training and the full feature pipeline use identical definitions.
    df = add_draw_features(df)

    # Only played matches (unplayed fixtures have no score)
    df = df[df["home_score"].notna() & df["away_score"].notna()].copy()

    # Target 1: Match outcome H (0), D (1), A (2) — derived from scores, never from stored labels
    df["target_1x2"] = np.select(
        [df["home_score"] > df["away_score"], df["home_score"] == df["away_score"]], [0, 1], default=2
    )
    # Target 2: Over 2.5 Goals (0 / 1)
    df["target_o25"] = ((df["home_score"] + df["away_score"]) > 2.5).astype(int)

    sort_cols = [c for c in ["kickoff_millis", "match_id"] if c in df.columns]
    df_all = df.sort_values(by=sort_cols, kind="mergesort").reset_index(drop=True)
    if LOCKED_SEASONS and "season" not in df_all.columns:
        raise KeyError("A season column is required to enforce LOCKED_SEASONS")
    locked_mask = df_all["season"].astype(str).isin(LOCKED_SEASONS)
    locked_matches = int(locked_mask.sum())
    df = df_all.loc[~locked_mask].reset_index(drop=True)
    base_1x2_features = feature_set("1x2", list(df.columns))
    draw_1x2_features = feature_set("1x2", list(df.columns), include_draw_propensity=True)
    variant_results = evaluate_1x2_training_variants(
        df[draw_1x2_features],
        df["target_1x2"],
        df["season"] if "season" in df else pd.Series(["all"] * len(df)),
    )
    draw_propensity_gate = summarize_draw_propensity_gate(variant_results)
    include_draw_propensity = draw_propensity_gate["gate_passed"]
    feats = {
        "1x2": draw_1x2_features if include_draw_propensity else base_1x2_features,
        "o25": feature_set("o25", list(df.columns)),
    }
    targets = {"1x2": ("target_1x2", [0, 1, 2]), "o25": ("target_o25", [0, 1])}

    split_idx = int(len(df) * 0.8)
    dev, hold = df.iloc[:split_idx], df.iloc[split_idx:]
    logger.info(
        "Played matches: %s | locked-season matches excluded from evaluation: %s | dev: %s | hold-out: %s",
        len(df_all), locked_matches, len(dev), len(hold),
    )

    final_models: Dict[str, Any] = {}
    calibrators: Dict[str, Dict[str, Any]] = {}
    production_calibration_samples: Dict[str, int] = {}
    metrics: Dict[str, Any] = {}
    production_ensemble: Dict[str, Any] | None = None
    production_recency_calibrators: Dict[int, Dict[str, Any]] = {}

    for kind in ("1x2", "o25"):
        tcol, labels = targets[kind]
        cols = feats[kind]
        excluded_training_seasons = EXCLUDED_1X2_TRAINING_SEASONS if kind == "1x2" and "season" in dev else set()
        dev_fit = dev
        if excluded_training_seasons:
            dev_fit = dev[~dev["season"].astype(str).isin(excluded_training_seasons)]
        best, cv_scores = select_model(kind, dev_fit[cols], dev_fit[tcol], labels)
        base_model = candidate_models()[best]

        # Calibrate on out-of-fold development predictions only. The final holdout
        # remains untouched until every model and calibration choice is fixed.
        oof_probs, oof_targets = chronological_oof_predictions(
            base_model, dev_fit[cols], dev_fit[tcol], labels
        )
        evaluation_calibrator = fit_probability_calibrator(oof_probs, pd.Series(oof_targets), labels)
        holdout_ensemble: Dict[str, Any] | None = None
        if kind == "1x2":
            dc_oof_probs = dc_forward_for_blocks(dev, dev_fit)
            blend_weight, blend_curve = choose_blend_weight(
                oof_probs, dc_oof_probs, oof_targets, labels
            )
            ensemble_oof = blend_log(oof_probs, dc_oof_probs, blend_weight)
            ensemble_calibrator = fit_probability_calibrator(
                ensemble_oof, pd.Series(oof_targets), labels
            )
            dc_dev = DixonColesModel().fit(dev)
            holdout_ensemble = {
                "weight_logreg": blend_weight,
                "weight_curve": blend_curve,
                "calibrator": ensemble_calibrator,
                "dc_model": dc_dev,
            }

        # Hold-out evaluation (model trained on dev only)
        m_dev = fit_model(base_model, dev_fit[cols], dev_fit[tcol])
        raw_probs = ordered_probabilities(m_dev, hold[cols], labels)
        probs = apply_probability_calibrator(raw_probs, evaluation_calibrator)
        preds = probs.argmax(axis=1)
        y_hold = hold[tcol]

        prior = dev_fit[tcol].value_counts(normalize=True).reindex(labels, fill_value=0).values
        prior_probs = np.tile(prior, (len(hold), 1))
        mode = int(dev_fit[tcol].mode()[0])

        res = {
            "selected_model": best,
            "cv_log_loss": cv_scores[best],
            "cv_log_loss_by_candidate": cv_scores,
            "calibrator": evaluation_calibrator,
            "development_samples": int(len(dev_fit)),
            "test_samples": int(len(hold)),
            "test_accuracy_pct": round(float(accuracy_score(y_hold, preds) * 100), 2),
            "raw_test_accuracy_pct": round(float(accuracy_score(y_hold, raw_probs.argmax(axis=1)) * 100), 2),
            "baseline_accuracy_pct": round(float((y_hold == mode).mean() * 100), 2),
            "log_loss": round(_ll(y_hold, probs, labels), 3),
            "raw_log_loss": round(_ll(y_hold, raw_probs, labels), 3),
            "baseline_log_loss": round(_ll(y_hold, prior_probs, labels), 3),
            "pred_distribution": {int(k): int(v) for k, v in pd.Series(preds).value_counts().sort_index().items()},
            "raw_pred_distribution": {int(k): int(v) for k, v in pd.Series(raw_probs.argmax(axis=1)).value_counts().sort_index().items()},
            "actual_distribution": {int(k): int(v) for k, v in y_hold.value_counts().sort_index().items()},
            "n_features": len(cols),
            "season_holdouts": evaluate_season_holdouts(
                kind, df[cols].reset_index(drop=True), df[tcol].reset_index(drop=True),
                df["season"].reset_index(drop=True) if "season" in df else pd.Series(["all"] * len(df)), labels,
                excluded_training_seasons=excluded_training_seasons,
            ),
        }
        if kind == "1x2" and holdout_ensemble is not None:
            ensemble_probs = apply_probability_calibrator(
                blend_log(
                    raw_probs,
                    holdout_ensemble["dc_model"].predict_proba(hold),
                    holdout_ensemble["weight_logreg"],
                ),
                holdout_ensemble["calibrator"],
            )
            ensemble_losses = per_match_log_loss(ensemble_probs, y_hold.to_numpy(dtype=int))
            classifier_losses = per_match_log_loss(probs, y_hold.to_numpy(dtype=int))
            onehot_hold = np.eye(3)[y_hold.to_numpy(dtype=int)]
            draw_actual_hold = (y_hold.to_numpy(dtype=int) == 1)
            res["ensemble"] = {
                "weight_logreg": holdout_ensemble["weight_logreg"],
                "weight_curve": holdout_ensemble["weight_curve"],
                "log_loss": round(_ll(y_hold, ensemble_probs, labels), 4),
                "brier": round(float(np.mean(np.sum((ensemble_probs - onehot_hold) ** 2, axis=1))), 4),
                "draw_auc": round(float(roc_auc_score(draw_actual_hold, ensemble_probs[:, 1])), 4),
                "bootstrap_vs_single": paired_bootstrap_delta(ensemble_losses, classifier_losses),
            }
            holdout_recency: Dict[str, Any] = {}
            for half_life in (150, 300, 600):
                weights = recency_weights(len(oof_targets), half_life_rows=float(half_life))
                calibrator = fit_probability_calibrator(
                    oof_probs, pd.Series(oof_targets), labels, sample_weight=weights
                )
                recent_probs = apply_probability_calibrator(raw_probs, calibrator)
                recent_losses = per_match_log_loss(recent_probs, y_hold.to_numpy(dtype=int))
                holdout_recency[str(half_life)] = {
                    "log_loss": round(_ll(y_hold, recent_probs, labels), 5),
                    "delta_vs_standard": round(float(np.mean(recent_losses - classifier_losses)), 5),
                    "bootstrap_vs_standard": paired_bootstrap_delta(recent_losses, classifier_losses),
                }
            res["recency_calibration_holdout"] = holdout_recency
        model_loss = per_match_log_loss(probs, y_hold.to_numpy(dtype=int))
        prior_loss = per_match_log_loss(prior_probs, y_hold.to_numpy(dtype=int))
        res["bootstrap_vs_prior"] = paired_bootstrap_delta(model_loss, prior_loss)
        if kind == "o25":
            res["brier_score"] = round(float(brier_score_loss(y_hold, probs[:, 1])), 3)
            res["baseline_brier_score"] = round(float(brier_score_loss(y_hold, prior_probs[:, 1])), 3)
            actual_event = y_hold.to_numpy(dtype=int)
            res["reliability"] = reliability_table(probs[:, 1], actual_event)
            res["expected_calibration_error"] = expected_calibration_error(probs[:, 1], actual_event)
        else:
            onehot = np.eye(3)[y_hold.values]
            res["brier_score"] = round(float(np.mean(np.sum((probs - onehot) ** 2, axis=1))), 3)
            res["baseline_brier_score"] = round(float(np.mean(np.sum((prior_probs - onehot) ** 2, axis=1))), 3)
            draw_actual = (y_hold.to_numpy(dtype=int) == 1)
            res["draw_brier_score"] = round(float(np.mean((probs[:, 1] - draw_actual) ** 2)), 4)
            res["draw_auc"] = round(float(roc_auc_score(draw_actual, probs[:, 1])), 4)
            res["actual_draw_rate"] = round(float(draw_actual.mean()), 4)
            res["mean_draw_probability"] = round(float(probs[:, 1].mean()), 4)
            res["mean_draw_probability_on_draws"] = round(float(probs[draw_actual, 1].mean()), 4)
            res["mean_draw_probability_on_non_draws"] = round(float(probs[~draw_actual, 1].mean()), 4)
            res["reliability_draw"] = reliability_table(probs[:, 1], draw_actual.astype(int))
            res["draw_expected_calibration_error"] = expected_calibration_error(
                probs[:, 1], draw_actual.astype(int)
            )

        # Production model: refit on all eligible played matches (including the
        # latest holdout). For 1X2, 2022-23 remains feature history only.
        final_fit = df_all
        if excluded_training_seasons:
            final_fit = df_all[~df_all["season"].astype(str).isin(excluded_training_seasons)]
        # Keep the locked season out of probability calibration even though
        # played rows from it may be part of the final production model fit.
        calibration_fit = df
        if excluded_training_seasons:
            calibration_fit = calibration_fit[
                ~calibration_fit["season"].astype(str).isin(excluded_training_seasons)
            ]
        production_oof_probs, production_oof_targets = chronological_oof_predictions(
            base_model, calibration_fit[cols], calibration_fit[tcol], labels
        )
        production_calibrator = fit_probability_calibrator(
            production_oof_probs, pd.Series(production_oof_targets), labels
        )
        if kind == "1x2":
            production_dc_oof = dc_forward_for_blocks(df, calibration_fit)
            production_blend_weight, production_blend_curve = choose_blend_weight(
                production_oof_probs, production_dc_oof, production_oof_targets, labels
            )
            production_ensemble_oof = blend_log(
                production_oof_probs, production_dc_oof, production_blend_weight
            )
            production_ensemble_calibrator = fit_probability_calibrator(
                production_ensemble_oof, pd.Series(production_oof_targets), labels
            )
            production_ensemble = {
                "weight_logreg": production_blend_weight,
                "weight_curve": production_blend_curve,
                "calibrator": production_ensemble_calibrator,
                "oof_samples": int(len(production_oof_targets)),
            }
            for half_life in (150, 300, 600):
                weights = recency_weights(len(production_oof_targets), half_life_rows=float(half_life))
                production_recency_calibrators[half_life] = fit_probability_calibrator(
                    production_oof_probs,
                    pd.Series(production_oof_targets),
                    labels,
                    sample_weight=weights,
                )
        calibrators[kind] = production_calibrator
        production_calibration_samples[kind] = int(len(production_oof_targets))
        res["production_calibrator"] = production_calibrator
        res["production_calibration_oof_samples"] = int(len(production_oof_targets))
        final_models[kind] = fit_model(base_model, final_fit[cols], final_fit[tcol])
        res["n_train_final"] = int(len(final_fit))
        metrics["model_1x2" if kind == "1x2" else "model_over_2_5"] = res

    metrics["played_matches_total"] = int(len(df_all))
    metrics["evaluation_matches_total"] = int(len(df))
    metrics["locked_seasons_excluded"] = sorted(LOCKED_SEASONS)
    metrics["locked_season_matches_excluded"] = locked_matches
    metrics["1x2_variant_outer_holdouts"] = variant_results
    metrics["1x2_draw_propensity_outer_eval"] = draw_propensity_gate
    metrics["draw_propensity_enabled"] = bool(include_draw_propensity)
    draw_eval_path = Path("data/processed/1x2_draw_propensity_outer_eval.json")
    draw_eval_path.parent.mkdir(parents=True, exist_ok=True)
    draw_eval_path.write_text(json.dumps(draw_propensity_gate, indent=2), encoding="utf-8")
    metrics["dixon_coles_1x2"] = evaluate_dixon_coles(
        df.reset_index(drop=True), df["target_1x2"].reset_index(drop=True),
        df["season"].reset_index(drop=True) if "season" in df else pd.Series(["all"] * len(df)),
    )
    metrics["1x2_ensemble_outer_eval"] = evaluate_1x2_ensemble_outer_seasons(
        df.reset_index(drop=True),
        df[feats["1x2"]].reset_index(drop=True),
        df["target_1x2"].reset_index(drop=True),
        df["season"].reset_index(drop=True) if "season" in df else pd.Series(["all"] * len(df)),
    )
    outer_eval_path = Path("data/processed/1x2_ensemble_outer_eval.json")
    outer_eval_path.parent.mkdir(parents=True, exist_ok=True)
    outer_eval_path.write_text(json.dumps(metrics["1x2_ensemble_outer_eval"], indent=2), encoding="utf-8")

    metrics["1x2_calibration_drift_outer_eval"] = evaluate_calibration_drift_outer_seasons(
        df.reset_index(drop=True),
        df[feats["1x2"]].reset_index(drop=True),
        df["target_1x2"].reset_index(drop=True),
        df["season"].reset_index(drop=True) if "season" in df else pd.Series(["all"] * len(df)),
    )
    drift_eval_path = Path("data/processed/1x2_calibration_drift_outer_eval.json")
    drift_eval_path.parent.mkdir(parents=True, exist_ok=True)
    drift_eval_path.write_text(
        json.dumps(metrics["1x2_calibration_drift_outer_eval"], indent=2), encoding="utf-8"
    )
    selected_recency_half_life = metrics["1x2_calibration_drift_outer_eval"]["selected_half_life_rows"]
    if selected_recency_half_life is not None:
        calibrators["1x2"] = production_recency_calibrators[int(selected_recency_half_life)]
        metrics["model_1x2"]["production_calibrator"] = calibrators["1x2"]
        metrics["model_1x2"]["production_calibration_method"] = (
            f"forward_oof_recency_weighted_half_life_{int(selected_recency_half_life)}_rows"
        )
        metrics["1x2_calibration_drift_production"] = {
            "enabled": True,
            "half_life_rows": int(selected_recency_half_life),
            "oof_samples": production_calibration_samples["1x2"],
            "calibrator": calibrators["1x2"],
        }
    else:
        metrics["model_1x2"]["production_calibration_method"] = "forward_oof_standard"
        metrics["1x2_calibration_drift_production"] = {
            "enabled": False,
            "reason": "outer-season calibration decision gate not passed",
        }

    ensemble_gate_passed = metrics["1x2_ensemble_outer_eval"]["gate_passed"]
    if ensemble_gate_passed and production_ensemble is not None:
        final_models["dc"] = DixonColesModel().fit(df_all)
        calibrators["1x2_ensemble"] = production_ensemble["calibrator"]
        production_calibration_samples["1x2_ensemble"] = production_ensemble["oof_samples"]
        metrics["1x2_ensemble_production"] = {
            "enabled": True,
            "weight_logreg": production_ensemble["weight_logreg"],
            "weight_curve": production_ensemble["weight_curve"],
            "calibration_oof_samples": production_ensemble["oof_samples"],
            "dc_model_parameters": model_summary(final_models["dc"]),
        }
    else:
        metrics["1x2_ensemble_production"] = {
            "enabled": False,
            "reason": "outer-season decision gate not passed",
        }

    logger.info("=== Match Outcome Metrics (hold-out) ===")
    for k, r in metrics.items():
        if k in {
            "dixon_coles_1x2", "played_matches_total", "evaluation_matches_total",
            "locked_seasons_excluded", "locked_season_matches_excluded",
            "1x2_variant_outer_holdouts", "1x2_ensemble_outer_eval", "1x2_ensemble_production",
            "1x2_calibration_drift_outer_eval", "1x2_calibration_drift_production",
            "1x2_draw_propensity_outer_eval", "draw_propensity_enabled",
        }:
            continue
        logger.info(
            f"{k}: {r['selected_model']} | Acc {r['test_accuracy_pct']}% (base {r['baseline_accuracy_pct']}%) | "
            f"LogLoss {r['log_loss']} (base {r['baseline_log_loss']}) | Brier {r['brier_score']} "
            f"(base {r['baseline_brier_score']}) | preds {r['pred_distribution']} vs actual {r['actual_distribution']}"
        )
    logger.info(
        "Dixon-Coles 1X2: raw LL %.4f / calibrated LL %.4f / prior LL %.4f; "
        "raw acc %.2f%% / calibrated acc %.2f%%; predictions %s; parameters %s",
        metrics["dixon_coles_1x2"]["raw"]["log_loss"],
        metrics["dixon_coles_1x2"]["calibrated"]["log_loss"],
        metrics["dixon_coles_1x2"]["prior_log_loss"],
        metrics["dixon_coles_1x2"]["raw"]["accuracy_pct"],
        metrics["dixon_coles_1x2"]["calibrated"]["accuracy_pct"],
        metrics["dixon_coles_1x2"]["calibrated"]["pred_distribution"],
        metrics["dixon_coles_1x2"]["model_parameters"],
    )

    Path(model_output_dir).mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model_1x2": final_models["1x2"],
            "model_o25": final_models["o25"],
            "calibrators": calibrators,
            "calibration_method": (
                f"forward_oof_recency_weighted_half_life_{int(selected_recency_half_life)}_rows"
                if selected_recency_half_life is not None
                else "forward_oof_on_all_eligible_training_matches"
            ),
            "calibration_oof_samples": production_calibration_samples,
            "feature_names": feats["1x2"],  # Backward compatibility
            "feature_names_1x2": feats["1x2"],
            "feature_names_o25": feats["o25"],
            "metrics": metrics,
            **({
                "model_dc": final_models["dc"],
                "ensemble_weight": production_ensemble["weight_logreg"],
            } if ensemble_gate_passed and production_ensemble is not None else {}),
        },
        Path(model_output_dir) / "outcome_models_v1.joblib",
    )

    return metrics


if __name__ == "__main__":
    train_match_outcome_models()
