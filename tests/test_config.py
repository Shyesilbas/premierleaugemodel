import importlib
import os
import tempfile
from pathlib import Path
from unittest import mock

from src import config


def test_plm_data_dir_moves_every_data_path_but_not_models_or_reports():
    with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"PLM_DATA_DIR": tmp}):
        os.environ.pop("PLM_MODELS_DIR", None)
        os.environ.pop("PLM_REPORTS_DIR", None)
        cfg = importlib.reload(config)
        root = Path(tmp).resolve()
        assert cfg.DATA_DIR == root
        assert cfg.DB_PATH == root / "football.db"
        assert cfg.FEATURES_PATH == root / "competitions" / "premier_league" / "processed" / "features_matches_all.parquet"
        assert cfg.MATCHES_RAW_DIR == root / "competitions" / "premier_league" / "raw" / "matches"
        assert cfg.MODELS_DIR == cfg.ROOT / "models" / "production" / "premier_league"
        assert cfg.REPORTS_DIR == cfg.ROOT / "docs" / "reports"
    cfg = importlib.reload(config)  # back to whatever the caller's environment says
    assert cfg.DATA_DIR == Path(os.environ.get("PLM_DATA_DIR") or cfg.ROOT / "data").resolve()


def test_season_policy_is_reexported_for_existing_imports():
    from src.models.train_match_outcome import EXCLUDED_1X2_TRAINING_SEASONS, LOCKED_SEASONS

    assert LOCKED_SEASONS == config.LOCKED_SEASONS and "2026_27" in LOCKED_SEASONS
    assert EXCLUDED_1X2_TRAINING_SEASONS == config.EXCLUDED_1X2_TRAINING_SEASONS


def test_default_season_follows_plm_season_then_newest_fixtures_file():
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "competitions" / "premier_league" / "raw"
        raw.mkdir(parents=True)
        for season in ("2024_25", "2025_26", "2026_27"):
            (raw / f"fixtures_{season}.json").write_text("[]")
        with mock.patch.dict(os.environ, {"PLM_DATA_DIR": tmp}, clear=False):
            os.environ.pop("PLM_SEASON", None)
            cfg = importlib.reload(config)
            assert cfg.SEASONS == ["2024_25", "2025_26", "2026_27"] and cfg.DEFAULT_SEASON == "2026_27"
            with mock.patch.dict(os.environ, {"PLM_SEASON": "2025_26"}):
                assert importlib.reload(config).DEFAULT_SEASON == "2025_26"
    importlib.reload(config)


def test_display_path_is_relative_inside_the_repo_and_absolute_outside():
    assert config.display_path(config.ROOT / "docs" / "x.md") == str(Path("docs") / "x.md")
    assert config.display_path(Path("/somewhere/else.md")) == "/somewhere/else.md"


def test_every_competition_gets_its_own_data_and_model_folders():
    pl, laliga = config.competition_paths("premier_league"), config.competition_paths("la_liga")
    assert (pl.raw, pl.processed, pl.features, pl.models) == (config.RAW_DIR, config.PROCESSED_DIR, config.FEATURES_PATH, config.MODELS_DIR)
    assert laliga.raw == config.COMPETITIONS_DIR / "la_liga" / "raw"
    assert laliga.matches_raw == laliga.raw / "matches"
    assert laliga.features == config.COMPETITIONS_DIR / "la_liga" / "processed" / "features_matches_all.parquet"
    assert laliga.models == config.MODELS_ROOT / "la_liga"
    folders = [pl.raw, pl.processed, pl.models, laliga.raw, laliga.processed, laliga.models]
    assert len({str(f) for f in folders}) == len(folders)
    assert pl.processed not in laliga.processed.parents and laliga.processed not in pl.processed.parents
    assert laliga.fixtures("2026_27").name == "fixtures_2026_27.json"


def test_models_dir_override_moves_only_the_premier_league():
    with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"PLM_MODELS_DIR": tmp}):
        cfg = importlib.reload(config)
        assert cfg.competition_paths("premier_league").models == Path(tmp).resolve()
        assert cfg.competition_paths("la_liga").models == cfg.MODELS_ROOT / "la_liga"
    importlib.reload(config)
