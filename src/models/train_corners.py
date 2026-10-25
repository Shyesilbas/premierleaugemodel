#!/usr/bin/env python3
"""
Corner Prediction Model (Regularized Regression & Count Probabilities)
Predicts total match corners and probabilities for Over 8.5 / 9.5 / 10.5 corners.
Uses strictly curated, domain-relevant features (corners, shots, possession, box entries).
Evaluated with Time-Series Split and refitted on 100% data for production.
"""

import logging
from typing import Any, Dict

from src.config import FEATURES_PATH, MODELS_DIR, configure_logging
from src.models.count_model import CountModelSpec, train_count_model

logger = logging.getLogger("train_corners")

CURATED_FEATURES = [
    "home_corners_for_roll_10",
    "away_corners_for_roll_10",
    "home_corners_against_roll_10",
    "away_corners_against_roll_10",
    "home_corners_for_roll_5",
    "away_corners_for_roll_5",
    "home_shots_for_roll_5",
    "away_shots_for_roll_5",
    "home_touches_in_opp_box_roll_5",
    "away_touches_in_opp_box_roll_5",
]

CORNER_MODEL_SPEC = CountModelSpec(
    name="Corners",
    label="Corner",
    target_col="total_corners",
    artifact_filename="corner_model_v1.joblib",
    features=tuple(CURATED_FEATURES),
    thresholds=(8, 9, 10),
    primary_threshold=9,
    ridge_alphas=(1.0, 10.0, 50.0, 100.0, 250.0, 500.0),
    include_elastic=True,
    lgbm_params={"learning_rate": 0.02, "n_estimators": 55},
)


def train_corners_model(
    data_path: str = str(FEATURES_PATH),
    model_output_dir: str = str(MODELS_DIR),
) -> Dict[str, Any]:
    return train_count_model(CORNER_MODEL_SPEC, data_path, model_output_dir, logger)


if __name__ == "__main__":
    configure_logging()
    train_corners_model()
