# Project Status

**Snapshot:** 2026-10-13, local cached data
**Current season:** 2026/27, 60 of 380 fixtures completed

## Current state

- Four cached seasons contain 1,520 fixtures, including 1,200 completed matches and 320 upcoming fixtures.
- Processed match and feature tables were rebuilt from the local raw cache; the combined feature table has 534 columns, including raw-stat presence flags.
- All production model families were retrained. Candidate selection uses expanding-window time-series folds, with both a final chronological holdout and prior-season holdouts recorded in [Model Benchmarks](reports/model_benchmarks.md).
- The 1X2 classifier was compared with a Dixon–Coles team attack/defence baseline on identical chronological and season holdouts. The benchmark is evaluative; the existing classifier remains the production model.
- Data coverage, missing-stat selection patterns, and event-stream reports were regenerated. See [Data Quality](reports/data_quality.md), [Team Tactical Data Audit](reports/team_tactical_data_audit.md), and [Team Scenario Validation](reports/team_scenario_validation.md).

## Known model limits

- Results remain preliminary because only three season holdouts are available and the latest one is partial. Compare the per-season score ranges with the single chronological holdout.
- 1X2 and over/under probabilities now use a chronological out-of-fold temperature and class-offset calibrator. The calibration needs more seasons before it can be considered stable.
- Count thresholds now use a negative-binomial distribution with dispersion fit on training targets; the benchmark compares NB2, Poisson, and training-rate baselines.
- Omitted raw metrics remain null with `_reported` flags. Incomplete target rows are excluded from count-model training. Red-card omissions are still treated as zero under a sparse-event assumption, so card labels can be understated if the provider omits a real red card.
- Missingness is not uniform: offsides coverage drops from 65.8% in 2023/24 to 56.6% in 2025/26, and cards coverage also declines. The report compares this selection with team and match-outcome patterns; these are descriptive associations, not proof of cause.
- The Dixon–Coles comparator improves on the class-prior log-loss baseline but trails the current calibrated classifier on the main holdout; it also rarely chooses draws as its top class. It has not replaced the production model.
- The `xg` columns are a hand-built aggregate-stat proxy, not Opta shot-level xG and not a separately trained model.
- An incremental fixture sync refreshes processed data but does not retrain models. Run `python3 run_full_pipeline.py` after a sync and restart the API to load current artifacts.

## Next work

1. Recover or supplement missing yellow-card, save, and offside data, then recheck whether the current coverage gaps are provider-side or source-side.
2. Add more completed seasons and monitor whether the current classifier's advantage over Dixon–Coles persists.
3. Validate omitted sparse-count fields against event streams or another authoritative source, especially red cards.
4. Replace the xG proxy with verified shot-level xG input or remove the xG label from predictions.
