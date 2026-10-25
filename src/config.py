"""Project paths and season policy: the single place that knows where things live.

Data paths follow ``PLM_DATA_DIR`` (default ``<repo>/data``), so a pipeline run can
be pointed at an isolated copy of the data. Models follow ``PLM_MODELS_DIR`` and
``PLM_REPORTS_DIR`` moves the generated reports (default ``docs/reports``). Importing this module has no side effects.
"""

from __future__ import annotations

import logging
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
REPORTS_DIR = Path(os.environ.get("PLM_REPORTS_DIR") or ROOT / "docs" / "reports").resolve()


def _fixture_seasons() -> list[str]:
    return sorted(path.stem.removeprefix("fixtures_") for path in RAW_DIR.glob("fixtures_*.json"))


# Every cached season, oldest first, and the one scripts default to: PLM_SEASON, else the
# newest fixtures file. "2026_27" is only the fallback for a data dir without fixtures.
SEASONS = _fixture_seasons()
DEFAULT_SEASON = os.environ.get("PLM_SEASON") or (SEASONS[-1] if SEASONS else "2026_27")

# Pre-existing policy from earlier paired chronological experiments. Held fixed,
# not re-selected on the main holdout. These matches stay in feature history but
# 1X2 is not fitted on their labels.
EXCLUDED_1X2_TRAINING_SEASONS = {"2022_23"}
# Excluded from all evaluation, selection and calibration. Played matches may
# still be used to fit the final production estimator.
LOCKED_SEASONS = {"2026_27"}

SEASON_ORDER: dict[str, int] = {
    "2022_23": 0,
    "2023_24": 1,
    "2024_25": 2,
    "2025_26": 3,
    "2026_27": 4,
}


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the root logger once. Call from entry points only, never at import time."""
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


def display_path(path: Path) -> str:
    """Repo-relative path for log lines when inside the repo, else the absolute path."""
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)
