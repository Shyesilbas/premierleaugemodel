# AI_CONTEXT.md — Premier League Predictive Modeling Machine Context

> **Target Audience:** AI Agents, Copilots, Automated CI/CD Pipelines, and Quantitative Developers.  
> **Purpose:** Canonical single-file ground-truth context for the entire repository. No conversational prose; dense factual reference data.  
> **Documentation Network:** [README](README.md) | [Rapor Merkezi](docs/reports/README.md) | [Ana Kapsamlı Rapor](docs/reports/premier_league_models_comprehensive_report.md) | [Paper Trading 2026/27](docs/reports/paper_trading_protocol_2026_27.md) | [API Entegrasyonu](docs/model_api_integration.md) | [Veri Kataloğu](VERI_VE_GOSTERIM_KATALOGU.md)  
> **Last Updated:** 2026-10-24  
> **Database:** `data/premier_league.db` (SQLite3, 1,900 fixtures, 1,595 completed matches, 305 upcoming)  
> **Active Production Models:** `models/production/*.joblib`

---

## 1. Database & Data Architecture Specification

```yaml
database_architecture:
  sqlite_path: "data/premier_league.db"
  total_seasons: 5 (2022/23, 2023/24, 2024/25, 2025/26, 2026/27)
  fixture_counts:
    total_fixtures: 1900
    completed_matches: 1595
    upcoming_fixtures: 305
    current_season_played_matches: 75 (2026/27)
  tables:
    matches: { rows: 1900, cols: 40, role: "Core fixtures, scores, kickoff_millis, ground, referees, match status, competition_id" }
    external_match_xg: { rows: 1564, cols: 8, role: "TheStatsAPI / Opta verified shot-level xG backfill" }
    external_match_odds: { rows: 391, cols: 29, role: "Bookmaker opening and closing odds for 1X2, Over 2.5, BTTS" }
    player_market_values: { rows: 1771, cols: 10, role: "Transfermarkt player valuations, age, position, nationality" }
    team_market_values: { rows: 102, cols: 9, role: "Club total squad market values and squad size per season" }
    referees: { rows: 153, cols: 15, role: "Referee season aggregates, yellow/red card rates, strictness_label" }
    model_match_audit: { rows: 440, cols: 39, role: "Historical backtest audit log of model probabilities vs actuals" }
    tm_clubs_cache: { rows: 280, cols: 3, role: "Transfermarkt club ID mapping and badge asset URLs" }
    team_transfers_cache: { rows: 27, cols: 4, role: "Club inbound/outbound transfer market transaction history" }
    team_season_transfers_cache: { rows: 6, cols: 5, role: "Season-specific transfer detail cache" }
    player_market_value_history_cache: { rows: 3, cols: 4, role: "Player historical valuation trajectory cache" }
    predictions_cache: { rows: 0, cols: 6, role: "In-memory dynamic match prediction cache" }
  processed_parquet_layer:
    matches_summary_all: "data/processed/matches_summary_all.parquet (1,580 matches, 244+ Opta metrics)"
    shots_events_all: "data/processed/shots_events_all.parquet (all shot coordinates, events, outcome tags)"
    features_matches_all: "data/processed/features_matches_all.parquet (58 tactical features, strict shift(1))"
  event_stream_reconstruction:
    won_corners_recovered: 67 matches recovered from timeline event streams
    saves_reconstruction: cross-verified against opponent shots on target minus goals
```

---

## 2. Model 1: Flagship Goals Model (`goals_models_v1.joblib`)

> Audited and rebuilt on 2026-10-17. Full findings: `docs/reports/models/goals_model.md` §11.

