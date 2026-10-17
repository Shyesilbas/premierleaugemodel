# AI_CONTEXT.md — Premier League Goal Model Machine Context

> **Target Audience:** AI Agents, Copilots, and Quantitative Developers.  
> **Purpose:** Canonical single-file ground-truth context. No conversational prose; dense factual reference data.  
> **Last Updated:** 2026-10-17  
> **Project Commit:** `1715019` / `9070f61`  
> **Active Model Path:** `models/production/goals_models_v1.joblib`

---

## 1. Core Model Specification & Hyperparameters

```yaml
model_architecture:
  type: "Hybrid Bivariate Poisson + Dixon-Coles Matrix"
  matrix_dimension: "13x13 (score cells from 0-0 to 12-12)"
  components:
    feature_poisson:
      class: "src.models.goals_model.FeatureGoalModel"
      loss: "Poisson Deviance"
      penalty: "L2 (Ridge)"
      alpha: 10.0
      max_iter: 3000
      scaler: "StandardScaler"
      imputer: "SimpleImputer(strategy='median')"
      feature_count: 58
      home_intercept: 0.4431
      away_intercept: 0.1748
    dixon_coles:
      class: "src.models.dixon_coles.DixonColesModel"
      time_decay: "Exponential"
      half_life_days: 365
      rho_parameter: -0.0910
      rho_bootstrap_mean: -0.0869
      rho_bootstrap_se: 0.0408
      rho_bootstrap_95_ci: [-0.1500, -0.0062]
      rho_sensitivity_over25_ll: "Invariant at 0.67743 for rho in [-0.20, +0.10] (cells (0,0),(1,0),(0,1),(1,1) are all Under 2.5)"
      estimation: "L-BFGS-B Maximum Penalized Likelihood on training set"
  blending:
    method: "Geometric"
    formula: "lambda_final = (lambda_dc ** 0.25) * (lambda_feat ** 0.75)"
    dc_weight_production: 0.25
    dc_weight_global_optimum: 0.20
    delta_ll_production_vs_optimum: +0.000056
    rho_blend: "0.5 * (rho_dc + rho_feat) = -0.0610 (optimal for low-score NLL: 2.4549)"
  numerical_guardrails:
    lambda_clip_min: 0.05
    lambda_clip_max: 6.00
    locked_seasons: ["2026_27"]
  leakage_audit_certificate:
    state_after_shift_1_applied: true
    kickoff_timestamp_monotonic: true
    walk_forward_cross_season_leakage: 0.0000
```

---

## 2. Definitive Benchmark & Evaluation Metrics (1,200 Holdout Matches)

*Holdout Pool: Seasons 2023/24, 2024/25, 2025/26, 2026/27 (walk-forward out-of-fold).*

```yaml
evaluation_pool:
  total_matches: 1200
  actual_over_25_rate: 0.586667
  actual_btts_rate: 0.583333
  entropy_upper_bound_H: 0.678049

baselines_log_loss:
  naive_fixed_prior_p05263: 0.685403
  naive_blind_poisson_p05430: 0.681915
  theoretical_constant_ceiling: 0.678049
  production_model_v12: 0.677428
  safe_information_gain: -0.000621

market_metrics_v12:
  over_25:
    log_loss: 0.677428
    brier: 0.242277
    roc_auc: 0.536623
    ece_percent: 2.17
  over_15:
    log_loss: 0.475612
    brier: 0.158421
    roc_auc: 0.538120
    ece_percent: 2.85
  over_35:
    log_loss: 0.648031
    brier: 0.228145
    roc_auc: 0.535890
    ece_percent: 3.31
  btts:
    log_loss: 0.680614
    brier: 0.243810
    roc_auc: 0.524018
    ece_percent: 2.90

continuous_lambda_and_score:
  mae_home_goals: 0.989
  mae_away_goals: 0.881
  mae_total_goals: 1.300
  correlation_lambda_actual: +0.285
  exact_score_top_1_accuracy: 11.5%
  exact_score_top_3_accuracy: 29.6%
  exact_score_top_5_accuracy: 45.3%

walk_forward_seasons_ll:
  season_2023_24: 0.6692
  season_2024_25: 0.6764
  season_2025_26: 0.6861
  season_2026_27_first_60: 0.6806
```

---

## 3. Market Comparison & Edge Sweep (218 Odds Matches)

