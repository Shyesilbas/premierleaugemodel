---
name: sports-pipeline-and-paper-trading
description: >-
  Use this skill when running or modifying data ingestion pipelines, multi-league SQLite storage,
  Parquet rebuilds, lineup synchronization, early-season priors, or append-only pre-game paper
  trading / forecast ledgers.
---

# Sports Data Pipeline, Store & Paper Trading Workflow

Follow this workflow when modifying or running ingestion tools (`src/ingest/`), rebuild orchestration (`src/pipeline/`), SQLite persistence (`src/db/`), or forward-testing ledgers (`1x2_forecast_log.jsonl`).

## 1. Data Inspection & Path Hygiene
1. **Never Read Raw Binary or Giant Data Files:** Never open `.parquet`, `.db`, `.joblib`, or raw `raw/matches/*.json` dumps directly into context. Inspect SQLite via `sqlite3 data/football.db "SELECT ... LIMIT 5;"` or `.schema`.
2. **Centralized Path Resolution:** Always resolve paths through `src/config.py` (`competition_paths(key)`, `DATA_DIR`, `DB_PATH`, `MODELS_ROOT`, `REPORTS_DIR`) so `PLM_DATA_DIR`, `PLM_MODELS_DIR`, and `PLM_REPORTS_DIR` isolation works everywhere.
3. **Zero Emoji & Non-Blocking Locks:** Keep zero emojis in CLI/log outputs; respect file locks (`raw_store.competition_lock`) so concurrent sync jobs cannot corrupt shared state.

## 2. Multi-Competition Ingestion & Rebuild Chain
1. **Competition Registry (`config/competitions.yaml`):**
   - Premier League (`id=39`): PulseLive fixtures/streams/details + TheStatsAPI xG/odds + Transfermarkt market values.
   - National leagues (`provider: thestatsapi`, optional): TheStatsAPI (`match_id +100_000_000`, `team_id +10_000_000`) + openfootball schedule placeholders (`300_000_000+`) + optional Transfermarkt market values (`transfermarkt_code`).
   - UCL (`id=2`) & UEL (`id=3`): UEFA public API + TheStatsAPI payloads (data-only; no prediction models).
2. **Ordered Derived Rebuild (`src/pipeline/rebuild.py`):**
   - Shared single chain used by cron sync and weekly training: `process -> player_index -> features -> database`. Each runs in its own interpreter; any failure raises `RebuildError` and stops downstream steps.
   - Always pass atomic writes (`src/ingest/files.py:atomic_write_json`, `src/ingest/raw_store.py:write_json`).
3. **Schema & Competition Isolation:**
   - All shared SQLite tables (`matches`, `team_market_values`, `player_market_values`, etc.) scope multi-league rows by `competition_id`. Never overwrite another competition's player or team rows.
   - Keep external API secrets strictly in environment variables (`THESTATSAPI_API_KEY`, `API_FOOTBALL_KEY`, `PLM_ADMIN_TOKEN`), never in repo files.

## 3. Append-Only Pre-Game Paper Trading Ledger
1. **Strict Pre-Kickoff Locking:** `python3 -m src.analytics.prospective_1x2_benchmark snapshot` records one immutable prediction per fixture per day before kickoff into `data/competitions/<key>/processed/1x2_forecast_log.jsonl`.
2. **Provenance & Classification:** Record UTC timestamp, artifact SHA-256 fingerprint, forecast-time base rates, and `origin` (`prospective` vs `in_sample_backfill`) so `model_audit.py` and `prospective_1x2_benchmark.py score` keep live metrics uncontaminated.
3. **Scorecards:** Score outputs write strictly to `reports/prospective_1x2_scorecard.json` (PL) or `reports/prospective_1x2_scorecard_<key>.json` (optional national leagues). Follow decision thresholds in `docs/paper_trading_protocol_2026_27.md`.

## 4. Verification & Doc Sync
After modifying ingestion tools, schemas, or pipelines:
1. Update `src/ingest/__main__.py:TOOLS`, `docs/data_sources.md`, `docs/scripts_reference.md`, and `docs/artifact_registry.md`.
2. Ensure every CLI tool supports `--help` without side effects (`pytest tests/test_cli_help.py tests/test_docs.py -q`).
3. Run `./scripts/verify.sh` and `pytest -q`.
