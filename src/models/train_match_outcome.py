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
from lightgbm import LGBMClassifier
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler
import joblib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("train_match_outcome")

# Mild time-decay season weights (previous 0.40 -> 4.50 range effectively discarded older seasons)
SEASON_WEIGHTS = {"2023_24": 0.6, "2024_25": 0.8, "2025_26": 1.0, "2026_27": 1.2}

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


def _form_features() -> List[str]:
    return [f"{side}_{stat}_{suf}" for side in ("home", "away") for stat in FORM_STATS for suf in FORM_SUFFIXES]


def feature_set(kind: str, columns: List[str]) -> List[str]:
    extra = EXTRA_1X2 if kind == "1x2" else EXTRA_O25
    wanted = STRENGTH_FEATURES + DIFF_FEATURES + _form_features() + extra
    missing = [c for c in wanted if c not in columns]
    if missing:
        raise KeyError(f"Missing features (rebuild features first): {missing[:10]}")
    return wanted


def candidate_models(kind: str) -> Dict[str, Any]:
    cands: Dict[str, Any] = {}
    for c in (0.001, 0.003, 0.01, 0.03, 0.1):
        cands[f"logreg_C{c}"] = make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=5000))
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


def fit_model(model: Any, X: pd.DataFrame, y: pd.Series, w: np.ndarray) -> Any:
    model = clone(model)
    if isinstance(model, Pipeline):
        model.fit(X, y, **{f"{model.steps[-1][0]}__sample_weight": w})
    else:
        model.fit(X, y, sample_weight=w)
    return model


def _ll(y: pd.Series, p: np.ndarray, labels: List[int]) -> float:
    return float(log_loss(y, p, labels=labels))


def select_model(kind: str, X: pd.DataFrame, y: pd.Series, w: np.ndarray, labels: List[int]) -> Tuple[str, Dict[str, float]]:
    """Walk-forward CV on the development set; returns best candidate name and all CV scores."""
    tscv = TimeSeriesSplit(n_splits=N_CV_SPLITS)
    scores: Dict[str, float] = {}
    for name, model in candidate_models(kind).items():
        fold_ll = []
        for tr_idx, va_idx in tscv.split(X):
            m = fit_model(model, X.iloc[tr_idx], y.iloc[tr_idx], w[tr_idx])
            fold_ll.append(_ll(y.iloc[va_idx], m.predict_proba(X.iloc[va_idx]), labels))
        scores[name] = round(float(np.mean(fold_ll)), 4)
    best = min(scores, key=scores.get)
    logger.info(f"[{kind}] CV log-loss: {scores} -> selected {best}")
    return best, scores


def train_match_outcome_models(
    data_path: str = "data/processed/features_matches_all.parquet",
    model_output_dir: str = "models/production",
    reports_output_dir: str = "reports",
) -> Dict[str, Any]:
    if not Path(data_path).exists():
        data_path = "data/processed/features_matches_2024_25.parquet"

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
    weights = df["season"].map(SEASON_WEIGHTS).fillna(1.0).values

    feats = {"1x2": feature_set("1x2", list(df.columns)), "o25": feature_set("o25", list(df.columns))}
    targets = {"1x2": ("target_1x2", [0, 1, 2]), "o25": ("target_o25", [0, 1])}

    split_idx = int(len(df) * 0.8)
    dev, hold = df.iloc[:split_idx], df.iloc[split_idx:]
    w_dev = weights[:split_idx]
    logger.info(f"Played matches: {len(df)} | dev: {len(dev)} | hold-out: {len(hold)}")

    final_models: Dict[str, Any] = {}
    metrics: Dict[str, Any] = {}

    for kind in ("1x2", "o25"):
        tcol, labels = targets[kind]
        cols = feats[kind]
        best, cv_scores = select_model(kind, dev[cols], dev[tcol], w_dev, labels)
        base_model = candidate_models(kind)[best]

        # Hold-out evaluation (model trained on dev only)
        m_dev = fit_model(base_model, dev[cols], dev[tcol], w_dev)
        probs = m_dev.predict_proba(hold[cols])
        preds = probs.argmax(axis=1)
        y_hold = hold[tcol]

        prior = dev[tcol].value_counts(normalize=True).reindex(labels, fill_value=0).values
        prior_probs = np.tile(prior, (len(hold), 1))
        mode = int(dev[tcol].mode()[0])

        res = {
            "selected_model": best,
            "cv_log_loss": cv_scores[best],
            "test_accuracy_pct": round(float(accuracy_score(y_hold, preds) * 100), 2),
            "baseline_accuracy_pct": round(float((y_hold == mode).mean() * 100), 2),
            "log_loss": round(_ll(y_hold, probs, labels), 3),
            "baseline_log_loss": round(_ll(y_hold, prior_probs, labels), 3),
            "pred_distribution": {int(k): int(v) for k, v in pd.Series(preds).value_counts().sort_index().items()},
            "actual_distribution": {int(k): int(v) for k, v in y_hold.value_counts().sort_index().items()},
            "n_features": len(cols),
        }
        if kind == "o25":
            res["brier_score"] = round(float(brier_score_loss(y_hold, probs[:, 1])), 3)
            res["baseline_brier_score"] = round(float(brier_score_loss(y_hold, prior_probs[:, 1])), 3)
        else:
            onehot = np.eye(3)[y_hold.values]
            res["brier_score"] = round(float(np.mean(np.sum((probs - onehot) ** 2, axis=1))), 3)
            res["baseline_brier_score"] = round(float(np.mean(np.sum((prior_probs - onehot) ** 2, axis=1))), 3)

        # Production model: refit on ALL played matches (incl. the most recent hold-out games)
        final_models[kind] = fit_model(base_model, df[cols], df[tcol], weights)
        res["n_train_final"] = int(len(df))
        metrics["model_1x2" if kind == "1x2" else "model_over_2_5"] = res

    logger.info("=== Match Outcome Metrics (hold-out) ===")
    for k, r in metrics.items():
        logger.info(
            f"{k}: {r['selected_model']} | Acc {r['test_accuracy_pct']}% (base {r['baseline_accuracy_pct']}%) | "
            f"LogLoss {r['log_loss']} (base {r['baseline_log_loss']}) | Brier {r['brier_score']} "
            f"(base {r['baseline_brier_score']}) | preds {r['pred_distribution']} vs actual {r['actual_distribution']}"
        )

    Path(model_output_dir).mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model_1x2": final_models["1x2"],
            "model_o25": final_models["o25"],
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
