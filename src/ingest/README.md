# Ingest Module

Fetches raw fixtures, match statistics, event streams, official lineups, xG, betting odds, club badges, and Transfermarkt valuations across supported competitions using atomic writes and per-competition locks.

> [!NOTE]
> **Related Documentation & Runbooks:**
> - **Source Map & CLI Catalog:** [`docs/data_sources.md`](../../docs/data_sources.md) · [`docs/scripts_reference.md`](../../docs/scripts_reference.md)
> - **Key Entry Points:** [`__main__.py`](__main__.py) · [`sync_season_data.py`](sync_season_data.py) · [`sync_prematch_lineups.py`](sync_prematch_lineups.py) · [`sync_competition.py`](sync_competition.py) · [`raw_store.py`](raw_store.py) · [`files.py`](files.py) · [`provider_factory.py`](provider_factory.py)

## Business Rules & Invariants
- **CLI Registry Parity:** Every runnable tool under `src/ingest/` must support `--help` cleanly and appear in `TOOLS` inside [`__main__.py`](__main__.py) and [`docs/data_sources.md`](../../docs/data_sources.md) (verified by `tests/test_docs.py` and `tests/test_cli_help.py`).
- **Atomic File Writes & Locks:** Use `atomic_write_json` ([`files.py`](files.py)) or `write_json` ([`raw_store.py`](raw_store.py)) and guard competition syncs with `competition_lock` (`CompetitionSyncRunning`).
- **Provider Separation & ID Offsets:** PulseLive serves Premier League (`fetch_season_data.py`), UEFA + TheStatsAPI serve UCL/UEL (`sync_competition_data.py`, `sync_thestatsapi_competition.py`), and TheStatsAPI + openfootball support optional national leagues (`fetch_thestatsapi_league.py`, `load_thestatsapi_league.py`, `fetch_openfootball_schedule.py`).
- **Secrets via Environment Only:** `THESTATSAPI_API_KEY` and `API_FOOTBALL_KEY` are read strictly from environment variables.
- **Change rule:** When adding or retiring a script, update `TOOLS` in [`__main__.py`](__main__.py), [`docs/data_sources.md`](../../docs/data_sources.md), and [`docs/scripts_reference.md`](../../docs/scripts_reference.md).
