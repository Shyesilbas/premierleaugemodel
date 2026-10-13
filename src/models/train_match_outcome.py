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
from src.models.model_utils import apply_probability_calibrator
from src.models.dixon_coles import DixonColesModel, model_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("train_match_outcome")

FORM_STATS = [
    "goals_for", "goals_against", "xg_for", "xg_against",
    "shots_ontarget_for", "shots_ontarget_against",
    "big_chances_for", "touches_in_opp_box", "possession",
]
FORM_SUFFIXES = ["roll_5", "roll_10", "ewma_02", "ewma_04"]
STRENGTH_FEATURES = [
    "elo_home", "elo_away", "elo_diff",
    "ppg_home", "ppg_away", "ppg_diff",
    "gdpg_home", "gdpg_away", "gdpg_diff",
]
DIFF_FEATURES = [f"sdiff_{t}_{s}" for t in ("xg", "goals", "sot") for s in ("e02", "r10")]
EXTRA_1X2 = ["home_rest_days", "away_rest_days", "exp_home_xg_5", "exp_away_xg_5"]
EXTRA_O25 = EXTRA_1X2 + ["exp_match_xg_5", "exp_match_shots_5"]

N_CV_SPLITS = 4
# Paired chronological holdouts showed that supervised 1X2 training on 2022-23
# consistently weakened draw probabilities and usually worsened proper scores.
# Keep those matches in feature history, but don't fit the 1X2 classifier on them.
EXCLUDED_1X2_TRAINING_SEASONS = {"2022_23"}


def _form_features() -> List[str]:
    return [f"{side}_{stat}_{suf}" for side in ("home", "away") for stat in FORM_STATS for suf in FORM_SUFFIXES]


def feature_set(kind: str, columns: List[str]) -> List[str]:
    extra = EXTRA_1X2 if kind == "1x2" else EXTRA_O25
    wanted = STRENGTH_FEATURES + DIFF_FEATURES + _form_features() + extra
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
    """Outer-season comparison of history windows and xG proxy usage.

    The estimator is fixed to the current CV winner (logreg_C0.003) so this
    diagnostic isolates data-window/feature choices. Each outer season is
    calibrated only from forward OOF predictions in its earlier training data.
    """
    labels = [0, 1, 2]
    season_values = seasons.astype(str).reset_index(drop=True)
    X = X.reset_index(drop=True)
    y = y.reset_index(drop=True)
    ordered_seasons = list(pd.unique(season_values))
    feature_variants = {
        "all_features": list(X.columns),
        "without_xg_proxy": [column for column in X.columns if "xg" not in column.lower()],
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
            if policy == "exclude_2022_23":
                keep = ~prior_seasons.eq("2022_23").to_numpy()
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
                    "train_samples": int(len(X_train)),
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


def train_match_outcome_models(
    data_path: str = "data/processed/features_matches_all.parquet",
    model_output_dir: str = "models/production",
) -> Dict[str, Any]:
    if not Path(data_path).exists():
        raise FileNotFoundError(f"Feature dataset not found: {data_path}. Run the full pipeline to rebuild it.")

    df = pd.read_parquet(data_path)
    logger.info(f"Loaded featured dataset with {len(df)} matches.")

    # Only played matches (unplayed fixtures have no score)
    df = df[df["home_score"].notna() & df["away_score"].notna()].copy()

    # Target 1: Match outcome H (0), D (1), A (2) — derived from scores, never from stored labels
    df["target_1x2"] = np.select(
        [df["home_score"] > df["away_score"], df["home_score"] == df["away_score"]], [0, 1], default=2
    )
    # Target 2: Over 2.5 Goals (0 / 1)
    df["target_o25"] = ((df["home_score"] + df["away_score"]) > 2.5).astype(int)

    sort_cols = [c for c in ["kickoff_millis", "match_id"] if c in df.columns]
    df = df.sort_values(by=sort_cols, kind="mergesort").reset_index(drop=True)
    feats = {"1x2": feature_set("1x2", list(df.columns)), "o25": feature_set("o25", list(df.columns))}
    targets = {"1x2": ("target_1x2", [0, 1, 2]), "o25": ("target_o25", [0, 1])}

    split_idx = int(len(df) * 0.8)
    dev, hold = df.iloc[:split_idx], df.iloc[split_idx:]
    logger.info(f"Played matches: {len(df)} | dev: {len(dev)} | hold-out: {len(hold)}")

    final_models: Dict[str, Any] = {}
    calibrators: Dict[str, Dict[str, Any]] = {}
    production_calibration_samples: Dict[str, int] = {}
    metrics: Dict[str, Any] = {}

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
        if kind == "o25":
            res["brier_score"] = round(float(brier_score_loss(y_hold, probs[:, 1])), 3)
            res["baseline_brier_score"] = round(float(brier_score_loss(y_hold, prior_probs[:, 1])), 3)
        else:
            onehot = np.eye(3)[y_hold.values]
            res["brier_score"] = round(float(np.mean(np.sum((probs - onehot) ** 2, axis=1))), 3)
            res["baseline_brier_score"] = round(float(np.mean(np.sum((prior_probs - onehot) ** 2, axis=1))), 3)

        # Production model: refit on all eligible played matches (including the
        # latest holdout). For 1X2, 2022-23 remains feature history only.
        final_fit = df
        if excluded_training_seasons:
            final_fit = df[~df["season"].astype(str).isin(excluded_training_seasons)]
        production_oof_probs, production_oof_targets = chronological_oof_predictions(
            base_model, final_fit[cols], final_fit[tcol], labels
        )
        production_calibrator = fit_probability_calibrator(
            production_oof_probs, pd.Series(production_oof_targets), labels
        )
        calibrators[kind] = production_calibrator
        production_calibration_samples[kind] = int(len(production_oof_targets))
        res["production_calibrator"] = production_calibrator
        res["production_calibration_oof_samples"] = int(len(production_oof_targets))
        final_models[kind] = fit_model(base_model, final_fit[cols], final_fit[tcol])
        res["n_train_final"] = int(len(final_fit))
        metrics["model_1x2" if kind == "1x2" else "model_over_2_5"] = res

    metrics["played_matches_total"] = int(len(df))
    metrics["1x2_variant_outer_holdouts"] = evaluate_1x2_training_variants(
        df[feats["1x2"]],
        df["target_1x2"],
        df["season"] if "season" in df else pd.Series(["all"] * len(df)),
    )
    metrics["dixon_coles_1x2"] = evaluate_dixon_coles(
        df.reset_index(drop=True), df["target_1x2"].reset_index(drop=True),
        df["season"].reset_index(drop=True) if "season" in df else pd.Series(["all"] * len(df)),
    )

    logger.info("=== Match Outcome Metrics (hold-out) ===")
    for k, r in metrics.items():
        if k in {"dixon_coles_1x2", "played_matches_total", "1x2_variant_outer_holdouts"}:
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
            "calibration_method": "forward_oof_on_all_eligible_training_matches",
            "calibration_oof_samples": production_calibration_samples,
            "feature_names": feats["1x2"],  # Backward compatibility
            "feature_names_1x2": feats["1x2"],
            "feature_names_o25": feats["o25"],
            "metrics": metrics,
        },
        Path(model_output_dir) / "outcome_models_v1.joblib",
    )

    return metrics


if __name__ == "__main__":
    train_match_outcome_models()
