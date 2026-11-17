# Competitions Module

Loads competition metadata and cold-start priors from YAML configuration (`config/competitions.yaml`, `config/priors.yaml`) and exposes competition-capability flags.

> [!NOTE]
> **Related Documentation & Runbooks:**
> - **Competition Config & Data Map:** [`config/competitions.yaml`](../../config/competitions.yaml) · [`docs/data_sources.md`](../../docs/data_sources.md)
> - **Key Entry Points:** [`registry.py`](registry.py) · [`normalizer.py`](normalizer.py)

## Business Rules & Invariants
- **Single Competition Registry:** `CompetitionRegistry` (`get_competition`, `list_competitions`, `get_priors`) maps both slug keys (`premier_league`, `champions_league`, `europa_league`) and numeric IDs (`39`, `2`, `3`) to immutable `CompetitionConfig` objects.
- **Dynamic Capability Flags:** `CompetitionConfig` computes `is_continental`, `is_domestic`, `sync_kinds` (PL exposes `matches`, `referees`, `lineups`; other competitions expose `matches`), `has_model`, `zones`, `schedule_source`, and `transfermarkt_code`.
- **Normalizer Status:** `CrossLeagueNormalizer` in [`normalizer.py`](normalizer.py) is experimental/unwired in active production prediction models.
- **Change rule:** Any new competition added to `config/competitions.yaml` must also be documented in [`docs/data_sources.md`](../../docs/data_sources.md) (`tests/test_docs.py` enforces parity).