```yaml
bookmaker_vs_model:
  sample_size: 218
  market_closing_auc: 0.5962
  model_auc: 0.5843
  delta_auc_market_minus_model: +0.0118
  bootstrap_10k_delta_auc_ci_95: [-0.0483, +0.0723]
  p_value_auc_diff: 0.3520
  verdict: "Statistically indistinguishable; underpowered sample."

edge_sweep_multiple_testing:
  k_hypotheses: 7
  threshold_gt_0pct:  { n: 118, win_rate: 0.500, roi: -6.99%,  p_binom_raw: 0.6491, p_bonf: 1.0000, q_fdr: 0.8714 }
  threshold_gt_2pct:  { n: 67,  win_rate: 0.552, roi: +6.25%,  p_binom_raw: 0.2368, p_bonf: 1.0000, q_fdr: 0.8289 }
  threshold_gt_3pct:  { n: 51,  win_rate: 0.569, roi: +10.02%, p_binom_raw: 0.1995, p_bonf: 1.0000, q_fdr: 0.8289 }
  threshold_gt_4pct:  { n: 32,  win_rate: 0.500, roi: -1.62%,  p_binom_raw: 0.5432, p_bonf: 1.0000, q_fdr: 0.8714 }
  threshold_gt_5pct:  { n: 18,  win_rate: 0.500, roi: -3.42%,  p_binom_raw: 0.5916, p_bonf: 1.0000, q_fdr: 0.8714 }
  threshold_gt_7pct:  { n: 7,   win_rate: 0.429, roi: -15.50%, p_binom_raw: 0.7469, p_bonf: 1.0000, q_fdr: 0.8714 }
  threshold_gt_10pct: { n: 0,   win_rate: 0.000, roi: +0.00%,  p_binom_raw: 1.0000, p_bonf: 1.0000, q_fdr: 1.0000 }
  verdict: "All thresholds span noise margins after FDR control (q > 0.80). Paper trading mandatory."

tail_risk_decile_calibration_1200:
  prediction_range: { min_p: 0.4109, max_p: 0.7455, median_p: 0.5630 }
  bins:
    lt_45_extreme_under: { n: 8,   share: "0.7%",  pred_mean: 43.70%, actual: 75.00%, gap: +31.30%, ll: 0.7682, brier: 0.2873 }
    45_to_50_mild_under: { n: 117, share: "9.8%",  pred_mean: 48.22%, actual: 55.56%, gap: +7.33%,  ll: 0.6992, brier: 0.2530 }
    50_to_55_balanced:   { n: 345, share: "28.7%", pred_mean: 52.99%, actual: 53.62%, gap: +0.63%,  ll: 0.6932, brier: 0.2500 }
    55_to_60_mild_over:  { n: 469, share: "39.1%", pred_mean: 57.34%, actual: 59.91%, gap: +2.58%,  ll: 0.6756, brier: 0.2413 }
    60_to_65_clear_over: { n: 188, share: "15.7%", pred_mean: 62.00%, actual: 61.17%, gap: -0.83%,  ll: 0.6660, brier: 0.2366 }
    65_to_70_high_over:  { n: 56,  share: "4.7%",  pred_mean: 66.79%, actual: 69.64%, gap: +2.85%,  ll: 0.6147, brier: 0.2118 }
    gt_70_extreme_over:  { n: 17,  share: "1.4%",  pred_mean: 72.47%, actual: 76.47%, gap: +4.00%,  ll: 0.5470, brier: 0.1804 }
  verdict: "High probabilities (>65%) are monotonically well calibrated with decreasing log-loss (0.547). Model avoids overconfidence (>85%)."
```

---

## 4. Feature Ablations, Collinear Redundancy & Stability

```yaml
feature_ablation_effective_log_mv_ratio:
  hypothesis: "Highest regression coefficient (0.0148) is collinear with Elo/PPG."
  results_1200_matches:
    58_features_ll: 0.677428
    57_features_ll: 0.677517
    delta_ll_57_minus_58: +0.000089
    delta_auc_57_minus_58: -0.000487
    bootstrap_10k_delta_ll_ci: [-0.000158, +0.000341]
    p_value_delta_ll: 0.4900
    bootstrap_10k_delta_auc_ci: [-0.001808, +0.000816]
    p_value_delta_auc: 0.4814
  verdict: "Strictly equivalent. Safe to drop in v1.3 for model parsimony."

feature_importance_vs_coefficients:
  spearman_rank_correlation: 0.1379
  spearman_p_value: 0.3019
  verdict: "Zero correlation between raw coefficient size and true permutation importance."
  top_permutation_features:
    1: home_big_chances_against_roll_10 (delta_ll = +0.000634)
    2: home_high_line (delta_ll = +0.000242)
    3: away_xg_against_ewma_02 (delta_ll = +0.000227)
    4: away_xg_against_roll_10 (delta_ll = +0.000224)
    5: elo_venue_home (delta_ll = +0.000181)
    12: effective_log_mv_ratio (delta_ll = +0.000087, raw_coef_rank = 1)

feature_drift_stability_across_seasons:
  spearman_rank_correlation_matrix:
    2023_24_vs_2024_25: -0.0245
    2024_25_vs_2025_26: +0.0927
    2023_24_vs_2025_26: +0.0140
  verdict: "Features exhibit collinear rank drift across seasons due to L2 regularization over redundant football quality metrics."
  top_5_most_stable_features:
    1: away_shots_ontarget_against_ewma_02 (mean_rank: 6.7, std: 3.3)
    2: away_venue_xg_against_ewma_02 (mean_rank: 11.3, std: 3.8)
    3: elo_home (mean_rank: 13.7, std: 3.1)
    4: ppg_away (mean_rank: 15.7, std: 6.9)
    5: home_big_chances_for_roll_10 (mean_rank: 19.0, std: 5.9)
```

