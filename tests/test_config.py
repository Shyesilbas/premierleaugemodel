import importlib
import os
import tempfile
from pathlib import Path
from unittest import mock

from src import config


def test_plm_data_dir_moves_every_data_path_but_not_models_or_reports():
    with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"PLM_DATA_DIR": tmp}):
        os.environ.pop("PLM_MODELS_DIR", None)
        cfg = importlib.reload(config)
        root = Path(tmp).resolve()
        assert cfg.DATA_DIR == root
        assert cfg.DB_PATH == root / "premier_league.db"
        assert cfg.FEATURES_PATH == root / "processed" / "features_matches_all.parquet"
        assert cfg.MATCHES_RAW_DIR == root / "raw" / "matches"
        assert cfg.MODELS_DIR == cfg.ROOT / "models" / "production"
        assert cfg.REPORTS_DIR == cfg.ROOT / "docs" / "reports"
    cfg = importlib.reload(config)  # back to whatever the caller's environment says
    assert cfg.DATA_DIR == Path(os.environ.get("PLM_DATA_DIR") or cfg.ROOT / "data").resolve()


def test_season_policy_is_reexported_for_existing_imports():
    from src.models.train_match_outcome import EXCLUDED_1X2_TRAINING_SEASONS, LOCKED_SEASONS

    assert LOCKED_SEASONS == config.LOCKED_SEASONS and "2026_27" in LOCKED_SEASONS
    assert EXCLUDED_1X2_TRAINING_SEASONS == config.EXCLUDED_1X2_TRAINING_SEASONS


def test_default_season_follows_plm_season_then_newest_fixtures_file():
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw"
        raw.mkdir()
        for season in ("2024_25", "2025_26", "2026_27"):
            (raw / f"fixtures_{season}.json").write_text("[]")
        with mock.patch.dict(os.environ, {"PLM_DATA_DIR": tmp}, clear=False):
            os.environ.pop("PLM_SEASON", None)
            cfg = importlib.reload(config)
            assert cfg.SEASONS == ["2024_25", "2025_26", "2026_27"] and cfg.DEFAULT_SEASON == "2026_27"
            with mock.patch.dict(os.environ, {"PLM_SEASON": "2025_26"}):
                assert importlib.reload(config).DEFAULT_SEASON == "2025_26"
    importlib.reload(config)