```yaml
goal_model:
  type: "Independent Poisson rates + Dixon-Coles low-score tau, 13x13 score matrix (NOT a bivariate Poisson)"
  matrix_dimension: "13x13 (score cells from 0-0 to 12-12)"
  selection:
    source_of_truth: "src/models/train_goals.py::BLEND_GRID"
    grid: { feature_sets: [compact, full], feature_alphas: [0.1, 0.3, 1, 3, 10, 30], dc_weights: [0.0], dc_half_life_days: 365 }
    procedure: "select_blend_config(): forward folds inside the given data only, pooled exact-score NLL (-log M[i, min(h,12), min(a,12)]), lowest wins, no 1-SE rule"
    nested_in_evaluation: true   # evaluate_goal_models reruns selection inside each outer season
    gate_requires_same_grid: true
  production_config:            # chosen on all unlocked seasons (2022/23-2025/26); 2026/27 locked season not used
    feature_set: full
    feature_count: 60          # feature_names in the artifact (includes exp_match_xg_10, exp_venue_match_xg); COMPACT_GOAL_FEATURES (13) remains a grid option
    feature_alpha: 3.0
    dc_weight: 0.0            # lambda = lambda_feat; unused DC fit skipped when dc_weight == 0.0
    dc_half_life_days: 365
    rho: "fit_rho_from_lambdas() on blended lambdas (expanding OOF with sample_weight in FeatureGoalModel)"
    calibrators: { over_1.5: applied (0.4729 -> 0.4707), over_2.5: applied (0.6774 -> 0.6758), over_3.5: applied (0.6469 -> 0.6460), btts: applied (0.6830 -> 0.6817) }  # forward-fold OOF on 1X2-aligned matrix
    fit_matches: 1595
  api_serving:
    endpoint: "GET /api/predict"
    one_x_two_source: "outcome_models_v1 (logistic)"
    score_matrix: "align_to_outcome_probs(): matrix 1X2 regions rescaled to the logistic 1X2 during calibration, evaluation, and inference; O/U, BTTS, team totals, expected goals all read from the aligned matrix"
    btts_label: "null unless evaluation_gate.btts_gate.passed (CI vs constant Poisson must exclude 0); API also returns btts_informative"
  honest_outer_holdout:        # 1,140 matches (2023/24-2025/26), each season fit on earlier seasons only, nested selection; v1.6 + 1X2 v1.2 (2026-10-25)
    score_nll: { model: 2.9696, constant_poisson: 3.0959, v1_4: 2.9786, delta_vs_v1_4: -0.0090 }
    over_25_frozen_season: { mean_season_log_loss: 0.6767, delta_vs_prior: -0.0081, ci95: [-0.0157, -0.0003], ece_decile: 0.0424, significant: true }
    over_25_vs_constant_poisson: { delta: -0.0058, ci95: [-0.0132, +0.0018], significant: false }
    over_25_vs_market_bet365: { delta: +0.0078, ci95: [+0.0001, +0.0156], n: 1134, market_better: true }
    btts_vs_constant_poisson: { delta: -0.0017, ci95: [-0.0075, +0.0039], gate_passed: false }
    btts_vs_market_bet365:   { delta: +0.0046, ci95: [-0.0009, +0.0100], n: 1138 }
    over_25_weekly_refit:  { log_loss: 0.6756, vs_frozen: -0.0014, ci95_vs_frozen: [-0.0036, +0.0009], vs_rolling_prior: -0.0046, ci95_vs_rolling_prior: [-0.0110, +0.0018] }
    selected_configs: { "2023_24": "full a10 w0", "2024_25": "full a3 w0", "2025_26": "full a3 w0" }
    by_season_over_25_model_vs_prior: { "2023_24": [0.6645, 0.6790], "2024_25": [0.6763, 0.6854], "2025_26": [0.6892, 0.6900] }
    btts_model_vs_prior:     { "2023_24": [0.6709, 0.6863], "2024_25": [0.6840, 0.6824], "2025_26": [0.6851, 0.6859] }
    alignment_to_logistic_1x2: "not re-measured in v1.4 (v1.3: one_x_two -0.0157, over_25 -0.0012, btts +0.0014)"
  diagnosis:
    supremacy_vs_volume: "corr(lambda_h - lambda_a, goal diff) 0.44; corr(lambda_total, total goals) 0.065 (measured on the 58-feature model)"
    level_shift: "season scoring level moves: 2023/24 trained on 2.85 goals/match, observed 3.28 -> main cause of the pooled Under bias; weekly refit recovers it"
    market_benchmark_only: "closing O/U odds are a benchmark, not a feature (using them as a feature would copy the market)"
  rejected_experiments:
    1_isotonic_calibration: "In-sample 0.6712 -> OOF collapsed to 0.7107 (overfit step functions)"
    2_xgboost_residual_learner: "LL 0.6890 - 0.6904 vs 0.6774 (noise splitting)"
    3_sliding_window_500: "LL 0.6801 vs 0.6774 (data starvation at 25 matches/team)"
    4_lambda_floor_shrinkage: "Train-optimal alpha=0.00 (previous 0.40 was holdout snooping)"
    5_segment_10_blind_spot: "Mann-Whitney raw p=0.1687, Bonferroni p=1.0000, FDR q=0.4049 (Type I error)"
    6_temperature_calibration_ou: "Shuffled-KFold gain was time leakage; forward folds: O2.5 0.6777 -> 0.6799 (worse)"
    7_com_poisson_dispersion: "nu in {1.15, 1.3} via nested grid: O2.5 delta -0.0040 vs -0.0044 baseline, ECE 6.8% vs 4.6%, BTTS 2025/26 worse than prior"
    8_feature_model_recency_weights: "half-life 365d never selected in nested grid; 180d under weekly refit -0.0004 vs refit (noise)"
    9_dixon_coles_ridge_search: "ridge {1,3,10,30} nested: score NLL 3.0003 -> 3.0005; DC alone ridge 30 3.0314 vs blend 3.0003"
    10_lineup_shot_volume_features: "XI shot-volume features (2 variants): score NLL -0.0033 [-0.0051,-0.0016] but O2.5 -0.0005 / BTTS 0.0000, n.s. vs constant Poisson"
    11_dc_weight_0.25_0.5: "removed from grid: nested score NLL 3.0003 -> 2.9786 with dc_weights=[0.0]"
  superseded_values: "Pre-audit 0.6774 / ECE 2.17% / 1,200 matches included the locked 2026/27 season and hyperparameters picked on the same holdout."
```

