# API Module

FastAPI service layer exposing fixtures, standings, team/player/referee profiles, league statistics, live match predictions, model audit metrics, and token-protected admin sync endpoints.

> [!NOTE]
> **Related Documentation & Runbooks:**
> - **Contracts & Frontend Parity:** [`docs/model_api_integration.md`](../../docs/model_api_integration.md) · [`frontend/src/services/README.md`](../../frontend/src/services/README.md) · [`scripts/check_api_endpoints.py`](../../scripts/check_api_endpoints.py)
> - **Key Entry Points:** [`server.py`](server.py) · [`etag.py`](etag.py) · [`match_refresh.py`](match_refresh.py) · [`state.py`](state.py) · [`prediction_service.py`](prediction_service.py) · [`league_prediction.py`](league_prediction.py) · [`security.py`](security.py) · [`routes/predict.py`](routes/predict.py) · [`routes/meta.py`](routes/meta.py) · [`routes/fixtures.py`](routes/fixtures.py) · [`routes/matches.py`](routes/matches.py) · [`routes/teams.py`](routes/teams.py) · [`routes/players.py`](routes/players.py) · [`routes/stats.py`](routes/stats.py)

## Business Rules & Invariants
- **HTTP Transport (`server.py`, `etag.py`):** `GZipMiddleware` compresses responses `>= 1024` bytes; `ETagMiddleware` adds blake2b `ETag` + `Cache-Control: no-cache` on read-only `GET /api/*` routes (returning `304 Not Modified` on matching `If-None-Match`, excluding `/api/admin/*` and `/api/data-version`).
- **State Reload Discipline:** Other modules must access loaded datasets/models strictly via `state.<attr>` (never `from src.api.state import ...`) so middleware `_reload_if_data_changed` updates take effect seamlessly.
- **Fast Incremental Refresh (`match_refresh.py`):** Single-match and pending-batch refresh write PulseLive JSON and update SQLite + runtime caches immediately (~1 s), queueing derived Parquet/feature rebuilds asynchronously.
- **Unified Prediction Paths:** `compute_match_prediction` ([`prediction_service.py`](prediction_service.py)) serves Premier League (`outcome_models_v1`, 1X2-aligned `goals_models_v1`, 5 gated count models); `compute_league_prediction` ([`league_prediction.py`](league_prediction.py)) serves configured `thestatsapi` national leagues (`has_model: true`); continental cups return 404.
- **Security Controls:** `require_admin_token` guards `/api/admin/*` routes when `PLM_ADMIN_TOKEN` is set; `cors_origins` restricts browser origins to localhost dev defaults or `PLM_CORS_ORIGINS`.

## API
- `GET /` — API service health/status banner (`server.py`).
- `GET /api/data-version`, `GET /api/competitions`, `GET /api/fixtures/pending`, `POST|GET /api/admin/*` — Metadata, single/batch match refresh & admin controls (`routes/meta.py`).
- `GET /api/predict`, `GET /api/model-audit` (PL only), `GET /api/benchmarks` — ML predictions & evaluations (`routes/predict.py`).
- `GET /api/fixtures`, `/api/fixtures/grouped`, `/api/fixtures/bracket`, `/api/standings`, `/api/referees*`, `/api/match/{match_id}/recent-form` (`routes/fixtures.py`).
- `GET /api/match/{match_id}/details`, `/api/match/{match_id}/odds` (`routes/matches.py`).
- `GET /api/teams*`, `/api/players`, `/api/players/profile`, `/api/players/compare-data`, `/api/stats` (`routes/teams.py`, `routes/players.py`, `routes/stats.py`).
