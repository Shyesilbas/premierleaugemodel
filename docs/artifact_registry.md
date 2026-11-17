# Artifact Registry

This file describes the artifact ownership and refresh path. Snapshot counts and model scores live in the generated reports so they have one source of truth.

Which source feeds which competition (provider, script, raw files, tables): [docs/data_sources.md](data_sources.md).

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

The API loads these files from `models/production/premier_league/`. Each artifact contains the fitted estimator and its required feature names. Count-model artifacts also store their fitted conditional dispersion parameter; the outcome artifact stores its probability calibrators. The goal-matrix artifact is fit on completed matches in `features_matches_all.parquet` (currently 1,608 rows across 2022/23–2026/27), while its nested calibration and baseline rates use 1,520 unlocked matches and exclude the locked 2026/27 season. Its outer-season evaluation is saved in `data/competitions/premier_league/processed/goal_model_outer_eval.json`; the selected O2.5 score-matrix candidate cleared the evaluation gate. Count-model artifacts record both deployment gates in `metrics["skill_gate"]` (CV gate plus the development-only nested outer-season gate, `outer_season_wins` / `outer_season_count`); when either fails, `model` is a fitted `training_mean` pipeline and the API reports `model_skill: "baseline"`. Run `python3 run_full_pipeline.py` after updating the local raw cache to rebuild processed data, retrain the models, and refresh the benchmark and data reports.

## Experiment reports

| Artifact | Purpose | Produced by |
|---|---|---|
| `reports/experiments/2026-10-25_box_features_ablation.json` | Outer-season ablation of the provider-specific penalty-area features in the 1X2 model | `research/box_features_ablation.py` |
| `reports/experiments/2026-10-25_new_league_readiness.md` | Summary of that ablation for national-league readiness | written from the JSON above |

## Canonical reports

Generated outputs and dated audits live in `reports/`; hand-maintained model architecture reports live in `docs/reports/models/`.

- [Reports index](../reports/README.md) is the entry point for all generated reports and frozen audits.
- [Model reports](reports/models/) own each production model's architecture, results, audit findings, rejected experiments, and change history (hand-maintained).
- [Repository Audit](../reports/audits/repository_audit.md) contains the current codebase review and prioritized improvement plan.
- [Model Benchmarks](../reports/model_benchmarks.md) owns current evaluation scores and protocol.
- [Data Quality and Coverage](../reports/data_quality.md) owns fixture counts, source coverage, referee coverage, and target distributions.
- [Team Tactical Data Audit](../reports/team_tactical_data_audit.md) owns detailed team-stat coverage by season.
- [Team Scenario Validation](../reports/team_scenario_validation.md) owns event-stream validation against raw match statistics.
- [Project Status](project_status.md) summarizes current findings and remaining model limitations.
- `reports/prospective_1x2_scorecard.json` is generated by `python3 -m src.analytics.prospective_1x2_benchmark score` after logged forecasts have completed; it contains separate 1X2 and goal-market score groups, including log-loss/Brier comparisons with the forecast-time base rates.