---

## 3. Model 2: 1X2 Match Outcome Model (`outcome_models_v1.joblib`)

```yaml
outcome_1x2_model:
  type: "Multinomial Logistic Regression with Softmax Temperature Calibration"
  artifact_path: "models/production/outcome_models_v1.joblib"
  pipeline:
    imputer: "SimpleImputer(strategy='median', keep_empty_features=True)"
    scaler: "StandardScaler()"
    classifier: "LogisticRegression(C=0.003, max_iter=5000)"
  feature_count: 74  # v1.4 (2026-10-25): Starting XI minute-weighting & continuity (xi_continuity_diff, xi_weighted_ov_diff, missing_reg_mins_diff)
  calibrator:
    method: "forward_oof_on_all_eligible_training_matches"
    regularization: { reg_temp: 0.10, reg_bias: 0.50 }
    oof_sample_size: 922
  outer_season_walk_forward_1140_matches:
    seasons: { "2023_24": 0.9292, "2024_25": 0.9730, "2025_26": 1.0174 }
    pooled_log_loss: 0.9732 (v1.3: 0.9746, v1.2: 0.9757, v1.1: 0.9789, delta vs v1.1: -0.0057)
    pooled_accuracy_pct: 54.47% (v1.2: 54.30%, v1.1: 54.12%)
    pooled_brier: 0.5790 (v1.3: 0.5798, v1.2: 0.5806, v1.1: 0.5826)
    pooled_rps: 0.1977 (v1.3: 0.1980, v1.2: 0.1985, v1.1: 0.1994)
    cv_log_loss: 0.9674 (v1.3: 0.9709, v1.2: 0.9739, v1.1: 0.9755)
  dc_comparator:
    team_count: 25
    intercept: 0.240819
    home_advantage: 0.144825
    rho: -0.046433
  benchmark_304_holdout_matches:
    multiclass_log_loss: 1.0240 (prior: 1.0920)
    class_prior_baseline_log_loss: 1.0920
    paired_bootstrap_delta_ll: -0.0680 (95% CI: [-0.1062, -0.0285], p_superior = 0.9998)
    multiclass_brier: 0.6160 (prior: 0.661)
    rps: 0.2073 (prior: 0.2288)
    accuracy_pct: 50.33% (prior: 40.79%)
    dixon_coles_holdout_ll: 1.0459 (calibrated; raw 1.0477)
  class_log_loss_breakdown:
    home_win: { matches: 124, model_ll: 0.7868, prior_ll: 0.8205, pred_mean_prob: 48.16% }
    draw:     { matches: 85,  model_ll: 1.4089, prior_ll: 1.4608, pred_mean_prob: 24.91% }
    away_win: { matches: 95,  model_ll: 1.0070, prior_ll: 1.1155, pred_mean_prob: 39.83% }
  known_limitation:
    draw_separation: "Draw AUC = 0.557 (current artifact; earlier runs 0.513-0.527). Model knows macro draw rate (25.1% predicted vs 28.0% actual) but cannot discriminate single match draws. In an earlier run 38% of total log-loss stemmed from draw matches (not re-measured on the current artifact)."
  rejected_experiments:
    1_lagged_xg_form_features: "Removed due to post-match timing leakage and historical provider sparsity."
    2_two_stage_draw_model: "Holdout LL collapsed to 1.0536, Brier 0.6378. Predicted zero draws."
    3_nine_draw_propensity_features: "Outer season delta LL = +0.0041 (worsened). Decision gate failed."
    4_1x2_ensemble_gate: "Dixon-Coles + Logreg ensemble outer season delta LL = +0.00455 (p=0.1754). Gate failed."
    5_calibration_drift_windowing: "Outer season delta LL = +0.00049. Gate failed."
```

