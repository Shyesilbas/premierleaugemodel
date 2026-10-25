# Artifact Registry

This file describes the artifact ownership and refresh path. Snapshot counts and model scores live in the generated reports so they have one source of truth.

## Configuration artifacts

| Artifact | Purpose | Produced by |
|---|---|---|
| `config/competitions.yaml` | Turnuva kayıt defteri: desteklenen liglerin id, format, uefa katsayısı ve sağlayıcı tanımları | El ile sürdürülür |
| `config/priors.yaml` | Turnuva bazlı soğuk başlangıç istatistik priörleri (sıfır sızıntı garantisi) | El ile sürdürülür |

## Data artifacts

| Artifact | Purpose | Produced by |
|---|---|---|
| `data/raw/{competition}/fixtures_{season}.json` | Çoklu lig fikstür takvimi | Çoklu lig senkronizasyonu |
| `data/raw/{competition}/matches/*_stream.json` | Çoklu lig play-by-play olay akışı | `src/processing/process_competition_data.py` |
| `data/processed/{competition}/matches_summary_{season}.parquet` | Turnuva bazlı ayrıştırılmış maç özetleri | `src/processing/process_competition_data.py` |
| `data/processed/{competition}/shots_events_{season}.parquet` | Turnuva bazlı şut ve olay koordinatları | `src/processing/process_competition_data.py` |
| `data/raw/fixtures_{season}.json` | Cached season fixture lists | Incremental season sync |
| `data/raw/matches/*_stats.json` | Raw team match statistics | Incremental season sync |
| `data/raw/matches/*_stream.json` | Match event streams | Incremental season sync |
| `data/raw/matches/*_details.json` | Match officials and detail fields | Incremental season sync |
| `data/processed/matches_summary_all.parquet` | Combined fixtures and parsed match statistics | `src/processing/process_season_data.py` |
| `data/processed/shots_events_all.parquet` | Combined parsed event records | `src/processing/process_season_data.py` |
| `data/processed/features_matches_all.parquet` | Pre-match rolling, form, and team strength features | `src/features/build_features.py` |
| `data/processed/players_registry.json` | Player identity and latest known team index | `src/processing/build_player_index.py` |
| `data/processed/player_match_logs.json` | Parsed player match logs across cached seasons | `src/processing/build_player_index.py` |
| `data/processed/team_staff.json` | Team staff records for a selected competition season | `src/ingest/fetch_team_staff.py` |
| `data/processed/1x2_forecast_log.jsonl` | Append-only pre-kickoff 1X2 and goal-market forecasts; records the outcome and goal-model SHA-256 fingerprints, market source, and ex-ante baseline probabilities | `python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14` |
| `data/premier_league.db` | SQLite database used by the application | Incremental season sync |

## Production model artifacts

| Artifact | Targets | Training source |
|---|---|---|
| `models/production/outcome_models_v1.joblib` | 1X2 result (logistic classifier, temperature calibrator, and gated ensemble metadata) | `src/models/train_match_outcome.py` |
| `models/production/goals_models_v1.joblib` | `blend_dc_feat` score matrix, Over 1.5/2.5/3.5 and BTTS probabilities, expected team goals, calibrators, model-vs-baseline gates, and unlocked-season baseline rates (including BTTS) | `python3 -m src.models.evaluate_goal_models` followed by `python3 -m src.models.train_goals` |
| `models/production/corner_model_v1.joblib` | Total corners | `src/models/train_corners.py` |
| `models/production/throws_model_v1.joblib` | Total throw-ins | `src/models/train_throws.py` |
| `models/production/saves_model_v1.joblib` | Total saves | `src/models/train_saves.py` |
| `models/production/cards_model_v1.joblib` | Total cards | `src/models/train_cards.py` |
| `models/production/offside_model_v1.joblib` | Total offsides | `src/models/train_offsides.py` |

The API loads these files from `models/production/`. Each artifact contains the fitted estimator and its required feature names. Count-model artifacts also store their fitted conditional dispersion parameter; the outcome artifact stores its probability calibrators. The goal-matrix artifact is fit on completed matches in `features_matches_all.parquet` (currently 1,595 rows across 2022/23–2026/27), while its nested calibration and baseline rates use 1,520 unlocked matches and exclude the locked 2026/27 season. Its outer-season evaluation is saved in `data/processed/goal_model_outer_eval.json`; the selected O2.5 score-matrix candidate cleared the evaluation gate. Count-model artifacts record both deployment gates in `metrics["skill_gate"]` (CV gate plus the development-only nested outer-season gate, `outer_season_wins` / `outer_season_count`); when either fails, `model` is a fitted `training_mean` pipeline and the API reports `model_skill: "baseline"`. Run `python3 run_full_pipeline.py` after updating the local raw cache to rebuild processed data, retrain the models, and refresh the benchmark and data reports.

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
- `docs/reports/prospective_1x2_scorecard.json` is generated by `python3 -m src.analytics.prospective_1x2_benchmark score` after logged forecasts have completed; it contains separate 1X2 and goal-market score groups, including log-loss/Brier comparisons with the forecast-time base rates.
