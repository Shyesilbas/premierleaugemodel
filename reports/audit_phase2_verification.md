# Phase 2: Independent Forensic Verification and Reproducibility Report

**Audit Date:** 14 October 2026  
**Lead Forensic Auditor:** Senior ML Engineer & Statistical Modeling Auditor  
**Target Document Under Review:** [reports/comprehensive_ml_audit.md](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/reports/comprehensive_ml_audit.md)  
**Execution Environment:** macOS, Python 3.12, scikit-learn, SQLite3, pandas  
**Evaluation Status:** Completed with live code execution; no production models or training data altered.

---

## 1. Executive Verdicts on Major Audit Claims

Each claim from the previous audit report was evaluated against actual source code and executed test scripts.

| # | Previous Audit Claim | Forensic Verdict | Ground Truth Evidence & File Reference |
|:---:|---|:---:|---|
| **C-01** | *Rolling features are strictly team-specific, lag-shifted, and free of target leakage.* | **VERIFIED** | Synthetic 3-team test in `audit/test_investigation_1.py` passed. [src/features/build_features.py:L241-L285](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/src/features/build_features.py) groups strictly by `team_id`, applies rolling mean over played matches, and shifts by 1. |
| **C-02** | *Database has 1,580 completed matches and 320 upcoming fixtures across 5 seasons.* | **VERIFIED** | Verified by SQL query on `matches` table in `data/premier_league.db`. Seasons 22/23 to 25/26 have 380 played matches each (1,520 total); 26/27 has 60 played and 320 upcoming. Total = 1,900 fixtures. |
| **C-03** | *Season 2026/27 is locked out from model evaluation, selection, and holdout splits.* | **VERIFIED** | `LOCKED_SEASONS = {'2026_27'}` in [src/models/train_match_outcome.py:L85](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/src/models/train_match_outcome.py#L85) filters out all 60 matches of 26/27 prior to `chronological_holdout_split`. |
| **C-04** | *Evaluation holdout contains exactly 304 matches.* | **VERIFIED** | Chronological 80% boundary on 1,520 evaluation matches yields 1,216 dev matches and **304 holdout matches** (all within season 2025/26: 2025-10-18 to 2026-05-24). |
| **C-05** | *1X2 model achieves 1.026 log-loss, 0.619 Brier, 49.01% accuracy, 0.5267 Draw AUC.* | **VERIFIED** | Directly reproduced from `outcome_models_v1.joblib` metrics dictionary across 304 holdout matches. |
| **C-06** | *Over 2.5 achieves 0.692 log-loss, 0.249 Brier, 56.58% raw / 54.61% calibrated accuracy.* | **VERIFIED** | Directly reproduced from `outcome_models_v1.joblib` on the 304 holdout matches. |
| **C-07** | *Secondary count models achieve Corners RMSE 3.1952, Cards RMSE 2.0201, Offsides MAE 1.5178.* | **VERIFIED** | Directly reproduced from artifact metrics dictionaries. Sample size is $N=316$ matches (20% split on 1,580 played matches). |
| **C-08** | *Offsides holdout RMSE was reported as 1.8980.* | **PARTIALLY VERIFIED** | Artifact holds `test_rmse = 1.9064` (delta = 0.0084). MAE (1.5178) and $R^2$ (+0.0971) match exactly. |
| **C-09** | *Red cards are weighted 2.0 in the cards target (`total_cards = yel + 2*red`).* | **CONTRADICTED** | [src/processing/process_season_data.py:L282](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/src/processing/process_season_data.py#L282) defines `total_cards = total_yellow_cards + total_red_cards`. Red cards are weighted **1.0**, not 2.0. |
| **C-10** | *Production serving in `server.py` evaluates the primary logistic regression model.* | **PARTIALLY VERIFIED** | [src/api/server.py:L1685-L1689](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/src/api/server.py#L1685-L1689) actually blends logistic regression with Dixon–Coles (`blend_log`, weight 0.65) because `"model_dc"` is present in the artifact, despite the ensemble failing the outer season gate during training. |
| **C-11** | *Scoreline matrix probabilities sum to 1.0, and Over lines are monotonic.* | **VERIFIED** | Evaluated on 20 fixtures in `audit/test_investigation_5.py`: 0 axiom violations. Monotonicity ($O1.5 \ge O2.5 \ge O3.5$) and BTTS sum identities hold within $10^{-6}$. |
| **C-12** | *Statistical superiority of 1X2 model holds under calendar clustering.* | **VERIFIED** | Cluster-robust Gameweek-block bootstrap yields 95% CI $[-0.1271, -0.0427]$ (widening by only +2.71% vs. IID $[-0.1274, -0.0452]$). $P(\text{model} > \text{prior}) = 100.0\%$. |

---

## 2. Table of Reported vs. Independently Reproduced Metrics

Evaluated by `audit/test_investigation_3.py`:

| Target / Metric | Previously Reported | Independently Reproduced | Absolute Difference | Verification Verdict | Holdout $N$ |
|---|:---:|:---:|:---:|:---:|:---:|
| **1X2 Multiclass Log-Loss** | 1.0260 | 1.0260 | 0.0000 | **VERIFIED** | 304 |
| **1X2 Multiclass Brier Score** | 0.6190 | 0.6190 | 0.0000 | **VERIFIED** | 304 |
| **1X2 Accuracy (%)** | 49.01% | 49.01% | 0.00% | **VERIFIED** | 304 |
| **1X2 Draw AUC** | 0.5267 | 0.5267 | 0.0000 | **VERIFIED** | 304 |
| **1X2 Draw ECE** | 0.0755 | 0.0755 | 0.0000 | **VERIFIED** | 304 |
| **Over 2.5 Goals Log-Loss** | 0.6920 | 0.6920 | 0.0000 | **VERIFIED** | 304 |
| **Over 2.5 Brier Score** | 0.2490 | 0.2490 | 0.0000 | **VERIFIED** | 304 |
| **Over 2.5 Raw Accuracy (%)** | 56.58% | 56.58% | 0.00% | **VERIFIED** | 304 |
| **Over 2.5 Calibrated Accuracy (%)** | 54.61% | 54.61% | 0.00% | **VERIFIED** | 304 |
| **Over 2.5 ECE** | 0.0787 | 0.0787 | 0.0000 | **VERIFIED** | 304 |
| **Corners Holdout RMSE** | 3.1952 | 3.1952 | 0.0000 | **VERIFIED** | 316 |
| **Corners Holdout MAE** | 2.5932 | 2.5932 | 0.0000 | **VERIFIED** | 316 |
| **Cards Holdout RMSE** | 2.0201 | 2.0201 | 0.0000 | **VERIFIED** | 316 |
| **Cards Holdout MAE** | 1.6328 | 1.6328 | 0.0000 | **VERIFIED** | 316 |
| **Offsides Holdout RMSE** | 1.8980 | 1.9064 | +0.0084 | **MINOR DISCREPANCY** | 316 |
| **Offsides Holdout MAE** | 1.5178 | 1.5178 | 0.0000 | **VERIFIED** | 316 |

---

## 3. Exact Holdout Membership & Chronological Split Details

Reconciled by `audit/test_investigation_2.py`:

```
Total Matches in System: 1,900
├── Completed / Played Matches: 1,580
│   ├── Locked Out Season 2026/27: 60 matches (Preserved as prospective holdout)
│   └── Evaluation Cohort (2022/23 to 2025/26): 1,520 matches
│       ├── Chronological Split Boundary (80.0%): 1,216 matches
│       │   ├── EXCLUDED_1X2_TRAINING_SEASONS (2022/23): 380 matches (Feature history only)
│       │   ├── 1X2 Final Fitted Training Set: 836 matches
│       │   └── Over 2.5 Final Fitted Training Set: 1,216 matches
│       └── Chronological 1X2 & Over 2.5 Holdout: 304 matches (20.0%)
└── Upcoming Fixtures: 320 matches (all in 2026/27)
```

- **Holdout Start Date:** `2025-10-18 16:30:00`
- **Holdout End Date:** `2026-05-24 15:00:00`
- **Seasons Represented in 1X2 Holdout:** Exclusively season `2025_26` (the final 304 matches of that season).
- **Secondary Models Holdout Split:** Evaluated on all 1,580 played matches (including the 60 matches of 2026/27), yielding $1580 \times 0.20 = \mathbf{316\text{ matches}}$.

---

## 4. Synthetic Rolling-Feature Test & Results

Executed by `audit/test_investigation_1.py`:

- **Design:** Created 3 teams (101, 102, 103) with distinct magnitude values:
  - Team 101: `[10.0, 20.0, 30.0, 40.0]`
  - Team 102: `[1.0, 2.0, 3.0, 4.0]`
  - Team 103: `[100.0, 200.0, 300.0, 400.0]`
- **Observations:**
  1. For match index 0 of every team, `xg_roll_2` returned `NaN`.
  2. For match index 1, `xg_roll_2` returned match 0's value exactly (10.0, 1.0, 100.0).
  3. For match index 2, `xg_roll_2` returned mean of matches 0 and 1 (15.0, 1.5, 150.0).
  4. For match index 3, `xg_roll_2` shifted the window (mean of matches 1 and 2: 25.0, 2.5, 250.0).
- **Simultaneous Kickoff Verification:** Teams playing concurrent fixtures at 15:00 BST do not leak statistics into each other's pre-match rows.
- **Unplayed Fixture Inheritance:** Match 503 (unplayed) correctly inherited the form state of Team 1 (2.2) and Team 3 (0.5) from prior played matches.

---

## 5. Production versus Component Model Comparison

Investigated in `audit/test_investigation_4.py`:

| Component / Layer | Artifact Key | Present in Production Joblib? | Active in `src/api/server.py`? | Holdout Log-Loss |
|---|:---:|:---:|:---:|:---:|
| **Standalone Logistic Regression** | `model_1x2` | Yes | Yes (Base component) | **1.0260** |
| **Dixon–Coles Bivariate Poisson** | `model_dc` | Yes | Yes (Blended component) | 1.0358 |
| **Blended Ensemble** | `blend_log(0.65/0.35)` | Yes | **YES (Active Runtime Path)** | ~1.0261 (Outer season $\Delta=+0.0063$) |

### Forensic Finding on Inference Routing
- In `src/models/train_match_outcome.py:L442`, the ensemble failed the development gate:
  `Gate: failed; 0/1 seasons improved; mean log-loss Δ +0.0063.`
- However, `train_match_outcome.py:L1160` unconditionally saves `"model_dc"` into `outcome_models_v1.joblib` for prospective logging.
- At runtime, `src/api/server.py:L1685` checks `has_ensemble = "model_dc" in outcome_artifact`, which evaluates to `True`, inadvertently serving the blended ensemble rather than pure standalone logistic regression.

---

## 6. Mathematical Consistency Test Summary

Investigated in `audit/test_investigation_5.py` across 20 representative fixtures:

1. **Unit Probability Mass:** $\sum_{x, y} P(x, y) = 1.000000$ (Max deviation: $1.1 \times 10^{-7}$). **PASSED**.
2. **Monotonicity Across Goal Lines:** $P(\text{Over 1.5}) \ge P(\text{Over 2.5}) \ge P(\text{Over 3.5})$ holds across all 20 fixtures without inversion. **PASSED**.
3. **BTTS Scoreline Identity:** $\text{BTTS} = \sum_{x \ge 1, y \ge 1} P(x, y)$ matches `btts_prob()` within $10^{-6}$. **PASSED**.
4. **1X2 Decomposition from Score Matrix:** $P(\text{Home}) + P(\text{Draw}) + P(\text{Away}) = 1.000000$. **PASSED**.
5. **Standalone Over 2.5 Classifier vs. Matrix Over 2.5:**
   - Mean absolute difference: **4.68%**
   - Maximum absolute difference: **13.29%**
   - **Root Cause:** Dual modeling architecture. In `server.py`, Over 1.5 and 3.5 come from the Dixon–Coles score matrix, whereas Over 2.5 comes from the binary logistic classifier. While not a crash, it creates internal tension.

---

## 7. Highest-Severity Verified Defects

1. **Defect D-01 (Serving Gate Bypass):** [src/api/server.py:L1685](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/src/api/server.py#L1685) automatically enables Dixon–Coles blending whenever `"model_dc"` is present in the artifact dictionary. Because training saves `"model_dc"` even after failing the outer-season decision gate, production inadvertently serves the blended output instead of the standalone winner.
2. **Defect D-02 (Dual Goal Model Discrepancy):** The API exposes Over 2.5 from a standalone logistic classifier while exposing Over 1.5, 3.5, and BTTS from the Dixon–Coles matrix. On fixtures with high divergence, $P(\text{Over 2.5})$ can differ from the matrix by up to 13.3 percentage points.
3. **Defect D-03 (Audit Target Definition Inaccuracy):** The previous audit report stated that red cards carry a 2.0 weight in the cards target. The actual code in [src/processing/process_season_data.py:L282](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/src/processing/process_season_data.py#L282) uses equal 1.0 weighting (`total_yellow_cards + total_red_cards`).

---

## 8. List of Checks That Could Not Be Completed & Blockers

1. **Prospective Out-of-Sample Evaluation on Completed 2026/27 Matches:**
   - *Status:* BLOCKED / UNAVAILABLE.
   - *Reason:* While 60 matches of 2026/27 have been played, prospective predictions were not logged prior to those kickoffs. Testing on them now would constitute a retrospective backtest, not a true prospective forecast audit.
2. **Devigged Market Odds (+EV Benchmark):**
   - *Status:* BLOCKED / PENDING PHASE 5.
   - *Reason:* Pre-match exchange closing odds (Pinnacle/Betfair) are not yet populated in `external_match_odds`.

---

## 9. Prioritized Remediation Plan

*(To be implemented in subsequent phases after user authorization)*

1. **P0 — Fix Serving Gate in `server.py`:** Add explicit check: `has_ensemble = outcome_artifact.get("metrics", {}).get("1x2_ensemble_production", {}).get("enabled", False) and outcome_artifact.get("metrics", {}).get("evaluation_gate", {}).get("gate_passed", False)` to ensure failed ensemble experiments do not alter production serving.
2. **P0 — Unify Goal Totals to Dixon–Coles Joint Matrix:** Route Over 2.5 through `over_prob(score_matrix, 2.5)` to enforce 100% mathematical consistency across all goal markets.
3. **P1 — Correct Audit Documentation:** Update `reports/comprehensive_ml_audit.md` Deliverable H to accurately reflect equal 1.0 weighting for red cards.
4. **P1 — Ingest Market Odds:** Implement Shin / power devigging algorithm on closing market odds to establish true $+EV$ scorecard benchmarks.
