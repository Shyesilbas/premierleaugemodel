---
name: quant-model-experiment-and-audit
description: >-
  Use this skill whenever designing, running, auditing, or documenting machine learning
  experiments, feature ablations, calibration checks, walk-forward backtests, or model
  promotions in sports prediction repositories. Enforces zero-leakage protocols, locked
  season boundaries, baseline skill gates, train-serve parity, and documentation sync.
---

# Quant Model Experiment, Audit & Promotion Workflow

Follow this workflow whenever evaluating new features, tuning model hyperparameters, auditing model behavior, or updating model reports.

## 1. Pre-Flight & Production Safety

1. **Read Registry & Status First**:
   - Check `docs/artifact_registry.md` or `ARTIFACT_REGISTRY.md` and `docs/project_status.md` or `PROJECT_STATUS.md` before touching any code or data.
2. **Never Overwrite Production Silently**:
   - Never overwrite artifacts under `models/production/` or production manifests (`config/production_artifacts.yaml`) during analysis or experimentation.
   - Write all experimental outputs to `models/experimental/`, `data/experimental/`, `research/`, or `reports/backtests/YYYY-MM-DD_<topic>/`.
3. **Zero Emoji in Code & Artifacts**:
   - Never place emojis in Python code, comments, docstrings, commit messages, or markdown reports.
4. **Reproducibility & Seed Management**:
   - Explicitly seed all stochastic processes (train/test splits, bootstrap resampling, model initialization, CV folds). Report seeds in experiment headers and verify bitwise determinism.

## 2. Strict Zero-Leakage & Validation Protocol

1. **Strict Pre-Game Boundaries (`shift(1)`)**:
   - Every rolling, EWMA, form, usage, opponent allowance, or Elo feature must strictly use information available prior to tip-off / kickoff (`shift(1)` on chronologically sorted game logs).
   - Post-game statistics (e.g., realized match xG, actual minutes played tonight, overtime points) must never enter pre-game feature columns.
2. **Out-of-Fold Calibrators & Shrinkage**:
   - Fit all post-processing calibrators (Platt, temperature scaling, beta, isotonic) and shrinkage/prior weights (`alpha`, floor thresholds, blend decay windows) strictly inside training folds or expanding walk-forward splits. Never tune them on holdout or evaluation seasons.
   - Explicitly label any in-sample diagnostic metric as in-sample; never present it as generalization performance.
3. **Locked / Active Season Rule**:
   - The active in-progress season (e.g., `2026-27`) is locked for prospective monitoring. Do not use it to select features, tune hyperparameters, or make deployment decisions.
4. **Expanding-Window Walk-Forward & Outer-Season Evaluation**:
   - Evaluate candidates across multiple unseen historical seasons using expanding-window walk-forward validation (each season predicted by a model fit strictly on earlier seasons).

## 3. Hypothesis-Driven Diagnosis & Baseline Skill Gates

1. **Diagnose Before Algorithm Hopping**:
   - When a model underperforms on a cohort, test foundational distribution assumptions first (e.g., dispersion index $\sigma^2/\mu$, Chi-square goodness-of-fit for Poisson overdispersion) and inspect feature variances/correlations before switching algorithms (e.g., jumping to XGBoost).
   - Measure feature utility via permutation importance, SHAP, or multi-season ablation—never raw regression coefficients alone (collinear features can have large coefficients with near-zero permutation $\Delta \text{LL}$).
2. **Mandatory Baseline Comparison (Skill Gate)**:
   - Always benchmark candidates against strong, honest pre-game baselines:
     - **Win / 1X2 Probability**: Pure Elo + Home advantage, or historical base rates.
     - **Score / Goals / Totals**: Last-10 / EMA-10 actual points, prior-season team means, or `training_mean`.
     - **Player / Count Props**: EMA-10 per-game average or `training_mean` + outer-season gate.
   - **Gate Criterion**: A feature or model passes only if it beats the baseline on primary proper scoring rules (Log-Loss, Brier, MAE, RMSE) across the majority of unseen outer seasons.
3. **Statistical Rigor, Power Analysis & Multiple Testing**:
   - **Bootstrap CI**: For sample sizes $N < 500$, compute a 10,000-iteration bootstrap 95% Confidence Interval on the metric delta ($\Delta \text{LL}$, $\Delta \text{Brier}$, $\Delta \text{MAE}$).
   - **Power Analysis**: If the 95% CI spans zero ($p \ge 0.05$), document that the difference is within noise margins and state the required sample size:
     $$N_{\text{req}} = \frac{(Z_{\alpha/2} + Z_\beta)^2 \cdot \sigma^2}{\Delta^2}$$
     where $Z_{\alpha/2} = 1.96$ ($\alpha=0.05$) and $Z_\beta = 0.8416$ ($80\%$ power).
   - **Multiple Testing**: When testing $k > 1$ segments, hypotheses, or markets, apply Bonferroni or Benjamini-Hochberg FDR correction.
4. **Honest Rejection ("No Gain — Not Adopted")**:
   - If an experiment fails the skill gate or adds complexity for negligible gain (e.g., $< 0.01$ MAE on points or $< 0.0005$ Log-Loss), **do not adopt it**. Keep the simpler production configuration and record the negative result in the backtest/model report so it is not re-tested later.

## 4. Train-Serve Parity & Cross-Market Coherence

1. **Train-Serve Skew Audit**:
   - Verify that live inference code paths (FastAPI endpoints, CLI predictors, daily schedule runners) produce identical feature values and post-processing adjustments (early-season blends, residual corrections, injury/absence deltas) as the offline training dataset builder.
2. **Coherent Multi-Market Probabilities**:
   - Winner prediction must come from the dedicated Win / 1X2 probability model (or a score matrix explicitly aligned to it).
   - Multi-threshold probabilities ($P(\text{Over } 1.5) \ge P(\text{Over } 2.5) \ge P(\text{Over } 3.5)$, $P(\text{BTTS})$) must remain monotonic and derived from a single coherent distribution/matrix $M_{ij}$.

## 5. Documentation & Registry Synchronization Chain

Whenever a model changes, an audit concludes, or a backtest is finalized, update documents in this exact order using metrics read directly from the generated artifact/JSON files (never copy-paste stale numbers from prose):

1. **Experiment / Model Report**:
   - Create or update `reports/backtests/YYYY-MM-DD_<topic>/README.md` (with reproducible scripts in `code/`) or `docs/reports/models/<model>.md`.
2. **Artifact Registry**:
   - Register new active datasets, backtest reports, or promoted model artifacts in `docs/artifact_registry.md` or `ARTIFACT_REGISTRY.md`.
3. **Project Status**:
   - Log the completed work, key metric deltas, and current production status in `docs/project_status.md` or `PROJECT_STATUS.md`.
4. **Root Overview**:
   - Update benchmark tables in `README.md` (and `AI_CONTEXT.md` if present) if headline metrics or model versions changed.
5. **Verification**:
   - Run the test suite (`PYTHONPATH=. python3 -m pytest tests -q`) and structure audits (`scripts/audit/validate_project_structure.py` if present) before finishing.
