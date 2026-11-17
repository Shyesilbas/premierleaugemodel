# Pipeline Module

Provides the single ordered subprocess chain (`process -> player_index -> features -> database`) for rebuilding derived Parquet files, player indexes, features, and SQLite tables.

> [!NOTE]
> **Related Documentation & Runbooks:**
> - **Usage & Scripts Reference:** [`docs/scripts_reference.md`](../../docs/scripts_reference.md) · [`run_full_pipeline.py`](../../run_full_pipeline.py)
> - **Key Entry Point:** [`rebuild.py`](rebuild.py)

## Business Rules & Invariants
- **Ordered Subprocess Execution:** `rebuild_derived_data` executes `STEPS` (`process`, `player_index`, `features`, `database`) sequentially in isolated Python subprocesses so `PLM_DATA_DIR` propagates cleanly without `sys.argv` or memory leakage.
- **Fail-Fast Guarantee:** Any non-zero exit code raises `RebuildError` immediately and aborts downstream steps so SQLite and feature Parquet never end up half-updated.
- **Shared Entry Point:** Both cron sync (`sync_season_data.py`) and full training (`run_full_pipeline.py`) invoke `rebuild_derived_data`.
- **Change rule:** Keep `STEPS` ordering synchronized with upstream/downstream file dependencies (`attach_statsapi_xg` inside `features` reads `DB_PATH`, while `database` reads processed Parquet outputs).
