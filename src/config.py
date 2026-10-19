"""Project paths and season policy: the single place that knows where things live.

Data paths follow ``PLM_DATA_DIR`` (default ``<repo>/data``), so a pipeline run can
be pointed at an isolated copy of the data. Models follow ``PLM_MODELS_DIR`` and
reports stay in ``docs/reports``. Importing this module has no side effects.
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("PLM_DATA_DIR") or ROOT / "data").resolve()
RAW_DIR = DATA_DIR / "raw"
MATCHES_RAW_DIR = RAW_DIR / "matches"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = DATA_DIR / "premier_league.db"
MATCHES_SUMMARY_PATH = PROCESSED_DIR / "matches_summary_all.parquet"
FEATURES_PATH = PROCESSED_DIR / "features_matches_all.parquet"
MODELS_DIR = Path(os.environ.get("PLM_MODELS_DIR") or ROOT / "models" / "production").resolve()
REPORTS_DIR = ROOT / "docs" / "reports"

# Pre-existing policy from earlier paired chronological experiments. Held fixed,
# not re-selected on the main holdout. These matches stay in feature history but
# 1X2 is not fitted on their labels.
EXCLUDED_1X2_TRAINING_SEASONS = {"2022_23"}
# Excluded from all evaluation, selection and calibration. Played matches may
# still be used to fit the final production estimator.
LOCKED_SEASONS = {"2026_27"}
