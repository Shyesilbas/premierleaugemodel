import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pandas as pd

from src.analytics.pipeline_health import collect, evaluate


def _build(root: Path, raw_missing: bool = False, xg_ids=(1, 2)):
    matches = pd.DataFrame({
        "match_id": [1, 2, 3, 4],
        "season": ["2024_25", "2024_25", "2025_26", "2025_26"],
        "gameweek": [1, 2, 1, 2],
        "kickoff_millis": [1.7e12, 1.7e12 + 1e9, 1.8e12, 1.8e12 + 1e9],
        "home_score": [1.0, 2.0, 0.0, None],
    })
    matches.to_parquet(root / "features.parquet")
    with sqlite3.connect(root / "db.sqlite") as conn:
        conn.execute("CREATE TABLE matches (match_id INTEGER, competition_id INTEGER)")
        conn.execute("CREATE TABLE external_match_xg (match_id INTEGER)")
        conn.execute("CREATE TABLE external_match_odds (match_id INTEGER, bookmaker TEXT)")
        conn.executemany("INSERT INTO matches VALUES (?, 39)", [(i,) for i in (1, 2, 3, 4)])
        conn.execute("INSERT INTO matches VALUES (900, 2)")  # a European match is not a Premier League feature row
        conn.executemany("INSERT INTO external_match_xg VALUES (?)", [(i,) for i in xg_ids])
        conn.executemany("INSERT INTO external_match_odds VALUES (?, 'Bet365')", [(i,) for i in (1, 2, 3)])
    (root / "raw").mkdir()
    for m in (1, 2, 3):
        for kind in ("stats", "stream", "details"):
            if not (raw_missing and (m, kind) == (3, "details")):
                (root / "raw" / f"{m}_{kind}.json").write_text("{}")
    (root / "models").mkdir()
    (root / "models" / "m.joblib").write_bytes(b"x")
    return dict(
        features_path=root / "features.parquet", db_path=root / "db.sqlite",
        raw_dir=root / "raw", models_dir=root / "models",
    )


def test_latest_season_xg_gap_is_a_warning_with_its_gameweek():
    with tempfile.TemporaryDirectory() as tmp:
        paths = _build(Path(tmp), xg_ids=(1, 2))
        findings = evaluate(collect(**paths))
    levels = [level for level, _ in findings]
    assert "FAIL" not in levels
    assert any("2025_26" in text and "xG" in text and "[1]" in text for _, text in findings)


def test_incomplete_raw_cache_is_a_failure():
    with tempfile.TemporaryDirectory() as tmp:
        paths = _build(Path(tmp), raw_missing=True, xg_ids=(1, 2, 3))
        findings = evaluate(collect(**paths))
    assert any(level == "FAIL" and "stats/stream/details" in text for level, text in findings)


def test_clean_data_has_no_findings():
    with tempfile.TemporaryDirectory() as tmp:
        paths = _build(Path(tmp), xg_ids=(1, 2, 3))
        report = collect(**paths)
        report["model_days_behind_last_match"] = {"m.joblib": 1.0}
        findings = evaluate(report)
    assert findings == [], findings


def test_fetch_season_data_exits_nonzero_when_any_match_failed():
    from src.ingest import fetch_season_data

    summary = {"errors_count": 1, "errors": [{"match_id": 7, "error": "boom"}]}
    with mock.patch.object(fetch_season_data, "run_pipeline", return_value=summary), \
         mock.patch.object(sys, "argv", ["x", "--season", "1", "--season-name", "t"]):
        try:
            fetch_season_data.main()
        except SystemExit as exit_:
            assert exit_.code == 1
        else:
            raise AssertionError("expected SystemExit(1)")
