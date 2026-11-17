---
name: quant-model-experiment-and-audit
description: >-
  Use this skill whenever designing, running, auditing, or documenting machine learning
  experiments, feature ablations, calibration checks, walk-forward backtests, or model
  promotions in multi-league football prediction workflows. Enforces zero-leakage protocols,
  locked season boundaries, baseline skill gates, train-serve parity, and documentation sync.
---

# Quant Model Experiment, Audit & Promotion Workflow

Follow this workflow whenever evaluating new features, tuning model hyperparameters, auditing model behavior, or updating model reports in `premierLeaugeModelApp`.

## 1. Pre-Flight & Production Safety
1. **Read Registry & Status First:** Check `docs/artifact_registry.md` and `docs/project_status.md` before changing models or features.
2. **Never Overwrite Production Silently:** Isolate experiments with `PLM_DATA_DIR`, `PLM_MODELS_DIR`, `PLM_MODELS_ROOT`, and `PLM_REPORTS_DIR`, or write experimental outputs to `reports/experiments/` and `research/`. Never overwrite `models/production/<competition>/` during exploratory runs.
3. **Zero Emoji & Deterministic Seeds:** Zero emojis in code, comments, docstrings, or reports. Seed stochastic operations (bootstrap, permutations, CV) and record seeds in script docstrings and reports.

## 2. Strict Zero-Leakage & Validation Protocol
1. **Pre-Game Boundaries (`shift(1)`):** Rolling windows, EWMA, opponent-adjusted metrics, referee aggregates, Elo ratings, and Starting XI features must strictly use matches completed before kickoff (`shift(1)` or same-kickoff batch isolation). Never feed post-match xG, shots, or end-of-season market values as pre-match signals without flagging/preventing leakage.
2. **Out-of-Fold Calibrators & Nested Selection:** Fit softmax temperature/bias calibrators, O/U & BTTS probability calibrators, and `select_blend_config` / `tune_league_elo` grids strictly on earlier forward folds inside unlocked training seasons.
3. **Locked Season Rule (`2026_27`):** Defined in `src/config.py:LOCKED_SEASONS`. Never use `2026_27` for feature selection, hyperparameter tuning, or skill-gate decisions; report it strictly as prospective monitoring.
4. **Expanding-Window Walk-Forward:** Evaluate candidates across unseen historical outer seasons (`2023_24`, `2024_25`, `2025_26` for PL; configured outer seasons for national leagues) where each test season uses only earlier seasons for training.

## 3. Hypothesis-Driven Diagnosis & Baseline Skill Gates
1. **Diagnose Before Algorithm Hopping:** Measure permutation importance by feature family (never raw collinear regression weights alone).
2. **Mandatory Baseline Skill Gates:**
   - **1X2 Outcome:** Class prior and Elo + Home advantage (`LOG_LOSS`, `Brier`, `RPS`).
   - **Goals Matrix (`13x13`):** Nested prior, constant Poisson, and Bet365 closing odds (`O1.5`, `O2.5`, `O3.5`, `BTTS`, exact score NLL).
   - **Count Models (`corner`, `throws`, `offside`, `cards`, `saves`):** Both 4-fold CV gate (`apply_skill_gate`) AND nested outer-season gate (`apply_outer_season_gate`). Failing either deploys `training_mean` (`model_skill="baseline"`).
3. **Statistical Rigor & Multiple Testing:** Use paired block bootstrap (`with_inference`) with 10,000 iterations and Benjamini-Hochberg FDR (`apply_fdr` in `src/models/eval_utils.py`) when testing multiple markets or variants.
4. **Honest Rejection ("No Gain, Not Adopted"):** Keep simpler production baselines when gains are statistically null or fail decision gates, and document rejected experiments in `docs/reports/models/<model>.md`.

## 4. Train-Serve Parity & Unified Matrix Coherence
1. **Train-Serve Skew Audit:** Verify live prediction builders (`build_prediction_row` in `src/features/build_features.py` and `build_league_features` / `build_parity_features` for national leagues) match offline training columns (`tests/test_train_serve_parity.py`, `tests/test_league_model.py`).
2. **1X2-Aligned Score Matrix:** Keep `align_to_outcome_probs` active across evaluation, calibration, and `src/api/prediction_service.py` so 1X2, O/U, BTTS, and team totals share one coherent distribution.

## 5. Documentation & Registry Sync Chain
1. Update or add the relevant model report in `docs/reports/models/<model>.md` (and `reports/models/*.json` if generated) plus `docs/reports/premier_league_models_comprehensive_report.md` if architecture changes.
2. Update `docs/artifact_registry.md` and `docs/project_status.md`.
3. Update `AGENTS.md` if production feature counts or active models changed.
4. Run `./scripts/verify.sh` and `pytest -q`.
