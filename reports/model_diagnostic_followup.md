# Model Diagnostic Follow-up

> Historical investigation: this report preserves the earlier 1,200-match experiment and its paired holdout results. For the current 1,580-match snapshot and the latest production evaluation, use [Model Benchmarks](model_benchmarks.md) and [1X2 Model Audit](1x2_model_audit.md). The 2022–23 extension and subsequent model-policy results below are retained as development history.

Snapshot: 1,200 completed matches across 2023-24 through the partial 2026-27 season. The fixed chronological holdout is the last 240 matches; its first kickoff is 6 January 2026. All model selection and calibration use development-period data only.

## Card and offside labels on a paired holdout

The source-only fit uses only matches whose target was present in the PulseLive stats response. The event-filled fit uses the reconstructed target for every development match. Both are evaluated on the same final 240 matches using the event-filled target. Candidate selection uses four expanding-window folds within the first 960 matches.

| Target | Training labels | Train rows | Selected model | Holdout RMSE | Mean RMSE | Holdout MAE | Mean MAE | R² |
|---|---|---:|---|---:|---:|---:|---:|---:|
| Cards | Stats response only | 729 | `ridge_500` | 2.0716 | 2.1199 | 1.7040 | 1.7309 | -0.1784 |
| Cards | Event-filled | 960 | `ridge_500` | 1.9080 | 1.9184 | 1.5540 | 1.5674 | 0.0003 |
| Offsides | Stats response only | 608 | `ridge_250` | 2.1553 | 2.3381 | 1.8015 | 1.9613 | -0.1293 |
| Offsides | Event-filled | 960 | `ridge_250` | 1.9204 | 2.0593 | 1.5233 | 1.6525 | 0.1035 |

The fixed holdout contains 182 stats-complete card labels and 131 stats-complete offside labels. Event reconstruction supplies the remainder. The event-filled models reduce absolute errors on this holdout, especially for offsides. However, the mean baseline improves too, so the model's extra gain over the baseline remains small for cards and moderate for offsides. Card R² is effectively zero.

The older benchmark used a different holdout population after dropping incomplete labels. Its scores should not be directly compared with this paired result.

## 1X2 class probabilities

Label order is home win, draw, away win. The existing multinomial model has calibrated holdout log-loss 1.046, versus 1.050 raw and 1.104 for the class-prior baseline. Its multiclass Brier score is 0.631, versus 0.669 for the prior. The probability forecast beats the prior, though its class separation is uneven.

| Outcome | Actual rate | Mean raw probability | Mean calibrated probability | Mean probability when outcome occurs | Mean probability when it does not |
|---|---:|---:|---:|---:|---:|
| Home win | 39.17% | 41.96% | 40.64% | 46.49% | 36.87% |
| Draw | 30.42% | 25.06% | 27.31% | 27.97% | 27.02% |
| Away win | 30.42% | 32.98% | 32.06% | 36.80% | 29.99% |

The calibrated argmax confusion matrix is below; rows are actual outcomes and columns are predicted outcomes.

| Actual \\ predicted | Home | Draw | Away |
|---|---:|---:|---:|
| Home | 72 | 2 | 20 |
| Draw | 37 | 4 | 32 |
| Away | 38 | 3 | 32 |

Only 4 of 73 actual draws are selected as the most likely class. More tellingly, mean draw probability is 27.97% when the match is a draw and 27.02% otherwise. The current features and model do little to distinguish draw matches from non-draw matches. A global probability adjustment can shift the overall draw rate, but cannot create that missing separation.

## Explicit draw-model experiment

A two-stage model was evaluated on the same split: first estimate draw versus non-draw, then estimate home versus away conditional on a non-draw. Both stages used forward-only cross-validation for candidate selection and calibration.

| Model | Holdout log-loss | Accuracy | Brier | Predicted draws |
|---|---:|---:|---:|---:|
| Existing calibrated multinomial | 1.0460 | 45.00% | 0.6310 | 9 |
| Two-stage, raw | 1.0536 | 43.33% | 0.6378 | 0 |
| Two-stage, forward-calibrated | 1.0587 | 42.50% | 0.6419 | 0 |
| Dixon–Coles, calibrated | 1.0733 | 41.67% | 0.6491 | 6 |

Neither tested alternative replaces the existing classifier. The two-stage draw score did not rank any holdout match with a draw probability above both win probabilities.

## Next experiments

Odds/bookmaker fields are absent from the local match data. They are not needed for the current goal, so the model work can stay focused on its own pre-match features and probability quality. With the extra season in place, evaluate each full season as a chronological holdout and concentrate next on features and calibration that can distinguish draws from wins. Keep the current classifier as the baseline until a time-ordered evaluation shows a consistent gain.

## 2022–23 season extension

The 2022–23 season was fetched from the existing PulseLive API (competition-season ID 489): 380/380 fixtures have stats, event streams, and match details, with no duplicate fixture IDs. Processing and feature generation now include it, and the production pipeline was rerun. The dataset grew from 1,200 to 1,580 completed matches. Card and offside targets are usable for all 1,580 matches after event-based recovery.

The refreshed benchmark uses 316 matches in its main holdout, compared with 240 before adding the season, so those overall holdout scores are not a direct before/after comparison. After the training-policy change below, the 1X2 model has log-loss 1.044 versus a 1.114 class-prior baseline, and Brier 0.630 versus 0.675. It selects a draw for 2 of 316 matches. Season-by-season results and all target metrics are in `reports/model_benchmarks.md`.

To isolate its supervised-training contribution, both 1X2 variants were evaluated on the same final 240 matches, with the same feature rows and forward-only model selection/calibration. The only difference is whether 2022–23 rows are included in the training sample.

| 1X2 training data | Train rows | Selected model | Calibrated log-loss | Prior log-loss | Brier | Accuracy | Predicted draws | Mean draw probability on draws / other matches |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| 2023–24 onward | 960 | `logreg_C0.003` | 1.0418 | 1.1041 | 0.6288 | 44.17% | 7 | 27.80% / 26.81% |
| 2022–23 onward | 1,340 | `logreg_C0.001` | 1.0499 | 1.1055 | 0.6359 | 44.58% | 0 | 24.39% / 23.73% |

The same comparison was repeated with full-season holdouts. “Without 2022–23” still keeps the season in feature history; it removes only its labeled rows from 1X2 model fitting.

| Holdout | Matches | Log-loss without / with 2022–23 | Brier without / with 2022–23 | Draw picks without / with 2022–23 |
|---|---:|---:|---:|---:|
| 2024–25 | 380 | 0.9908 / 0.9964 | 0.5903 / 0.5946 | 9 / 0 |
| 2025–26 | 380 | 1.0298 / 1.0276 | 0.6201 / 0.6183 | 8 / 0 |
| 2026–27 (partial) | 60 | 1.0323 / 1.0365 | 0.6195 / 0.6258 | 6 / 1 |

Including 2022–23 slightly helps the 2025–26 proper scores, but worsens them on the other two holdouts and consistently lowers draw probabilities. The current 1X2 trainer therefore leaves the season in rolling feature history but excludes its match labels from supervised fitting. The refreshed benchmark and production artifact use that policy. This improves the evidence-based training choice; it does not solve draw separation. The next model experiment should compare a recent rolling window with recency-weighted training and evaluate across full-season holdouts.