---

## 4. Model 3: Secondary Count & Dynamics Models (`models/production/`)

```yaml
count_and_dynamics_models:
  regression_skill_gate:
    policy: >-
      Two gates (src/models/model_utils.py). CV gate: 4-fold expanding window on the first 80%;
      must beat training_mean by >=0.5% RMSE and win >=3 folds. Outer-season gate (2026-10-17):
      must beat training_mean in a majority of complete nested outer seasons (locked 2026/27 excluded).
      Failing either deploys training_mean and the API reports model_skill="baseline".
    evaluation_pool: "1,264 dev matches, 316 held-out matches (holdout is report-only; it contains the locked season)"
    source_of_truth: "artifact['metrics'] in each joblib; per-model reports in docs/reports/models/"
  models:  # retrained 2026-10-24 on the 2026-10-24 feature parquet (conditional NB2 dispersion, dev-only outer gate)
    corners:
      artifact: "models/production/corner_model_v1.joblib"
      report: "docs/reports/models/corners_model.md"
      algorithm: "training_mean (elastic_0.05_0.8 passed CV gate, failed dev outer-season gate 1/2)"
      features_count: 10
      outer_season_wins: "1/2"
      dispersion_alpha: 0.0154
      holdout_rmse: 3.2345 (baseline: 3.2345)
      holdout_mae: 2.6693 (baseline: 2.6693)
    throws:
      artifact: "models/production/throws_model_v1.joblib"
      report: "docs/reports/models/throws_model.md"
      algorithm: "poisson_10"
      features_count: 14
      outer_season_wins: "2/2"
      dispersion_alpha: 0.0148
      holdout_rmse: 6.9409 (baseline: 7.3368)
      holdout_mae: 5.5210 (baseline: 5.9405)
    offsides:
      artifact: "models/production/offside_model_v1.joblib"
      report: "docs/reports/models/offsides_model.md"
      algorithm: "ridge_250"
      features_count: 10
      outer_season_wins: "2/2"
      dispersion_alpha: 0.0497
      holdout_rmse: 1.9060 (baseline: 2.0133)
      holdout_mae: 1.5177 (baseline: 1.6161)
    cards:
      artifact: "models/production/cards_model_v1.joblib"
      report: "docs/reports/models/cards_model.md"
      algorithm: "training_mean (poisson_1 passed CV gate, failed dev outer-season gate 1/2)"
      candidate_features_count: 11
      dispersion_alpha: 0.0614
      holdout_rmse: 1.9918 (baseline: 1.9918)
      target_definition: "total_cards = total_yellow_cards + total_red_cards (equal 1.0 weight)"
      referee_feature: "referee_avg_cards / referee_avg_fouls: leakage-free historical averages, 10-match shrinkage to 4.15 / 21.5; referee identity carries no significant card signal in this data (ANOVA p=0.28)"
    saves:
      artifact: "models/production/saves_model_v1.joblib"
      report: "docs/reports/models/saves_model.md"
      algorithm: "training_mean (ridge_500 failed CV gate: 0.59% gain but only 2/4 folds)"
      candidate_features_count: 13
      dispersion_alpha: 0.0202
      holdout_rmse: 2.3478 (baseline: 2.3478)
      holdout_mae: 1.9006 (baseline: 1.9006)
```

---

## 5. API and System Endpoint Mapping

```yaml
api_endpoints:
  predict_match:
    route: "GET /api/predict?home_id=&away_id="
    consumed_by:
      - "frontend/src/components/match-detail/MatchPredictionTab.jsx"
      - "frontend/src/components/PredictorTab.jsx"
      - "frontend/src/components/PredictorMetricCards.jsx"
    response_fields:
      1x2: "predictions.1x2 { home_pct, draw_pct, away_pct }"
      goals_over_15: "goals.over_1.5.pct"
      goals_over_25: "goals.over_2.5.pct"
      goals_over_35: "goals.over_3.5.pct"
      goals_btts: "goals.btts_pct, goals.btts_prediction"
      goals_team_totals: "goals.team_totals { home, away }"
      metrics_corners: "metrics.corners"
      metrics_cards: "metrics.cards"
      metrics_saves: "metrics.saves"
      metrics_offsides: "metrics.offsides"
      metrics_throws: "metrics.throws"
  prospective_logging:
    log_file: "data/processed/1x2_forecast_log.jsonl"
    scorecard_file: "docs/reports/prospective_1x2_scorecard.json"
    command: "python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14"
```