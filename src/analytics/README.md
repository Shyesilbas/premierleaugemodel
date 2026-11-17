# Analytics Module

Produces prospective forward-test tracking scorecards, historical model audits, data-quality checks, pipeline health validation, tactical/scenario profiles, player ratings, and league statistics.

> [!NOTE]
> **Related Documentation & Runbooks:**
> - **Protocols & Reports:** [`docs/paper_trading_protocol_2026_27.md`](../../docs/paper_trading_protocol_2026_27.md) · [`reports/README.md`](../../reports/README.md) · [`docs/data_and_ui_catalog.md`](../../docs/data_and_ui_catalog.md)
> - **Key Entry Points:** [`prospective_1x2_benchmark.py`](prospective_1x2_benchmark.py) · [`model_audit.py`](model_audit.py) · [`league_stats.py`](league_stats.py) · [`player_ratings.py`](player_ratings.py) · [`team_tactics.py`](team_tactics.py) · [`team_scenarios.py`](team_scenarios.py) · [`team_attackers.py`](team_attackers.py) · [`pipeline_health.py`](pipeline_health.py) · [`data_quality_report.py`](data_quality_report.py) · [`league_feature_audit.py`](league_feature_audit.py)

## Business Rules & Invariants
- **Append-Only Pre-Kickoff Snapshots:** `prospective_1x2_benchmark.py` (`snapshot` / `score`) locks one pre-kickoff record per match per day into `1x2_forecast_log.jsonl` with model SHA-256 fingerprints (`_artifact_fingerprint`) and scores completed matches into `REPORTS_DIR / prospective_1x2_scorecard*.json`.
- **Hybrid Model Audit:** `model_audit.py` keeps logged pre-game `prospective` predictions untouched alongside labeled `in_sample_backfill` rows (Premier League only), computing proper 1X2 metrics (`log_loss`, `brier`, `rps`), Elo/base-rate/market bootstrap comparisons, confidence calibration bands, and prospective scorecard summaries.
- **Pure League Statistics Engine:** `build_league_stats` in [`league_stats.py`](league_stats.py) accepts in-memory tables so scope-specific and cumulative rankings run offline in unit tests (`tests/test_league_stats.py`).
- **Dynamic Player Ratings:** `calculate_single_match_score` and `get_player_dynamic_rating` in [`player_ratings.py`](player_ratings.py) weight recent form (70% EWMA) with seasonal baseline (30%).
- **Change rule:** Automated report generators (`data_quality_report.py`, `team_data_audit.py`, `audit_team_scenarios.py`) write via `REPORTS_DIR`; never hand-edit generated outputs.
