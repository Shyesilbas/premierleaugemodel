# Project Status

**Snapshot:** 2026-10-14, local cached data  
**Current season:** 2026/27, 60 of 380 fixtures completed

## Current state

- Five seasons contain 1,900 fixtures: 1,580 completed matches and 320 upcoming fixtures. Processed match and feature tables and production models were rebuilt from the local raw cache.
- Missing `won_corners` values are reconstructed from team-attributed event streams when the raw stat is absent. This adds 67 recovered team values and makes the total-corners target usable for all 1,580 completed matches. Raw values and reconstruction flags remain separate.
- Count-model selection now compares each feature model with a training-mean candidate inside every expanding-window fold. This gives the trainer a conservative fallback when the features do not generalize.
- F7 removed the low-coverage aggregate xG proxy from active features and the API path. The repository has no trained or production xG input; historical proxy comparisons remain only as audit records.
- F10 extends prospective logging to Over 1.5/2.5/3.5 and BTTS, alongside 1X2, with outcome and goal-model fingerprints. See [model-improvement guide, F10](reports/model_improvement_guide.md) and the append-only [forecast log](data/processed/1x2_forecast_log.jsonl).
- Current benchmark scores and temporal comparisons are in [Model Benchmarks](reports/model_benchmarks.md). Data coverage and source quality are in [Data Quality](reports/data_quality.md); event-stream corner checks are in [Team Scenario Validation](reports/team_scenario_validation.md).

## Known model limits

- The main 1X2 holdout log loss is 1.045 versus 1.114 for the class-prior baseline; multiclass Brier is 0.630 versus 0.675. Actual draws were 31.0%, mean predicted draw probability was 23.4%, draw AUC was 0.5381, and the model selected a draw as its most likely outcome in 4 of 316 matches. Draw-focused features gave small, mixed changes across season holdouts, so this is not a solved problem.
- Only three full prior-season holdouts and one 60-match partial-season holdout are available. Several policy and feature comparisons have been reviewed on those same seasons; keep the remainder of 2026/27 as a prospective evaluation set.
- Reliable shot-level xG is not available locally. The low-coverage aggregate proxy is not used in the current feature or API path.
- Saves are now usable for all 1,580 completed matches through event-stream recovery; raw provider values remain complete for 1,371 matches, and the original source flags are preserved. The saves model still selects `training_mean` after the CV skill gate. Details: [model-improvement guide, F9](reports/model_improvement_guide.md).
- Count-model improvements over the mean are small for corners, saves, and cards. The fold-fitted mean candidate prevents selecting a more complex model unless it wins chronological CV, but holdout scores remain the authority.
- Dixon–Coles remains an evaluation comparator: its 1X2 ensemble failed the three-season production gate (1/3 seasons improved; mean log-loss change +0.00312), so the production classifier remains unchanged. Full F4–F6 decisions are in the [1X2 audit](reports/1x2_model_audit.md).

## Next work

1. Keep saving immutable pre-kickoff 1X2 and goal-market forecasts, then score them after matches finish; do not use the partially evaluated season to repeatedly tune the model.
2. Compare high-coverage tactical features, such as forward-zone passing and final-third entries, through the same season holdouts before adding them to production.
3. Validate the event-derived corner fallback against source stats and unresolved team attribution as new raw data arrives.
4. Investigate authoritative goalkeeper-save data to recover the remaining missing target rows.
5. Run `python3 run_full_pipeline.py` after each raw-cache update and restart the API to load rebuilt production artifacts.
