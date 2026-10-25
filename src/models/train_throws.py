#!/usr/bin/env python3
"""
Throws Prediction Model (Regularized Regression & Count Probabilities)
Predicts total match throws (taç) and probabilities for Over 33.5 / 34.5 / 36.5 throws.
Uses strictly curated, domain-relevant features (throws for/against, possession, tempo).
Evaluated with Time-Series Split and refitted on 100% data for production.
"""

import logging
from typing import Any, Dict

from src.config import FEATURES_PATH, MODELS_DIR, configure_logging
from src.models.count_model import CountModelSpec, train_count_model

logger = logging.getLogger("train_throws")

CURATED_FEATURES = [
    "home_throws_roll_5",
    "home_throws_roll_10",
    "away_throws_roll_10",
    "home_opponent_throws_roll_10",
    "away_opponent_throws_roll_5",
    "away_opponent_throws_roll_10",
    "exp_home_throws_5",
    "exp_away_throws_5",
    "home_possession_roll_5",
    "away_possession_roll_5",
    "home_pass_pct_roll_10",
    "away_pass_pct_roll_10",
    "home_inacc_fwd_pass_roll_10",
    "away_inacc_fwd_pass_roll_10",
]

THROWS_MODEL_SPEC = CountModelSpec(
    name="Throws",
    label="Throws",
    target_col="total_throws",
    artifact_filename="throws_model_v1.joblib",
    features=tuple(CURATED_FEATURES),
    thresholds=(34,),
    primary_threshold=34,
    ridge_alphas=(1.0, 10.0, 50.0, 100.0, 500.0),
    include_elastic=False,
    lgbm_params={"learning_rate": 0.02, "n_estimators": 60},
)


def train_throws_model(
    data_path: str = str(FEATURES_PATH),
    model_output_dir: str = str(MODELS_DIR),
) -> Dict[str, Any]:
    return train_count_model(THROWS_MODEL_SPEC, data_path, model_output_dir, logger)


if __name__ == "__main__":
    configure_logging()
    train_throws_model()
