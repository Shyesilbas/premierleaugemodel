# Features Module

Computes leak-free pre-match team, strength, draw propensity, referee, and starting-XI features shared identically across offline training and live API inference.

> [!NOTE]
> **Related Documentation & Runbooks:**
> - **Architecture & Model Docs:** [`docs/reports/models/outcome_1x2_model.md`](../../docs/reports/models/outcome_1x2_model.md) · [`docs/reports/models/goals_model.md`](../../docs/reports/models/goals_model.md)
> - **Key Entry Points:** [`build_features.py`](build_features.py) · [`draw_features.py`](draw_features.py) · [`build_league_features.py`](build_league_features.py) · [`build_league_pl_features.py`](build_league_pl_features.py)

## Business Rules & Invariants
- **Strict Pre-Game Boundary (`shift(1)`):** Every rolling window (`[3, 5, 10]`), EWMA (`[0.2, 0.4]`), Elo update, and referee aggregate uses strictly prior completed matches (`compute_pre_match_features`, `compute_team_states`).
- **Train-Serve Parity:** Live inference calls `build_prediction_row` (PL) and `build_league_features` / `build_parity_features` (TheStatsAPI national leagues) rather than duplicating feature math; verified by `tests/test_train_serve_parity.py` and `tests/test_league_model.py`.
- **Same-Kickoff Draw Isolation:** `DrawFeatureState` (`build_draw_state`, `add_draw_features`) batches matches by kickoff timestamp so simultaneous fixtures never leak into one another.
- **Cold-Start Priors & Elo Reset:** `fill_feature_priors` fills early-season gaps via `LEAGUE_PRIORS`, while `advance_strength_state_to_season` regresses team Elo ratings by `ELO_SEASON_REGRESS = 0.20` toward `1500.0` (newcomers start at `ELO_NEWCOMER = 1430.0`).
- **Change rule:** Any new feature or window change requires updating parity tests and validating against multi-season outer-season gates without reading `LOCKED_SEASONS`.
