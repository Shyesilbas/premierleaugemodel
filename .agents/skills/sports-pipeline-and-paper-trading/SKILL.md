---
name: sports-pipeline-and-paper-trading
description: >-
  Use this skill when running or modifying data ingestion pipelines, season bootstrapping,
  early-season prior transitions, roster/injury adjustments, SQLite frontend stores, or
  append-only pre-game paper trading / forecast ledgers.
---

# Sports Data Pipeline, Store & Paper Trading Workflow

Follow this workflow when operating or modifying the data ingestion pipeline, feature builders, early-season transitions, pre-game paper trading ledgers, or frontend SQLite stores.

## 1. Data Inspection & File Hygiene Rules

1. **Never Dump Raw Data into Context**:
   - Never read full `.csv`, `.parquet`, `.jsonl`, or `.db` files directly into context.
   - To inspect schemas or sample rows, use `head -n 5 <file>`, Python one-liners printing `.columns` and `.shape`, or `sqlite3 <db> "SELECT ... LIMIT 5;"`.
2. **Centralized Path Resolution**:
   - Never hardcode season directory strings. Always use the project's path resolver (`src.core.data_paths.get_data_paths(season)` or `src/config.py`) and accept `--season` in CLI scripts.
3. **No Silent Historical Fetching**:
   - Do not re-fetch historical completed seasons from external APIs unless explicitly requested by the user.

## 2. Daily / Weekly Ingestion & Frontend Store Pipeline

1. **Incremental Sync & Recovery**:
   - Ingest only missing or newly completed fixtures/boxscores for the active season.
   - Preserve raw source semantics alongside recovered/imputed fields (e.g., starter flags, event-stream stat recovery, observed trade affiliations).
   - Fail loudly if an upstream step fails so downstream snapshots or stores are never built from half-updated data (see `scripts/ops/morning.py` or `run_full_pipeline.py`).
2. **Roster, Injury & Availability Handling**:
   - Keep historical training rosters (`team_rosters.csv`, `core_players.csv`) separate from display-only live rosters (`team_rosters_live.csv`).
   - Map official injury/status reports to deterministic availability weights (e.g., `OUT = 0.0`, `DOUBTFUL = 0.25`, `QUESTIONABLE = 0.60`, `PROBABLE = 0.90`).
   - For unmentioned players in live inference, apply the carry-forward participation rule consistently across Win, Score, and Player projections.
3. **Frontend SQLite Store Packaging**:
   - Package processed data into the frontend SQLite store (`data/frontend_store/` or `data/premier_league.db`).
   - **Sealed Seasons**: Once a historical season is complete (`status = closed`), skip rebuilding it on daily runs unless the schema version (`STORE_VERSION`) changes or `--force` is passed.

## 3. Early-Season Hand-Over & Prior Transitions

When modifying early-season inference or feature generation (`first 3 to 6 games` of a season):
1. **Smooth Prior-to-Form Decay**:
   - Blend pre-season priors (carried Elo with roster-turnover adjustment, or previous season's shrunk team/player means) with current-season form over a fixed game window (e.g., 6 games for teams, 3 games for players), decaying prior weight linearly to `0`.
2. **Reliability Scaling**:
   - Scale player or team priors by prior-season sample reliability (e.g., $\min(1, \text{games\_played} / N)$ or shrinkage toward league/rookie baselines for zero-history players).
3. **Single Source of Truth for Blends**:
   - Ensure the exact same early-season blend function is called by the API, CLI matchup scripts, daily schedule predictor, and SHAP/explanation generators.

## 4. Append-Only Pre-Game Paper Trading Ledger

When maintaining or querying forward-testing ledgers (`data/predictions/paper_ledger_*.jsonl` or `data/processed/1x2_forecast_log.jsonl`):
1. **Strict Pre-Game Locking (First Write Wins)**:
   - Freeze one prediction record per regular-season/playoff match **before** tip-off / kickoff.
   - Once a game's prediction is written to the `.jsonl` ledger, never overwrite it on subsequent runs.
2. **Origin & Timestamp Auditing**:
   - Record the exact UTC timestamp, model version / SHA-256 artifact fingerprint, baseline probabilities, and active injury report snapshot.
   - Flag any record generated after tip-off or via historical backfill (`origin: "backfill"`) so live prospective metrics remain strictly uncontaminated.
   - If backfilling missed games, compute features strictly as-of the morning of that game date (`< game_date`).
3. **Scorecard Evaluation**:
   - Join outcomes from completed raw match logs at read/score time.
   - Report accuracy, Brier, Log-Loss, and MAE side-by-side against naive baselines (always-home, market/base rates, Elo).

## 5. Verification

After modifying pipeline, ingestion, store, or inference code:
1. Run structure and path audits if available (`PYTHONPATH=. python3 scripts/audit/validate_project_structure.py && PYTHONPATH=. python3 scripts/audit/validate_season_path_refactor.py`).
2. Run the unit and integration test suite (`PYTHONPATH=. python3 -m pytest tests -q`).
