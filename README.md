# Premier League Match Analysis

This project stores Premier League fixtures and match statistics, builds pre-match team features, trains prediction models, and serves a React dashboard through FastAPI.

## Current data

The local cache contains four seasons: 2023/24, 2024/25, 2025/26, and the in-progress 2026/27 season. Counts change as fixtures finish; see [Data Quality](reports/data_quality.md) for the current snapshot and raw-provider field coverage.

## Run locally

Start the API from the repository root:

```bash
uvicorn src.api.server:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

## Refresh data and models

The Fixtures page can run the incremental season sync. It refreshes the provider fixture list and downloads data for changed or newly completed matches, then rebuilds the processed tables and SQLite database. That action does not retrain prediction models. Restart the API to load rebuilt data.

To rebuild features, retrain every model, and refresh the reports from the local cache, run:

```bash
python3 run_full_pipeline.py
```

The full pipeline does not fetch new upstream data. Run the incremental sync first when the cache needs updating.

## Model and data reports

- [Model Benchmarks](reports/model_benchmarks.md): one chronological benchmark report for all prediction targets.
- [Data Quality](reports/data_quality.md): fixture counts, referee/raw-stat coverage, target distributions, and missing-label patterns by season, team, and match outcome.
- [Team Tactical Data Audit](reports/team_tactical_data_audit.md): detailed coverage for team-level tactical fields.
- [Team Scenario Validation](reports/team_scenario_validation.md): compares event-stream shot and corner counts with match statistics.
- [Artifact Registry](ARTIFACT_REGISTRY.md): current processed datasets and model artifacts.
- [Project Status](PROJECT_STATUS.md): current snapshot and known model limitations.

## Evaluation and interpretation

All model rows are ordered by kickoff. Candidate selection uses expanding-window folds; the final 20% is held out and scored once. Results also include season-by-season holdouts where each test season is evaluated using only earlier seasons. Probability calibration is fitted from chronological out-of-fold development predictions. Regression imputation and scaling are fitted within each training fold. Production models are refit on all eligible rows only after evaluation. The 1X2 report includes a Dixon–Coles team attack/defence baseline on the same temporal holdouts; it is currently an evaluation comparator, not the API's production outcome model.

The data covers only a few seasons, and the latest season is incomplete. Treat small improvements over a mean or class-prior baseline as preliminary. Count thresholds use a negative-binomial distribution with dispersion estimated on training targets; reports compare it with Poisson and training-rate baselines. Raw metric omissions are kept as nulls with per-team `_reported` flags; models exclude rows whose target metrics are incomplete. The repository does not contain a trained xG model: its historical `xg` fields are a hand-built proxy from aggregate shot statistics and big chances, generated only when its inputs are present.
