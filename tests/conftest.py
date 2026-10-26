"""Shared pytest setup.

Tests marked ``needs_data`` read the local data lake and the trained models, which are not in
git (``data/football.db``, parquet files, ``models/production``). They are skipped on a
fresh clone or in CI instead of failing; everything else must run on synthetic data.
"""

import pytest

from src.config import FEATURES_PATH, MATCHES_RAW_DIR, MATCHES_SUMMARY_PATH, MODELS_DIR


def _missing_local_data() -> list[str]:
    needed = {
        "features parquet": FEATURES_PATH,
        "matches summary parquet": MATCHES_SUMMARY_PATH,
        "raw match cache": MATCHES_RAW_DIR,
        "production models": MODELS_DIR / "outcome_models_v1.joblib",
    }
    return [name for name, path in needed.items() if not path.exists()]


def pytest_collection_modifyitems(config, items):
    missing = _missing_local_data()
    if not missing:
        return
    skip = pytest.mark.skip(reason="needs local data and models (missing: " + ", ".join(missing) + ")")
    for item in items:
        if item.get_closest_marker("needs_data"):
            item.add_marker(skip)
