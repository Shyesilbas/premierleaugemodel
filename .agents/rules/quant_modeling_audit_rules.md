# Quant Modeling & Empirical Audit Guidelines

These mandatory guidelines govern all statistical modeling, calibration, and evaluation in this repository:

### 1. Strict Out-of-Fold / Zero Data Snooping Protocol
- **Calibrator & Shrinkage Fitting**: Any post-processing calibration (Platt, Beta, Isotonic) or shrinkage parameter (α, floor threshold) MUST be fit strictly on training folds or expanding walk-forward splits. Never select, tune, or optimize calibrator parameters on holdout or evaluation data.
- **Reporting In-Sample vs OOF**: In-sample scores may be reported for diagnostic purposes (learning curves, ablation studies), but MUST be explicitly labeled as such and never presented as generalization performance. All reported log-loss, Brier, and AUC numbers must be 5-fold cross-validated or temporal out-of-fold.

### 2. Mandatory Statistical Rigor & Small Sample Guardrails
- **Bootstrap Confidence Intervals**: For any sample size N < 500, never state a point estimate (ROI, win rate, delta AUC) without computing a 10,000-iteration Bootstrap 95% Confidence Interval and Binomial confidence bounds.
- **Statistical Significance**: If a 95% CI for delta-loss or delta-AUC spans zero (p ≥ 0.05), explicitly document that the difference is within noise margins and state the power requirements (required N) rather than claiming victory.
- **Multiple Testing Correction**: When testing k > 1 segments, hypotheses, or markets, apply Bonferroni or Benjamini-Hochberg FDR correction, or explicitly document why no correction was applied.

### 3. Unified Cross-Market Probability Monotonicity
- All multi-market goal probabilities (P(Over 1.5), P(Over 2.5), P(Over 3.5), P(BTTS)) must be derived from the coherent bivariate score matrix M_ij.
- Never implement ad-hoc divergent code branches or separate sub-models for single markets that violate joint consistency (P(1.5) ≥ P(2.5) ≥ P(3.5)) or create disjoint predictions for the same match.

### 4. Hypothesis-Driven Diagnosis Before Algorithm Hopping
- When a model underperforms or exhibits inverse ranking (AUC < 0.50) on a cohort:
  1. Test the foundational distribution assumptions first (e.g. dispersion index σ²/μ, Chi-square goodness-of-fit for Poisson overdispersion).
  2. Inspect feature-level variances and individual feature-target correlations inside that cohort.
  3. Formulate domain-grounded interaction features before switching algorithms (e.g., jumping to XGBoost or separate segment-specific models).
- **Feature Importance ≠ Coefficient**: Assess feature importance via permutation importance or SHAP, not raw regression coefficients. A high coefficient does not imply high predictive importance if the feature has collinear redundancy or low variance.

### 5. Reproducibility & Seed Management
- All stochastic processes (train/test splits, bootstrap resampling, model initialization, cross-validation folds) MUST be explicitly seeded.
- Report seed values in all experiment logs and script headers.
- Results must be bitwise reproducible across identical runs; if non-determinism is detected, investigate and eliminate the source before publishing findings.
- Maintain dataset snapshot integrity (or data versioning) for training and holdout datasets.