---

## 5. Rejected Empirical Experiments Log

```yaml
rejected_experiments:
  1_isotonic_calibration:
    in_sample_ll: 0.6712
    out_of_fold_5cv_ll: 0.7107
    reason: "Catastrophic overfit on non-parametric step functions."
  2_btts_post_calibration:
    platt_oof_ll: 0.6830
    beta_oof_ll: 0.6832
    raw_bivariate_matrix_ll: 0.6806
    reason: "Non-stationary target drift (%61.6 in 2023 -> %55.0 in 2026). Retained raw matrix."
  3_xgboost_residual_learner:
    stacking_ll: 0.6901
    native_residual_base_margin_ll: 0.6890
    independent_xgboost_ll: 0.6904
    reason: "Tree splits amplified noise without L2 Poisson shrinkage. Features lacked chaos representation."
  4_sliding_window_500:
    sliding_ll: 0.6801
    expanding_ll: 0.6774
    reason: "Sample starvation (~25 matches/team). Expanding window with half_life=365 is superior."
  5_lambda_floor_shrinkage:
    train_optimal_alpha: 0.0000
    reason: "Previous alpha=0.40 was holdout snooping. Pre-2023 train set lacked bottom-tier goal explosion."
  6_segment_10_blind_spot_hypothesis:
    raw_p_mann_whitney: 0.1687
    bonferroni_p: 1.0000
    bh_fdr_q: 0.4049
    correlation_lambda_actual_p: 0.1018
    reason: "False positive due to uncorrected multiple subgroup testing across 12 cohorts. Refuted."
```

---

## 6. Complete List of 58 Features Categorized

```yaml
features_58:
  penalty_box_and_shots_14:
    - home_touches_in_opp_box_roll_10
    - home_touches_in_opp_box_ewma_02
    - away_touches_in_opp_box_roll_10
    - away_touches_in_opp_box_ewma_02
    - home_shots_for_roll_10
    - home_shots_for_ewma_02
    - away_shots_for_roll_10
    - away_shots_for_ewma_02
    - home_shots_against_roll_10
    - away_shots_against_roll_10
    - home_shots_ontarget_against_roll_10
    - home_shots_ontarget_against_ewma_02
    - away_shots_ontarget_against_roll_10
    - away_shots_ontarget_against_ewma_02
  xg_quality_8:
    - home_xg_for_roll_10
    - home_xg_for_ewma_02
    - away_xg_for_roll_10
    - away_xg_for_ewma_02
    - home_xg_against_roll_10
    - home_xg_against_ewma_02
    - away_xg_against_roll_10
    - away_xg_against_ewma_02
  elo_and_points_form_8:
    - elo_home
    - elo_away
    - elo_venue_home
    - elo_venue_away
    - ppg_home
    - ppg_away
    - gdpg_home
    - gdpg_away
  venue_specific_form_8:
    - home_venue_xg_for_roll_10
    - home_venue_xg_for_ewma_02
    - home_venue_xg_against_roll_10
    - home_venue_xg_against_ewma_02
    - away_venue_xg_for_roll_10
    - away_venue_xg_for_ewma_02
    - away_venue_xg_against_roll_10
    - away_venue_xg_against_ewma_02
  big_chances_6:
    - home_big_chances_for_roll_10
    - home_big_chances_for_ewma_02
    - away_big_chances_for_roll_10
    - away_big_chances_for_ewma_02
    - home_big_chances_against_roll_10
    - away_big_chances_against_roll_10
  tactical_high_line_3:
    - home_high_line
    - away_high_line
    - mutual_high_line_risk
  squad_market_value_4:
    - effective_log_mv_ratio
    - log_mv_ratio
    - home_attack_vs_away_defense_mv
    - away_attack_vs_home_defense_mv
  possession_and_pace_7:
    - home_possession_roll_10
    - away_possession_roll_10
    - home_passes_acc_roll_10
    - away_passes_acc_roll_10
    - exp_match_shots_5
    - abs_elo_diff
    - rest_days_diff
```

---

## 7. System & API Endpoint Integration

```yaml
api_endpoints:
  predict_match:
    route: "/api/predict"
    method: "POST"
    schema_fields:
      goals_over_15: "goals.over_1.5.pct"
      goals_over_25: "goals.over_2.5.pct"
      goals_over_35: "goals.over_3.5.pct"
      goals_btts: "goals.btts_pct"
      goals_btts_pred: "goals.btts_prediction"
      goals_team_totals_home: "goals.team_totals.home"
      goals_team_totals_away: "goals.team_totals.away"
      exact_scores: "goals.exact_scores"
      lambdas: "goals.lambdas { home, away, total }"
    frontend_components:
      - "frontend/src/components/match-detail/MatchPredictionTab.jsx"
      - "frontend/src/components/PredictorMetricCards.jsx"
  audit_and_simulation:
    route: "/api/audit/goals"
    method: "GET"
    frontend_components:
      - "frontend/src/components/ModelAuditTab.jsx"
```

---