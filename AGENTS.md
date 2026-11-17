# premierLeaugeModelApp — Unified Agent Guide

Multi-league football platform (`premier_league` models + `champions_league` & `europa_league` data-only, plus reusable national-league pipeline tooling): Python 3.12 analytical ETL/modeling/FastAPI service (`src/`) and React 19 / Vite / Tailwind frontend (`frontend/`). Single source of truth for all AI agents (`CLAUDE.md`, `GEMINI.md`, `CODEX.md`, `.cursorrules`, `.windsurfrules`, `.clinerules` point here).

## Commands
- **Start dev stack:** `python3 start.py` or `./start.sh` (FastAPI `127.0.0.1:8000`, Vite `localhost:5173`).
- **Full rebuild & train (PL):** `python3 run_full_pipeline.py` (offline stages: `rebuild`, `audits`, `counts`, `outcome`, `goals`) | Derived rebuild only: `python3 -m src.pipeline.rebuild`.
- **Generic national-league training:** `python3 -m src.models.train_league_model --competition <key>` | `python3 -m src.models.train_league_counts --competition <key>` | `python3 -m src.models.train_league_goals --competition <key>`.
- **Paper trading:** `python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14` | `python3 -m src.analytics.prospective_1x2_benchmark score`.
- **Tests & lint:** `pytest -q` | `ruff check .` | `cd frontend && npm run dev | lint:design | lint | build`.
- **Verify:** `./scripts/verify.sh` = `check_no_emoji.py` + `check_docs.py` + `check_api_endpoints.py` + core doc/config/CLI pytest checks + frontend `lint:design`, `lint` & `build`.

## Skills (`.agents/skills/`, symlinked as `.claude/skills`)
Load the matching skill before modifying code.

| Touching | Skill |
|---|---|
| Model experiments, feature ablations, calibration, skill gates, promotions | `quant-model-experiment-and-audit` |
| Data ingestion, SQLite `football.db`, competition stores, paper trading ledger | `sports-pipeline-and-paper-trading` |
| Any doc, README, report, skill or `AGENTS.md` edit | `docs-drift-audit` |
| Backend routes, services, SQLite/Parquet logic, security or finding IDs | `backend-review-audit` |
| Frontend UI component, view, modal, table, chart or stylesheet | `restrained-ui-design-standard` |
| Frontend modules, React Context, services, caching or routing | `frontend-modular-architecture` |

## Active Production Models
- **Premier League (`models/production/premier_league/`):**
  - `goals_models_v1.joblib`: Independent Poisson + Dixon-Coles `13x13` score matrix (60 features, `alpha=3.0`, `dc_weight=0.0`), rescaled to 1X2 probabilities; calibrated O1.5/O2.5/O3.5 & BTTS probabilities (`btts_prediction=null` while `btts_gate` is closed).
  - `outcome_models_v1.joblib`: 74-feature multinomial Logistic Regression (`C=0.003`) + OOF softmax temperature/bias calibrator.
  - Count models (`corner`, `throws`, `offside`, `cards`, `saves`): gated via CV + nested outer-season gate (`throws` & `offsides` active; `corner`, `cards`, `saves` serve `training_mean` with `model_skill="baseline"`).
- **UCL / UEL:** Data-only (`competition_id` 2, 3); `/api/predict` returns 404 and `/api/model-audit` serves Premier League only (`hasAudit: true`).

## Invariants
- **Zero emoji** in code, comments, docstrings, UI text, reports, and git commits. Use `lucide-react` icons.
- **Pre-game leakage boundary (`shift(1)`):** All rolling windows, EWMA, Elo, and referee aggregates strictly use prior matches (`< kickoff`); maintain train-serve parity across offline builders (`src/features/`) and live inference (`src/api/`).
- **Locked season `2026_27`:** Strictly for prospective paper-trading evaluation; never use it for feature selection, tuning, or skill-gate decisions.
- **Production safety:** Never overwrite `models/production/*` during experiments; isolate runs with `PLM_DATA_DIR`, `PLM_MODELS_DIR`, `PLM_MODELS_ROOT`, and `PLM_REPORTS_DIR`.
- **One home per fact:** Module rules live in `src/<module>/README.md` and `frontend/src/<module>/README.md`; cross-module guides and registries live in `docs/`; generated outputs and frozen audits live in `reports/`.
- **Never read raw files directly:** Never read `.parquet`, `.db`, `.joblib`, raw `matches/*.json`, `node_modules/`, `frontend/dist/`, `.venv/`, `.pytest_cache/`, `__pycache__/`, or `.git/`. Inspect SQLite with `sqlite3 data/football.db "SELECT ... LIMIT 5;"`.

## Project Map & Risk Tiers
| Group | Modules | Risk |
|---|---|---|
| Modeling & Feature Integrity | `src/features`, `src/models`, `src/analytics` | High |
| Data, Sync & Storage | `src/ingest`, `src/processing`, `src/pipeline`, `src/db`, `src/competitions` | High |
| Serving & UI | `src/api`, `src/config.py`, `frontend/src/*` | Medium |

## Where to Look
1. **Module hub first:** `src/<module>/README.md` (frontend: `frontend/src/<module>/README.md` and `frontend/README.md`).
2. **Cross-module docs, registries & model specs:** `docs/README.md` (`docs/artifact_registry.md`, `docs/project_status.md`, `docs/data_sources.md`, `docs/reports/models/*.md`).
3. **Generated benchmarks & frozen audits:** `reports/README.md`.
