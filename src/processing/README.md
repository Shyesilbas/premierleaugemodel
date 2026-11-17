# Processing Module

Transforms cached raw provider JSON payloads into tabular season/combined Parquet datasets, recovered event counts, player registries, and competition SQLite match rows.

> [!NOTE]
> **Related Documentation & Runbooks:**
> - **Pipeline Order & Data Catalog:** [`src/pipeline/README.md`](../pipeline/README.md) · [`docs/data_and_ui_catalog.md`](../../docs/data_and_ui_catalog.md) · [`docs/artifact_registry.md`](../../docs/artifact_registry.md)
> - **Key Entry Points:** [`process_season_data.py`](process_season_data.py) · [`build_player_index.py`](build_player_index.py) · [`process_competition_data.py`](process_competition_data.py)

## Business Rules & Invariants
- **Missing vs Zero Semantics:** [`process_season_data.py`](process_season_data.py) distinguishes absent provider statistics (`NaN`) from genuine `0` values on sparse fields (`SPARSE_ZERO_METRICS`) and uses `_sum_if_complete` / `_threshold_if_known` so incomplete matches do not fabricate totals.
- **Event-Stream Recovery:** `_event_counts_by_team` recovers missing corners and saves from valid match textstreams while preserving recovery flags separately.
- **Player Registry & Match Logs:** [`build_player_index.py`](build_player_index.py) aggregates `*_details.json` into `players_registry.json` and `player_match_logs.json` under `PROCESSED_DIR`.
- **Competition Isolation:** [`process_competition_data.py`](process_competition_data.py) filters writes strictly by `competition_id` inside `sync_matches_to_sqlite`.
- **Change rule:** Invoke derived rebuilds via `python3 -m src.pipeline.rebuild` rather than ad-hoc out-of-order script calls.
