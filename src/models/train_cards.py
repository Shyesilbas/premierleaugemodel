#!/usr/bin/env python3
"""
Premier League Cards Prediction Model (Regularized Regression & Count Probabilities)
Predicts total match cards (Yellow + Red) and probabilities for Over 3.5 / 4.5 cards.
Uses curated pre-match discipline features and referee aggregates (no raw IDs).
Candidate selection uses expanding chronological folds; the final holdout is scored once.
"""

import logging
from typing import Any, Dict

from src.config import FEATURES_PATH, MODELS_DIR, configure_logging
from src.models.count_model import CountModelSpec, train_count_model

logger = logging.getLogger("train_cards")

CURATED_FEATURES = [
    "home_cards_for_roll_5",
    "away_cards_for_roll_5",
    "home_cards_against_roll_5",
    "away_cards_against_roll_5",
    "home_fouls_committed_roll_5",
    "away_fouls_committed_roll_5",
    "home_fouls_drawn_roll_5",
    "away_fouls_drawn_roll_5",
    "abs_elo_diff",
    "referee_avg_cards",
    "referee_avg_fouls",
]

CARDS_MODEL_SPEC = CountModelSpec(
    name="Cards",
    label="Cards",
    target_col="total_cards",
    artifact_filename="cards_model_v1.joblib",
    features=tuple(CURATED_FEATURES),
    thresholds=(3, 4),
    primary_threshold=3,
    ridge_alphas=(0.1, 1.0, 10.0, 50.0, 100.0, 250.0, 500.0),
    include_elastic=True,
    lgbm_params={"learning_rate": 0.03, "n_estimators": 50},
    top_features_as_records=True,
    include_target_col_in_artifact=True,
    legacy_metric_aliases={
        "o35_accuracy": "over_3_5_accuracy_pct",
        "o35_majority_baseline": "majority_baseline_pct",
        "o45_accuracy": "over_4_5_accuracy_pct",
    },
)


def train_cards_model(
    data_path: str = str(FEATURES_PATH),
    model_output_dir: str = str(MODELS_DIR),
) -> Dict[str, Any]:
    return train_count_model(CARDS_MODEL_SPEC, data_path, model_output_dir, logger)


if __name__ == "__main__":
    configure_logging()
    train_cards_model()
