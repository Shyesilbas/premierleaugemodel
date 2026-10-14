"""Train and persist the selected production score-matrix model."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from src.models.dixon_coles import over_prob
from src.models.eval_utils import per_match_log_loss
from src.models.goals_model import BlendedGoalModel
from src.models.model_utils import apply_probability_calibrator
from src.models.train_match_outcome import (
    LOCKED_SEASONS,
    N_CV_SPLITS,
    feature_set,
    fit_probability_calibrator,
)


logger = logging.getLogger("train_goals")

CHOSEN = {
    "kind": "blend_dc_feat",
    "dc_half_life_days": 365.0,
    "feature_alpha": 20.0,
    "dc_weight": 0.5,
}
OU_LINES = (1.5, 2.5, 3.5)
LABELS = [0, 1]


def _binary_probabilities(p_over: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p_over, dtype=float), 1e-6, 1.0 - 1e-6)
    return np.column_stack([1.0 - p, p])


def _forward_oof_predictions(
    df: pd.DataFrame,
    features: list[str],
) -> tuple[dict[float, np.ndarray], dict[float, np.ndarray]]:
    """Fit each fold only on earlier matches and collect raw OU probabilities."""
    probabilities: dict[float, list[np.ndarray]] = {line: [] for line in OU_LINES}
    targets: dict[float, list[np.ndarray]] = {line: [] for line in OU_LINES}
    splitter = TimeSeriesSplit(n_splits=N_CV_SPLITS)
    for train_idx, valid_idx in splitter.split(df):
        train = df.iloc[train_idx]
        valid = df.iloc[valid_idx]
        model = BlendedGoalModel(
            features,
            dc_half_life_days=CHOSEN["dc_half_life_days"],
            feature_alpha=CHOSEN["feature_alpha"],
            dc_weight=CHOSEN["dc_weight"],
        ).fit(train)
        matrices = model.predict_matrices(valid)
        total_goals = (valid["home_score"] + valid["away_score"]).to_numpy(dtype=float)
        for line in OU_LINES:
            probabilities[line].append(over_prob(matrices, line))
            targets[line].append((total_goals > line).astype(int))
    return (
        {line: np.concatenate(values) for line, values in probabilities.items()},
        {line: np.concatenate(values) for line, values in targets.items()},
    )


def _calibration_result(
    probabilities: np.ndarray,
    targets: np.ndarray,
) -> tuple[dict[str, Any] | None, dict[str, float]]:
    """Keep calibration only when expanding-window OOF loss improves."""
    raw = np.asarray(probabilities, dtype=float)
    y = np.asarray(targets, dtype=int)
    if len(raw) != len(y) or len(raw) < N_CV_SPLITS + 2:
        raise ValueError("Calibration predictions and targets must align and contain enough rows")

    raw_oof_losses: list[np.ndarray] = []
    calibrated_oof_losses: list[np.ndarray] = []
    splitter = TimeSeriesSplit(n_splits=N_CV_SPLITS)
    for train_idx, valid_idx in splitter.split(raw):
        calibrator = fit_probability_calibrator(
            _binary_probabilities(raw[train_idx]),
            pd.Series(y[train_idx]),
            LABELS,
        )
        valid_raw = _binary_probabilities(raw[valid_idx])
        valid_calibrated = apply_probability_calibrator(valid_raw, calibrator)
        raw_oof_losses.append(per_match_log_loss(valid_raw, y[valid_idx]))
        calibrated_oof_losses.append(per_match_log_loss(valid_calibrated, y[valid_idx]))

    raw_loss = float(np.concatenate(raw_oof_losses).mean())
    calibrated_loss = float(np.concatenate(calibrated_oof_losses).mean())
    use_calibrator = calibrated_loss < raw_loss
    final_calibrator = None
    if use_calibrator:
        final_calibrator = fit_probability_calibrator(
            _binary_probabilities(raw),
            pd.Series(y),
            LABELS,
        )
    return final_calibrator, {
        "raw_nested_oof_log_loss": raw_loss,
        "calibrated_nested_oof_log_loss": calibrated_loss,
        "calibration_applied": bool(use_calibrator),
        "nested_oof_matches": int(sum(len(losses) for losses in raw_oof_losses)),
    }


def train_goals_models(
    data_path: str = "data/processed/features_matches_all.parquet",
    evaluation_path: str = "data/processed/goal_model_outer_eval.json",
    model_output_dir: str = "models/production",
) -> dict[str, Any]:
    """Fit the selected model on played matches and calibrate on unlocked seasons."""
    source = Path(data_path)
    if not source.exists():
        raise FileNotFoundError(f"Goal-model feature data not found: {source}")
    evaluation_file = Path(evaluation_path)
    if not evaluation_file.exists():
        raise FileNotFoundError(
            f"Goal-model outer evaluation not found: {evaluation_file}. "
            "Run src.models.evaluate_goal_models before production training."
        )

    evaluation = json.loads(evaluation_file.read_text(encoding="utf-8"))
    gate = evaluation.get("o25_candidate_gates", {}).get(CHOSEN["kind"])
    if not gate or not gate.get("passed"):
        raise ValueError(f"Selected goal model did not pass the O2.5 gate: {CHOSEN['kind']}")

    df = pd.read_parquet(source)
    df = df[df["home_score"].notna() & df["away_score"].notna()].copy()
    required = {"season", "kickoff_millis", "match_id", "home_id", "away_id"}
    missing = required.difference(df.columns)
    if missing:
        raise KeyError(f"Goal-model training data missing columns: {sorted(missing)}")
    df = df.sort_values(["kickoff_millis", "match_id"], kind="mergesort").reset_index(drop=True)

    if LOCKED_SEASONS:
        eval_df = df[~df["season"].astype(str).isin(LOCKED_SEASONS)].copy().reset_index(drop=True)
    else:
        eval_df = df.copy()
    if eval_df.empty:
        raise ValueError("No unlocked played matches are available for OOF calibration")

    features = feature_set("o25", list(df.columns))
    oof_probabilities, oof_targets = _forward_oof_predictions(eval_df, features)
    calibrators: dict[str, dict[str, Any] | None] = {}
    calibration_metrics: dict[str, dict[str, Any]] = {}
    for line in OU_LINES:
        calibrator, metrics = _calibration_result(oof_probabilities[line], oof_targets[line])
        key = f"over_{line}"
        calibrators[key] = calibrator
        calibration_metrics[key] = metrics

    total_goals = (eval_df["home_score"] + eval_df["away_score"]).to_numpy(dtype=float)
    base_rates = {
        f"over_{line}": float(np.mean(total_goals > line))
        for line in OU_LINES
    }
    base_rates["btts"] = float(np.mean(
        (eval_df["home_score"].to_numpy(dtype=float) > 0)
        & (eval_df["away_score"].to_numpy(dtype=float) > 0)
    ))
    final_model = BlendedGoalModel(
        features,
        dc_half_life_days=CHOSEN["dc_half_life_days"],
        feature_alpha=CHOSEN["feature_alpha"],
        dc_weight=CHOSEN["dc_weight"],
    ).fit(df)

    artifact = {
        "model": final_model,
        "model_name": CHOSEN["kind"],
        "feature_names": features,
        "chosen": dict(CHOSEN),
        "ou_lines": list(OU_LINES),
        "calibrators": calibrators,
        "calibration_metrics": calibration_metrics,
        "base_rates": base_rates,
        "skill_gate": {
            "over_1.5": "model_matrix",
            "over_2.5": "model",
            "over_3.5": "model_matrix",
        },
        "locked_seasons_excluded_from_calibration": sorted(LOCKED_SEASONS),
        "calibration_matches": int(len(eval_df)),
        "production_fit_matches": int(len(df)),
        "evaluation_gate": gate,
    }

    output_dir = Path(model_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "goals_models_v1.joblib"
    joblib.dump(artifact, output_path)
    logger.info(
        "Saved %s goal model to %s (fit=%d, unlocked calibration rows=%d)",
        CHOSEN["kind"],
        output_path,
        len(df),
        len(eval_df),
    )
    return artifact


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_goals_models()
