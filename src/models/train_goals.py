"""Train and persist the selected production score-matrix model."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from src.models.dixon_coles import DixonColesModel, btts_prob, matrix_from_lambdas, over_prob
from src.models.eval_utils import per_match_log_loss
from src.models.goals_model import BlendedGoalModel, FeatureGoalModel, blend_lambdas
from src.models.model_utils import apply_probability_calibrator
from src.models.train_match_outcome import (
    LOCKED_SEASONS,
    N_CV_SPLITS,
    feature_set,
    fit_probability_calibrator,
    forward_time_splits,
)


logger = logging.getLogger("train_goals")

# Single source of the blend search space; evaluate_goal_models runs the same
# selection inside each outer season, so its gate validates this procedure.
BLEND_GRID = {
    "kind": "blend_dc_feat",
    "dc_half_life_days": 365.0,
    "feature_sets": ["compact", "full"],
    "feature_alphas": [0.1, 0.3, 1.0, 3.0, 10.0, 30.0],
    # DC weight 0 only: nested outer seasons chose it every time and beat the 0/0.25/0.5 grid by
    # 0.0217 score NLL (GOAL_MODELS_ANALYSIS P8); DC still supplies half of the shared rho.
    "dc_weights": [0.0],
}
# Fixed a priori (not tuned on outer seasons): one strength rating per side,
# one recency form version (ewma_02) of chance quality and shot volume for and
# against, plus expected match tempo. Every column is already in the full set.
COMPACT_GOAL_FEATURES = [
    "elo_home", "elo_away",
    "home_xg_for_ewma_02", "home_xg_against_ewma_02",
    "away_xg_for_ewma_02", "away_xg_against_ewma_02",
    "home_shots_ontarget_for_ewma_02", "home_shots_ontarget_against_ewma_02",
    "away_shots_ontarget_for_ewma_02", "away_shots_ontarget_against_ewma_02",
    "exp_match_shots_5",
]
SCORE_CAP = 12  # last row/column of the score matrix
OU_LINES = (1.5, 2.5, 3.5)
LABELS = [0, 1]


def goal_feature_sets(columns: list[str]) -> dict[str, list[str]]:
    """Return the candidate goal-model feature lists named in ``BLEND_GRID``."""
    full = feature_set("o25", columns)
    missing = [column for column in COMPACT_GOAL_FEATURES if column not in full]
    if missing:
        raise KeyError(f"Compact goal features must be a subset of the full set: {missing}")
    return {"full": full, "compact": list(COMPACT_GOAL_FEATURES)}


def _binary_probabilities(p_over: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p_over, dtype=float), 1e-6, 1.0 - 1e-6)
    return np.column_stack([1.0 - p, p])


def blend_model(features: list[str], chosen: dict[str, Any]) -> BlendedGoalModel:
    """Build the unfitted blend described by a ``select_blend_config`` result."""
    return BlendedGoalModel(
        features,
        dc_half_life_days=chosen["dc_half_life_days"],
        feature_alpha=chosen["feature_alpha"],
        dc_weight=chosen["dc_weight"],
    )


def select_blend_config(df: pd.DataFrame, feature_sets: dict[str, list[str]]) -> dict[str, Any]:
    """Pick feature set, feature_alpha and dc_weight by forward-fold score-matrix NLL using ``df`` only."""
    kickoffs = df["kickoff_millis"] if "kickoff_millis" in df.columns else None
    losses: dict[tuple[str, float, float], list[np.ndarray]] = {}
    for train_idx, valid_idx in forward_time_splits(len(df), kickoffs, n_splits=N_CV_SPLITS):
        train, valid = df.iloc[train_idx], df.iloc[valid_idx]
        dc = DixonColesModel(half_life_days=BLEND_GRID["dc_half_life_days"]).fit(train)
        if not dc.fit_ok_:
            # Same rule as BlendedGoalModel: never score a blend on an unconverged DC fit.
            logger.warning("Skipping selection fold: Dixon-Coles did not converge on %d rows", len(train))
            continue
        dc_home, dc_away = dc.lambdas(valid)
        cells = np.arange(len(valid))
        home_goals = np.minimum(valid["home_score"].to_numpy(dtype=int), SCORE_CAP)
        away_goals = np.minimum(valid["away_score"].to_numpy(dtype=int), SCORE_CAP)
        for set_name in BLEND_GRID["feature_sets"]:
            for alpha in BLEND_GRID["feature_alphas"]:
                feat = FeatureGoalModel(feature_sets[set_name], alpha=alpha).fit(train)
                feat_home, feat_away = feat.lambdas(valid)
                rho = 0.5 * (dc.rho_ + feat.rho_)
                for weight in BLEND_GRID["dc_weights"]:
                    matrices = matrix_from_lambdas(
                        blend_lambdas(dc_home, feat_home, weight),
                        blend_lambdas(dc_away, feat_away, weight),
                        rho,
                    )
                    losses.setdefault((set_name, alpha, weight), []).append(
                        -np.log(matrices[cells, home_goals, away_goals])
                    )
    if not losses:
        raise RuntimeError("No selection fold had a converged Dixon-Coles fit")
    pooled = {key: np.concatenate(parts) for key, parts in losses.items()}
    # The matrix carries goal difference and team goals, which O2.5 alone cannot rank
    # (total-goals signal is weak), so the lowest score NLL wins with no tie-break.
    set_name, alpha, weight = min(pooled, key=lambda key: float(pooled[key].mean()))
    return {
        "kind": BLEND_GRID["kind"],
        "dc_half_life_days": BLEND_GRID["dc_half_life_days"],
        "feature_set": set_name,
        "feature_alpha": float(alpha),
        "dc_weight": float(weight),
    }


def _forward_oof_predictions(
    df: pd.DataFrame,
    features: list[str],
    chosen: dict[str, Any],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], np.ndarray]:
    """Fit each fold only on earlier matches and collect raw OU and BTTS probabilities."""
    keys = [f"over_{line}" for line in OU_LINES] + ["btts"]
    probabilities: dict[str, list[np.ndarray]] = {k: [] for k in keys}
    targets: dict[str, list[np.ndarray]] = {k: [] for k in keys}
    oof_kickoffs: list[np.ndarray] = []

    kickoffs = df["kickoff_millis"] if "kickoff_millis" in df.columns else None
    for train_idx, valid_idx in forward_time_splits(len(df), kickoffs, n_splits=N_CV_SPLITS):
        train = df.iloc[train_idx]
        valid = df.iloc[valid_idx]
        oof_kickoffs.append(valid["kickoff_millis"].to_numpy())
        model = blend_model(features, chosen).fit(train)
        matrices = model.predict_matrices(valid)

        hs = valid["home_score"].to_numpy(dtype=float)
        as_ = valid["away_score"].to_numpy(dtype=float)
        total_goals = hs + as_

        for line in OU_LINES:
            k = f"over_{line}"
            probabilities[k].append(over_prob(matrices, line))
            targets[k].append((total_goals > line).astype(int))

        probabilities["btts"].append(btts_prob(matrices))
        targets["btts"].append(((hs > 0) & (as_ > 0)).astype(int))

    return (
        {k: np.concatenate(values) for k, values in probabilities.items()},
        {k: np.concatenate(values) for k, values in targets.items()},
        np.concatenate(oof_kickoffs),
    )


def _calibration_result(
    probabilities: np.ndarray,
    targets: np.ndarray,
    kickoffs: np.ndarray,
) -> tuple[dict[str, Any] | None, dict[str, float]]:
    """Score the calibrator on later OOF rows only and return it when it lowers log loss."""
    raw = np.asarray(probabilities, dtype=float)
    y = np.asarray(targets, dtype=int)
    if len(raw) != len(y) or len(raw) != len(kickoffs) or len(raw) < N_CV_SPLITS + 2:
        raise ValueError("Calibration predictions and targets must align and contain enough rows")

    scored_parts: list[np.ndarray] = []
    calibrated_parts: list[np.ndarray] = []
    for tr_idx, val_idx in forward_time_splits(len(raw), kickoffs, n_splits=N_CV_SPLITS):
        fold_calibrator = fit_probability_calibrator(
            _binary_probabilities(raw[tr_idx]),
            pd.Series(y[tr_idx]),
            LABELS,
        )
        val_cal = apply_probability_calibrator(_binary_probabilities(raw[val_idx]), fold_calibrator)
        scored_parts.append(val_idx)
        calibrated_parts.append(val_cal[:, 1])
    scored = np.concatenate(scored_parts)

    raw_bin = _binary_probabilities(raw[scored])
    cal_bin = _binary_probabilities(np.concatenate(calibrated_parts))
    raw_loss = float(per_match_log_loss(raw_bin, y[scored]).mean())
    calibrated_loss = float(per_match_log_loss(cal_bin, y[scored]).mean())
    use_calibrator = calibrated_loss < raw_loss
    final_calibrator = None
    if use_calibrator:
        final_calibrator = fit_probability_calibrator(
            _binary_probabilities(raw),
            pd.Series(y),
            LABELS,
        )
    return final_calibrator, {
        "raw_oof_log_loss": raw_loss,
        "calibrated_oof_log_loss": calibrated_loss,
        "calibration_applied": bool(use_calibrator),
        "oof_matches": int(len(raw)),
        "scored_matches": int(len(scored)),
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
    gate = evaluation.get("o25_candidate_gates", {}).get(BLEND_GRID["kind"])
    if not gate or not gate.get("passed"):
        raise ValueError(f"Selected goal model did not pass the O2.5 gate: {BLEND_GRID['kind']}")
    if gate.get("selection_grid") != BLEND_GRID:
        raise ValueError(
            "Goal-model gate was produced with a different selection grid; "
            "rerun src.models.evaluate_goal_models first."
        )

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

    feature_sets = goal_feature_sets(list(df.columns))
    chosen = select_blend_config(eval_df, feature_sets)
    features = feature_sets[chosen["feature_set"]]
    logger.info("Selected goal blend on unlocked forward folds: %s", chosen)
    oof_probabilities, oof_targets, oof_kickoffs = _forward_oof_predictions(eval_df, features, chosen)
    calibrators: dict[str, dict[str, Any] | None] = {}
    calibration_metrics: dict[str, dict[str, Any]] = {}
    for key in [f"over_{line}" for line in OU_LINES] + ["btts"]:
        calibrators[key], calibration_metrics[key] = _calibration_result(
            oof_probabilities[key], oof_targets[key], oof_kickoffs
        )

    total_goals = (eval_df["home_score"] + eval_df["away_score"]).to_numpy(dtype=float)
    base_rates = {
        f"over_{line}": float(np.mean(total_goals > line))
        for line in OU_LINES
    }
    base_rates["btts"] = float(np.mean(
        (eval_df["home_score"].to_numpy(dtype=float) > 0)
        & (eval_df["away_score"].to_numpy(dtype=float) > 0)
    ))
    final_model = blend_model(features, chosen).fit(df)

    artifact = {
        "model": final_model,
        "model_name": chosen["kind"],
        "feature_names": features,
        "chosen": chosen,
        "selection_grid": BLEND_GRID,
        "ou_lines": list(OU_LINES),
        "calibrators": calibrators,
        "calibration_metrics": calibration_metrics,
        "base_rates": base_rates,
        "skill_gate": {
            "over_1.5": "model_matrix",
            "over_2.5": "model",
            "over_3.5": "model_matrix",
            "btts": "model_matrix",
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
        chosen["kind"],
        output_path,
        len(df),
        len(eval_df),
    )
    return artifact


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_goals_models()
