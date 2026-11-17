# Reports

Two kinds of files live here (default `REPORTS_DIR = <repo>/reports`, configurable via `PLM_REPORTS_DIR`). Generated outputs are written by training, auditing, or benchmarking scripts and are never edited by hand. Records (audits, experiments) are dated, frozen notes of what was measured on a given date. Architecture and active model docs live under [`docs/README.md`](../docs/README.md) and [`docs/reports/models/`](../docs/reports/models/).

## Generated Outputs

| Report / Output | Generator Command | Purpose |
|---|---|---|
| `model_benchmarks.md` | `python3 run_full_pipeline.py` | PL chronological holdout and count-model regression gate summary. |
| `data_quality.md` | `python3 -m src.analytics.data_quality_report` | 5-season PL fixture coverage, missing target counts, and recovered metrics. |
| `team_tactical_data_audit.md` | `python3 -m src.analytics.team_data_audit` | Tactical stat availability and zero-vs-missing audit across seasons. |
| `team_scenario_validation.md` | `python3 -m src.analytics.audit_team_scenarios` | Event-stream shot/corner reconstruction validation against match totals. |
| `prospective_1x2_scorecard.json` | `python3 -m src.analytics.prospective_1x2_benchmark score` | Live prospective 1X2 & goal-market log-loss/Brier scorecard vs market and prior baselines. |
| `models/<key>_*.json` | `train_league_model`, `train_league_counts`, `evaluate_league_goal_models`, `tune_league_elo`, `ablate_league_features`, `league_feature_audit` | Machine-readable JSON evaluations for optional TheStatsAPI national leagues. |
| `experiments/2026-10-25_box_features_ablation.json` | `python3 research/box_features_ablation.py` | Penalty-area and box-touch feature ablation for PL 1X2. |
| `1x2_lineup_feature_pilot.md` | `python3 research/lineup_feature_pilot.py` | Starting XI continuity feature pilot evaluation. |

## Frozen Audits & Experiment Notes

- `audits/1x2_model_audit.md` — 1X2 forensic audit and calibration analysis.
- `audits/goal_models_analysis.md` — Oct 19, 2026 Goals / Over 2.5 / BTTS root-cause analysis.
- `audits/repository_audit.md` — Oct 17, 2026 codebase structure and test audit snapshot.
- `audits/scripts_audit.md` — Oct 25, 2026 script inventory and workflow audit.
- `experiments/2026-10-25_new_league_readiness.md` — Summary of PL box-feature ablation for future national-league readiness.
