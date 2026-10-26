"""Project paths and season policy: the single place that knows where things live.

Every competition owns one folder per kind of artifact, so leagues never share files::

    data/football.db                            shared SQLite store; every match row carries competition_id
    data/competitions/<key>/raw/                provider downloads (fixtures_<season>.json, matches/<id>_*.json)
    data/competitions/<key>/processed/          parquet tables, features, evaluation JSON, forecast log
    models/production/<key>/                    trained .joblib artifacts of that competition

``competition_paths(key)`` is the way to reach them. The module-level constants (``RAW_DIR``, ``PROCESSED_DIR``,
``FEATURES_PATH``, ``MODELS_DIR`` ...) are the Premier League's paths, which most of the pipeline still uses.

``PLM_DATA_DIR`` moves everything under ``data/`` (so a run can use an isolated copy), ``PLM_MODELS_ROOT`` moves
``models/production`` and ``PLM_MODELS_DIR`` points the Premier League at one specific artifact folder.
``PLM_REPORTS_DIR`` moves the generated reports (default ``docs/reports``). Importing this module has no side effects.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("PLM_DATA_DIR") or ROOT / "data").resolve()
COMPETITIONS_DIR = DATA_DIR / "competitions"
DB_PATH = DATA_DIR / "football.db"
MODELS_ROOT = Path(os.environ.get("PLM_MODELS_ROOT") or ROOT / "models" / "production").resolve()
REPORTS_DIR = Path(os.environ.get("PLM_REPORTS_DIR") or ROOT / "docs" / "reports").resolve()
DEFAULT_COMPETITION = "premier_league"


@dataclass(frozen=True)
class CompetitionPaths:
    """Where one competition keeps its raw downloads, processed tables and trained models."""

    key: str
    raw: Path
    matches_raw: Path
    processed: Path
    summary: Path
    features: Path
    models: Path

    def fixtures(self, season: str) -> Path:
        return self.raw / f"fixtures_{season}.json"

    def fixture_seasons(self) -> list[str]:
        return sorted(path.stem.removeprefix("fixtures_") for path in self.raw.glob("fixtures_*.json"))


def competition_paths(key: str = DEFAULT_COMPETITION) -> CompetitionPaths:
    """Paths of one competition; nothing is created on disk."""
    root = COMPETITIONS_DIR / key
    if key == DEFAULT_COMPETITION and os.environ.get("PLM_MODELS_DIR"):
        models = Path(os.environ["PLM_MODELS_DIR"]).resolve()
    else:
        models = MODELS_ROOT / key
    return CompetitionPaths(
        key=key,
        raw=root / "raw",
        matches_raw=root / "raw" / "matches",
        processed=root / "processed",
        summary=root / "processed" / "matches_summary_all.parquet",
        features=root / "processed" / "features_matches_all.parquet",
        models=models,
    )


_PL = competition_paths(DEFAULT_COMPETITION)
RAW_DIR = _PL.raw
MATCHES_RAW_DIR = _PL.matches_raw
PROCESSED_DIR = _PL.processed
MATCHES_SUMMARY_PATH = _PL.summary
FEATURES_PATH = _PL.features
MODELS_DIR = _PL.models


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
