#!/usr/bin/env python3
"""
Offside Prediction Model (Regularized Regression & Count Probabilities)
Predicts total match offsides and probabilities for Over 2.5 / 3.5 / 4.5 offsides.
Uses strictly curated, domain-relevant features (offsides for/against, defensive line proxy, possession).
Evaluated with Time-Series Split and refitted on 100% data for production.
"""

import logging
from typing import Any, Dict

from src.config import FEATURES_PATH, MODELS_DIR, configure_logging
from src.models.count_model import CountModelSpec, train_count_model

logger = logging.getLogger("train_offsides")

CURATED_FEATURES = [
    "home_offsides_for_roll_5",
    "home_offsides_for_roll_10",
    "away_offsides_for_roll_5",
    "away_offsides_for_roll_10",
    "home_offsides_against_roll_5",
    "away_offsides_against_roll_5",
    "home_offsides_against_roll_10",
    "away_offsides_against_roll_10",
    "home_possession_roll_5",
    "away_possession_roll_5",
]

OFFSIDES_MODEL_SPEC = CountModelSpec(
    name="Offsides",
    label="Offside",
    target_col="total_offsides",
    artifact_filename="offside_model_v1.joblib",
    features=tuple(CURATED_FEATURES),
    thresholds=(3,),
    primary_threshold=3,
    ridge_alphas=(0.1, 1.0, 10.0, 50.0, 100.0, 250.0, 500.0),
    include_elastic=True,
    lgbm_params={"learning_rate": 0.03, "n_estimators": 55},
    round_top_features=True,
    include_target_col_in_artifact=True,
)


def train_offsides_model(
    data_path: str = str(FEATURES_PATH),
    model_output_dir: str = str(MODELS_DIR),
) -> Dict[str, Any]:
    return train_count_model(OFFSIDES_MODEL_SPEC, data_path, model_output_dir, logger)


if __name__ == "__main__":
    configure_logging()
    train_offsides_model()
