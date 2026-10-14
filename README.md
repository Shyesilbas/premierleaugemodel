# Premier League Match Analysis

This project stores Premier League fixtures and match statistics, builds pre-match team features, trains prediction models, and serves a React dashboard through FastAPI.

## Current data

The local cache contains five seasons: 2022/23 through the in-progress 2026/27 season. Counts change as fixtures finish; see [Data Quality](reports/data_quality.md) for the current snapshot, recovered event labels, and raw-provider field coverage.

## Run locally

Start the API from the repository root:

```bash
uvicorn src.api.server:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite 8 requires Node.js `^20.19.0` or `>=22.12.0`. Use one of those versions for the frontend commands.

## Refresh data and models

The Fixtures page can run the incremental season sync. It refreshes the provider fixture list and downloads data for changed or newly completed matches, then rebuilds the processed tables and SQLite database. That action does not retrain prediction models. Restart the API to load rebuilt data.

To rebuild features, retrain every model, and refresh the reports from the local cache, run:

```bash
python3 run_full_pipeline.py
```

The full pipeline does not fetch new upstream data. Run the incremental sync first when the cache needs updating.

## Goal and 1X2 evaluation

The score-matrix model is implemented in `src/models/goals_model.py`, trained in `src/models/train_goals.py`, and evaluated against season holdouts by `src/models/evaluate_goal_models.py`. The 1X2 draw-propensity state is in `src/features/draw_features.py`; shared bootstrap and reliability metrics are in `src/models/eval_utils.py`.

To save the API's upcoming production forecasts and later score completed matches, run:

```bash
python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14
python3 -m src.analytics.prospective_1x2_benchmark score
```

The append-only log keeps 1X2 and goal-market predictions with their model-artifact fingerprints. After logged matches finish, the score command creates `reports/prospective_1x2_scorecard.json` with 1X2, Over 1.5/2.5/3.5, and BTTS scores.

## Reports and status

- [Reports index](reports/README.md): all reports and machine-readable evaluation artifacts in one place.
- [Comprehensive codebase audit](reports/repository_audit.md): current benchmark summary, engineering findings, test coverage, and improvement plan.
- [Project Status](PROJECT_STATUS.md): current snapshot and known model limitations.
- [Artifact Registry](ARTIFACT_REGISTRY.md): processed datasets and production model artifacts.

## Evaluation and interpretation

All model rows are ordered by kickoff. For 1X2 and Over 2.5, the main split uses the nearest boundary to 80% while keeping matches with equal kickoff times together; expanding-window CV folds also keep kickoff groups intact. Current 1X2 feature, ensemble, and recency-calibration gates use development data only. Season-by-season holdouts evaluate each test season using only earlier seasons. Probability calibration is fitted from chronological out-of-fold development predictions. Regression imputation and scaling are fitted within each training fold. Production models are refit on eligible rows after evaluation. The 1X2 report includes a Dixon–Coles baseline using the same main holdout and 1X2 training-season exclusion; it remains an evaluation comparator, not the API's production outcome model.

The data covers only a few seasons, and the latest season is incomplete. Treat small improvements over a mean or class-prior baseline as preliminary. Count thresholds use a negative-binomial distribution with dispersion estimated on training targets; reports compare it with Poisson and training-rate baselines. Raw metric omissions are kept as nulls with per-team `_reported` flags; models exclude rows whose target metrics are incomplete. Provider-sourced TheStatsAPI xG is stored with its source and shown in match details for post-match use; it is excluded from pre-match 1X2 features because actual match xG is only available after kickoff. Legacy aggregate-stat xG proxies are also excluded from the model. There is no model trained to predict pre-match xG.
