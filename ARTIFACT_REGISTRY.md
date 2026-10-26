# Artifact Registry

This file describes the artifact ownership and refresh path. Snapshot counts and model scores live in the generated reports so they have one source of truth.

Which source feeds which competition (provider, script, raw files, tables): [docs/data_sources.md](docs/data_sources.md).

## Directory layout

Data and models are separated per competition (key in `config/competitions.yaml`, paths from `src.config.competition_paths`):

```
data/football.db                          shared SQLite (parsed rows), every match row has competition_id (39 PL, 2 UCL, 3 UEL)
data/competitions/<key>/raw/              provider downloads. PL: fixtures_<season>.json, matches/<id>_*.json.
                                          UCL/UEL: <provider>/fixtures_<season>.json, standings_<season>.json, matches/<id>_<kind>.json, competition/<season>_<kind>.json
data/competitions/<key>/processed/        parquet tables, features, evaluation JSON, forecast log
models/production/<key>/                  trained .joblib artifacts of that competition
models/backup/<key>/                      previous artifact versions
```

Only `premier_league` has processed tables and production models. Champions League and Europa League are data-only: parsed rows and payloads are in the shared database and the raw provider responses are archived as files under their own folders (written by `src/ingest/raw_store.py`).

## Configuration artifacts

| Artifact | Purpose | Produced by |
|---|---|---|
| `config/competitions.yaml` | Turnuva kayıt defteri: desteklenen liglerin id, format, uefa katsayısı ve sağlayıcı tanımları | El ile sürdürülür |
| `config/priors.yaml` | Turnuva bazlı soğuk başlangıç istatistik priörleri (sıfır sızıntı garantisi) | El ile sürdürülür |

## Data artifacts

| Artifact | Purpose | Produced by |
|---|---|---|
| `data/competitions/premier_league/raw/fixtures_{season}.json` | Cached season fixture lists | Incremental season sync |
| `data/competitions/premier_league/raw/matches/*_stats.json` | Raw team match statistics | Incremental season sync |
| `data/competitions/premier_league/raw/matches/*_stream.json` | Match event streams | Incremental season sync |
| `data/competitions/premier_league/raw/matches/*_details.json` | Match officials and detail fields | Incremental season sync |
| `data/competitions/premier_league/processed/matches_summary_all.parquet` | Combined fixtures and parsed match statistics | `src/processing/process_season_data.py` |
| `data/competitions/premier_league/processed/shots_events_all.parquet` | Combined parsed event records | `src/processing/process_season_data.py` |
| `data/competitions/premier_league/processed/features_matches_all.parquet` | Pre-match rolling, form, and team strength features | `src/features/build_features.py` |
| `data/competitions/premier_league/processed/players_registry.json` | Player identity and latest known team index | `src/processing/build_player_index.py` |
| `data/competitions/premier_league/processed/player_match_logs.json` | Parsed player match logs across cached seasons | `src/processing/build_player_index.py` |
| `data/competitions/premier_league/processed/team_staff.json` | Team staff records for a selected competition season | `src/ingest/fetch_team_staff.py` |
| `data/competitions/la_liga/processed/1x2_forecast_log.jsonl` | Append-only pre-kickoff LaLiga 1X2 and goal-market forecasts (same record format as the Premier League log; 21 forecasts saved on 2026-10-26) | `python3 -m src.analytics.prospective_1x2_benchmark snapshot --competition la_liga` |
| `data/competitions/premier_league/processed/1x2_forecast_log.jsonl` | Append-only pre-kickoff 1X2 and goal-market forecasts; records the outcome and goal-model SHA-256 fingerprints, market source, and ex-ante baseline probabilities | `python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14` |
| `data/football.db` | SQLite database used by the application; Premier League plus Champions League and Europa League matches (`competition_id`), `external_match_payloads` and `external_competition_payloads` (TheStatsAPI statistics, lineups, player stats, timeline, shot map, odds, squads, standings, managers) | Incremental season sync, `src/ingest/sync_competition_data.py` (UEFA fixtures, results, standings), `src/ingest/sync_thestatsapi_competition.py` (TheStatsAPI details; no odds before 2024/25) |

