# Database Module (`src/db/`)

Manages the shared SQLite store (`data/football.db`), schema initialization, multi-competition market/xG/odds tables, and query helpers for fixtures and referees.

> [!NOTE]
> **Related Documentation & Runbooks:**
> - **Artifact & Source Ownership:** [`docs/artifact_registry.md`](../../docs/artifact_registry.md) · [`docs/data_sources.md`](../../docs/data_sources.md) · [`docs/data_and_ui_catalog.md`](../../docs/data_and_ui_catalog.md)
> - **Key Entry Point:** [`database.py`](database.py)

## Business Rules & Invariants
- **Shared Multi-Competition Store:** One SQLite database (`DB_PATH`) stores PL (`competition_id = 39`), UCL (`2`), and UEL (`3`); queries must always scope by `competition_id` so cross-league rows never collide.
- **Idempotent Table Provisioning:** `init_db`, `ensure_external_xg_table`, `ensure_external_odds_table`, `ensure_external_payload_tables`, and `ensure_market_value_tables` preserve existing external xG, odds, and payload rows across `populate_db_from_sources` rebuilds (`tests/test_database.py`).
- **Concurrency Timeout:** `get_db` connects with `timeout=120` and `sqlite3.Row` row factory so background sync jobs do not immediately hit lock contention.
- **No Raw DB Inspection in Context:** Inspect schema or rows via `sqlite3 data/football.db ".schema"` or `SELECT ... LIMIT 5;`.
- **Change rule:** Preserve backward-compatible `competition_id` migration logic for pre-existing local SQLite databases.
