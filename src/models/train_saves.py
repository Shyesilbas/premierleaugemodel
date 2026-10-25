#!/usr/bin/env python3
"""
Goalkeeper Saves Prediction Model (Regularized Ridge & Baseline Shrinkage)
Predicts total match goalkeeper saves.
Uses strictly curated, domain-relevant features (shots conceded, shots on target conceded, xG against).
Evaluated with Time-Series Split and refitted on 100% data for production.
"""

import logging
from typing import Any, Dict

from src.config import FEATURES_PATH, MODELS_DIR, configure_logging
from src.models.count_model import CountModelSpec, train_count_model

logger = logging.getLogger("train_saves")

CURATED_FEATURES = [
    "home_saves_roll_3",
    "home_saves_roll_5",
    "home_saves_roll_10",
    "away_saves_roll_3",
    "away_saves_roll_5",
    "away_saves_roll_10",
    "home_shots_against_roll_5",
    "away_shots_against_roll_5",
    "home_shots_ontarget_against_roll_5",
    "away_shots_ontarget_against_roll_5",
    "home_shots_for_roll_5",
    "away_shots_for_roll_5",
    "exp_match_shots_5",
]

SAVES_MODEL_SPEC = CountModelSpec(
    name="Saves",
    label="Saves",
    target_col="total_saves",
    artifact_filename="saves_model_v1.joblib",
    features=tuple(CURATED_FEATURES),
    thresholds=(),
    ridge_alphas=(0.1, 1.0, 10.0, 50.0, 100.0, 500.0, 1000.0),
    include_elastic=False,
    lgbm_params={"max_depth": 2, "num_leaves": 4, "learning_rate": 0.02, "n_estimators": 40},
)


def train_saves_model(
    data_path: str = str(FEATURES_PATH),
    model_output_dir: str = str(MODELS_DIR),
) -> Dict[str, Any]:
    return train_count_model(SAVES_MODEL_SPEC, data_path, model_output_dir, logger)


if __name__ == "__main__":
    configure_logging()
    train_saves_model()