## Production model artifacts

| Artifact | Targets | Training source |
|---|---|---|
| `models/production/premier_league/outcome_models_v1.joblib` | 1X2 result (logistic classifier, temperature calibrator, and gated ensemble metadata) | `src/models/train_match_outcome.py` |
| `models/production/premier_league/goals_models_v1.joblib` | `blend_dc_feat` score matrix, Over 1.5/2.5/3.5 and BTTS probabilities, expected team goals, calibrators, model-vs-baseline gates, and unlocked-season baseline rates (including BTTS) | `python3 -m src.models.evaluate_goal_models` followed by `python3 -m src.models.train_goals` |
| `models/production/premier_league/corner_model_v1.joblib` | Total corners | `src/models/train_corners.py` |
| `models/production/premier_league/throws_model_v1.joblib` | Total throw-ins | `src/models/train_throws.py` |
| `models/production/premier_league/saves_model_v1.joblib` | Total saves | `src/models/train_saves.py` |
| `models/production/premier_league/cards_model_v1.joblib` | Total cards | `src/models/train_cards.py` |
| `models/production/premier_league/offside_model_v1.joblib` | Total offsides | `src/models/train_offsides.py` |

The API loads these files from `models/production/premier_league/`. Each artifact contains the fitted estimator and its required feature names. Count-model artifacts also store their fitted conditional dispersion parameter; the outcome artifact stores its probability calibrators. The goal-matrix artifact is fit on completed matches in `features_matches_all.parquet` (currently 1,595 rows across 2022/23–2026/27), while its nested calibration and baseline rates use 1,520 unlocked matches and exclude the locked 2026/27 season. Its outer-season evaluation is saved in `data/competitions/premier_league/processed/goal_model_outer_eval.json`; the selected O2.5 score-matrix candidate cleared the evaluation gate. Count-model artifacts record both deployment gates in `metrics["skill_gate"]` (CV gate plus the development-only nested outer-season gate, `outer_season_wins` / `outer_season_count`); when either fails, `model` is a fitted `training_mean` pipeline and the API reports `model_skill: "baseline"`. Run `python3 run_full_pipeline.py` after updating the local raw cache to rebuild processed data, retrain the models, and refresh the benchmark and data reports.

## LaLiga model artifacts

