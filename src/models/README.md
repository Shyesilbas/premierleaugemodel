# Models Module

Trains, calibrates, evaluates, and persists production 1X2 outcome, 13x13 goal score-matrix, and gated regression count models for Premier League (plus reusable multi-league trainers).

> [!NOTE]
> **Related Documentation & Runbooks:**
> - **Model Registry & Specs:** [`docs/artifact_registry.md`](../../docs/artifact_registry.md) · [`docs/reports/models/goals_model.md`](../../docs/reports/models/goals_model.md) · [`docs/reports/models/outcome_1x2_model.md`](../../docs/reports/models/outcome_1x2_model.md)
> - **Key Entry Points:** [`train_match_outcome.py`](train_match_outcome.py) · [`train_goals.py`](train_goals.py) · [`evaluate_goal_models.py`](evaluate_goal_models.py) · [`goals_model.py`](goals_model.py) · [`dixon_coles.py`](dixon_coles.py) · [`count_model.py`](count_model.py) · [`model_utils.py`](model_utils.py) · [`eval_utils.py`](eval_utils.py) · [`train_league_model.py`](train_league_model.py) · [`train_league_counts.py`](train_league_counts.py) · [`train_league_goals.py`](train_league_goals.py)

## Business Rules & Invariants
- **1X2 Calibration & Ensembles:** `train_match_outcome.py` builds OOF temperature/bias calibrators via `forward_time_splits` and enables DC blending only when the outer-season gate passes.
- **Coherent Score Matrix (`13x13`):** `FeatureGoalModel` and `DixonColesModel` (`matrix_from_lambdas`) feed `align_to_outcome_probs`, scaling home/draw/away cells to the 1X2 probabilities before deriving `over_prob`, `btts_prob`, `team_over_prob`, and `expected_goals`.
- **Nested Goal Selection:** `train_goals.py` reads the exact same `BLEND_GRID` validated by `evaluate_goal_models.py` before writing `goals_models_v1.joblib`.
- **Two-Stage Count Skill Gates:** `train_corners.py`, `train_throws.py`, `train_offsides.py`, `train_cards.py`, and `train_saves.py` delegate through `train_count_model` (`CountModelSpec`): candidates must pass both `apply_skill_gate` (CV) and `apply_outer_season_gate` (dev seasons only); failing candidates fall back to `training_mean`.
- **Change rule:** Isolate exploratory runs with `PLM_MODELS_DIR` / `PLM_REPORTS_DIR`, preserve `LOCKED_SEASONS`, and test statistically via `with_inference` + `apply_fdr`.
