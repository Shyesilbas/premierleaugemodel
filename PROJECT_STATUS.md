# Project Status

**Snapshot:** 2026-10-14, local cached data  
**Current season:** 2026/27, 60 of 380 fixtures completed

Raporlara erişim: [Rapor Merkezi](reports/README.md) · [Kapsamlı kod denetimi](reports/repository_audit.md)

## Current state

- Five seasons contain 1,900 fixtures: 1,580 completed matches and 320 upcoming fixtures. Processed match and feature tables and production models were rebuilt from the local raw cache.
- Missing `won_corners` values are reconstructed from team-attributed event streams when the raw stat is absent. This adds 67 recovered team values and makes the total-corners target usable for all 1,580 completed matches. Raw values and reconstruction flags remain separate.
- Count-model selection now compares each feature model with a training-mean candidate inside every expanding-window fold. This gives the trainer a conservative fallback when the features do not generalize.
- TheStatsAPI xG remains in the separate provider table and API/frontend match display. Lagged xG form features have been removed from the feature dataset and 1X2 model because actual match xG is known only after kickoff. Coverage is 366/380 (2022/23), 35/380 (2023/24), 60/380 (2024/25), 320/380 (2025/26), and 60/60 played (2026/27).
- F10 extends prospective logging to Over 1.5/2.5/3.5 and BTTS, alongside 1X2, with outcome and goal-model fingerprints. See the [repository audit](reports/repository_audit.md) and append-only [forecast log](data/processed/1x2_forecast_log.jsonl).
- The full pipeline was rerun on 2026-10-14 from the local raw cache, rebuilding processed features, production artifacts, and current benchmark/data audit reports. The automated suite passed: 18 tests.
- Current benchmark scores and temporal comparisons are in [Model Benchmarks](reports/model_benchmarks.md). Data coverage and source quality are in [Data Quality](reports/data_quality.md); event-stream corner checks are in [Team Scenario Validation](reports/team_scenario_validation.md).

## Known model limits

- The grouped 1X2 holdout contains 304 matches (2025-10-18 onward); the fit uses 836 of the 1,216 development-period rows after the fixed 2022/23 exclusion. After removing xG form features, log loss is 1.028 versus 1.092 for the class-prior baseline; multiclass Brier is 0.620 versus 0.661. The model selected a draw as its most likely outcome in 2 of 304 matches. The draw-propensity gate saw one clean full development outer season, so the added features remain disabled.
- Equal kickoff times now stay together in CV and holdout splits. Current-run feature, ensemble, and recency decisions use development data only. The existing 2022/23 exclusion was held fixed rather than re-selected; treat the pre-kickoff 2026/27 forecast log as the cleaner prospective validation.
- Provider xG coverage remains incomplete, especially 2023/24 and the unfilled 2025/26 fixtures. Actual match xG is retained for display and post-match analysis, not pre-match prediction; the old aggregate proxy remains excluded.
- Saves are now usable for all 1,580 completed matches through event-stream recovery; raw provider values remain complete for 1,371 matches, and the original source flags are preserved. The saves model still selects `training_mean` after the CV skill gate. Details: [Model Benchmarks](reports/model_benchmarks.md) and [Data Quality](reports/data_quality.md).
- Count-model improvements over the mean are small for corners, saves, and cards. The fold-fitted mean candidate prevents selecting a more complex model unless it wins chronological CV, but holdout scores remain the authority.
- Dixon–Coles remains an evaluation comparator: on the same rows and training policy it scored 1.043 versus the classifier's 1.030. Its development-only ensemble gate currently has one eligible full season and did not improve; the three-season threshold is unmet. Full F4–F6 decisions are in the [1X2 audit](reports/1x2_model_audit.md).

## Next work

1. Keep saving immutable pre-kickoff 1X2 and goal-market forecasts, then score them after matches finish; do not use the partially evaluated season to repeatedly tune the model.
2. Compare high-coverage tactical features, such as forward-zone passing and final-third entries, through the same season holdouts before adding them to production.
3. Validate the event-derived corner fallback against source stats and unresolved team attribution as new raw data arrives.
4. Investigate authoritative goalkeeper-save data to recover the remaining missing target rows.
5. Run `python3 run_full_pipeline.py` after each raw-cache update and restart the API to load rebuilt production artifacts.