| Artifact | Purpose | Produced by |
|---|---|---|
| `models/production/la_liga/{corner,throws,offside,cards,saves}_model_v1.joblib` | LaLiga count models (same gated selection as the Premier League; throws and offsides passed the gate, the rest serve `training_mean`; features are the Premier League's own code, see `src/features/build_league_pl_features.py`) | `python3 -m src.models.train_league_counts --competition la_liga` |
| `docs/reports/models/la_liga_ablation_low_c_core_core_low_c.json` | LaLiga stronger-penalty and 22-feature ablation (both No Gain, Not Adopted; the CV curve over C is U-shaped with the minimum at 0.001) | `python3 -m src.models.ablate_league_features --competition la_liga --group low_c core core_low_c` |
| `docs/reports/models/la_liga_xi_ablation.json` | LaLiga first-XI feature ablation (No Gain, Not Adopted; production 1X2 set stays at 118 features) | `python3 -m src.models.ablate_league_features --competition la_liga --group xi` |
| `models/production/la_liga/goals_models_v1.joblib` | LaLiga goal model (the Premier League goal model on Premier League feature definitions) with the per-market skill gate and training base rates | `python3 -m src.models.train_league_goals --competition la_liga` |
| `docs/reports/models/la_liga_goal_model_eval.json`, `docs/reports/models/la_liga_goals.md` | Outer-season evaluation of the LaLiga goal-market candidates and the report | `python3 -m src.models.evaluate_league_goal_models --competition la_liga` |
| `docs/reports/models/la_liga_feature_audit.json`, `docs/reports/models/la_liga_feature_audit.md` | Permutation importance by feature family for the LaLiga 1X2 model (per outer season) and the throws and offsides models (holdout) | `python3 -m src.analytics.league_feature_audit --competition la_liga` |
| `docs/reports/models/la_liga_pl_parity_ablation.json` | LaLiga 1X2 with the Premier League's feature definitions (No Gain, Not Adopted: significantly worse on 2024/25, equal later) | `python3 -m src.models.ablate_league_features --competition la_liga --group pl_parity` |
| `docs/reports/models/la_liga_count_models_league_features.json` | First version of the LaLiga count models (own feature set); kept for the comparison with the Premier League definitions | `python3 -m src.models.train_league_counts --competition la_liga --features league` |
| `docs/reports/models/la_liga_count_models.json`, `docs/reports/models/la_liga_counts.md` | Raw metrics and the report of the LaLiga count models | same command |
| `models/production/la_liga/outcome_models_v1.joblib` | LaLiga 1X2 model, calibrator, Elo baseline, Poisson goal models and the gate decision | `python3 -m src.models.train_league_model --competition la_liga` |
| `docs/reports/models/la_liga_walk_forward.json` | Walk-forward results (single source of the numbers in `la_liga_outcome.md`) | same |
| `docs/reports/models/la_liga_outcome.md` | Model report | written from the JSON |
| `data/competitions/la_liga/processed/walk_forward_predictions.parquet` | Out-of-sample predictions that feed the audit page (git-ignored) | same |

## Experiment reports

| Artifact | Purpose | Produced by |
|---|---|---|
| `docs/reports/experiments/2026-10-25_box_features_ablation.json` | Outer-season ablation of the provider-specific penalty-area features in the 1X2 model | `research/box_features_ablation.py` |
| `docs/reports/experiments/2026-10-25_new_league_readiness.md` | Summary of that ablation and of the LaLiga sample pull | written from the JSON above |
| `data/competitions/la_liga/raw/openfootball/fixtures_<season>.json` | Full-season LaLiga calendar (public domain), used for the weeks the provider has not published | `src/ingest/fetch_openfootball_schedule.py` |
| `data/competitions/la_liga/raw/thestatsapi/` | LaLiga raw TheStatsAPI responses: fixture lists, per-match files (match, stats, lineups, player stats, timeline; odds from 2024/25; shot maps are not fetched), squads and team stats; match files git-ignored | `src/ingest/fetch_thestatsapi_league.py` (loaded by `src/ingest/load_thestatsapi_league.py`; refreshed by the update button through `src/ingest/sync_competition.py`) |

## Canonical reports

All reports live in `docs/reports/`; no code writes to a top-level `reports/` folder.

- [Reports index](docs/reports/README.md) is the entry point for all human-readable reports and evaluation artifacts.
- [Model reports](docs/reports/models/) own each production model's architecture, results, audit findings, rejected experiments, and change history (hand-maintained).
- [Repository Audit](docs/reports/repository_audit.md) contains the current codebase review and prioritized improvement plan.
- [Model Benchmarks](docs/reports/model_benchmarks.md) owns current evaluation scores and protocol.
- [Data Quality and Coverage](docs/reports/data_quality.md) owns fixture counts, source coverage, referee coverage, and target distributions.
- [Team Tactical Data Audit](docs/reports/team_tactical_data_audit.md) owns detailed team-stat coverage by season.
- [Team Scenario Validation](docs/reports/team_scenario_validation.md) owns event-stream validation against raw match statistics.
- [Project Status](PROJECT_STATUS.md) summarizes current findings and remaining model limitations.
- `docs/reports/prospective_1x2_scorecard_la_liga.json` is the LaLiga scorecard (`score --competition la_liga`); it is empty until a logged match completes.
- `docs/reports/prospective_1x2_scorecard.json` is generated by `python3 -m src.analytics.prospective_1x2_benchmark score` after logged forecasts have completed; it contains separate 1X2 and goal-market score groups, including log-loss/Brier comparisons with the forecast-time base rates.
