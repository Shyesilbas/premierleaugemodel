# Artifact Registry

This file describes the artifact ownership and refresh path. Snapshot counts and model scores live in the generated reports so they have one source of truth.

## Data artifacts

| Artifact | Purpose | Produced by |
|---|---|---|
| `data/raw/fixtures_{season}.json` | Cached season fixture lists | Incremental season sync |
| `data/raw/matches/*_stats.json` | Raw team match statistics | Incremental season sync |
| `data/raw/matches/*_stream.json` | Match event streams | Incremental season sync |
| `data/raw/matches/*_details.json` | Match officials and detail fields | Incremental season sync |
| `data/processed/matches_summary_all.parquet` | Combined fixtures and parsed match statistics | `src/processing/process_season_data.py` |
| `data/processed/shots_events_all.parquet` | Combined parsed event records | `src/processing/process_season_data.py` |
| `data/processed/features_matches_all.parquet` | Pre-match rolling, form, and team strength features | `src/features/build_features.py` |
| `data/premier_league.db` | SQLite database used by the application | Incremental season sync |

## Production model artifacts

| Artifact | Targets | Training source |
|---|---|---|
| `models/production/outcome_models_v1.joblib` | 1X2 result and over 2.5 goals | `src/models/train_match_outcome.py` |
| `models/production/corner_model_v1.joblib` | Total corners | `src/models/train_corners.py` |
| `models/production/throws_model_v1.joblib` | Total throw-ins | `src/models/train_throws.py` |
| `models/production/saves_model_v1.joblib` | Total saves | `src/models/train_saves.py` |
| `models/production/cards_model_v1.joblib` | Total cards | `src/models/train_cards.py` |
| `models/production/offside_model_v1.joblib` | Total offsides | `src/models/train_offsides.py` |

The API loads these files from `models/production/`. Each artifact contains the fitted estimator and its required feature names. Count-model artifacts also store their fitted dispersion parameter; the outcome artifact stores its probability calibrators. Run `python3 run_full_pipeline.py` after updating the local raw cache to rebuild processed data, retrain the models, and refresh the benchmark and data reports. That command does not fetch upstream data or rebuild SQLite.

## Canonical reports

- [Model Benchmarks](reports/model_benchmarks.md) owns current evaluation scores and protocol.
- [Data Quality and Coverage](reports/data_quality.md) owns fixture counts, source coverage, referee coverage, and target distributions.
- [Team Tactical Data Audit](reports/team_tactical_data_audit.md) owns detailed team-stat coverage by season.
- [Team Scenario Validation](reports/team_scenario_validation.md) owns event-stream validation against raw match statistics.
- [Project Status](PROJECT_STATUS.md) summarizes current findings and remaining model limitations.
