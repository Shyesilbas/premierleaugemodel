"""The Premier League's feature definitions applied to a league fed only by TheStatsAPI (LaLiga).

Instead of re-implementing the Premier League features, this module renames the league's statistics to the Premier League's
raw column names and runs the Premier League's own functions on them (``build_team_match_history``,
``compute_pre_match_features``, ``merge_features_to_matches``). Opponent-Elo normalisation of shots, shots on target, big chances,
touches and xG, the penalty strip (xG minus 0.78 per penalty attempt, big chances minus one per attempt), the rolling and
exponential windows, the venue form with sample-size shrinkage and the interaction and difference features are therefore the same
code, not a copy of it.

What differs, because of the data:
* penalty attempts are estimated from the provider's xG and non-penalty xG: ``round((xG - npxG) / 0.78)``;
* the first-XI features come from the provider's per-player rating (``_xi_features``), not from the Premier League's own player
  score, and the attack/defence split is by position;
* squad market values and penalty-area entries have no historical source, so the Premier League columns built from them
  (``log_mv_ratio``, ``effective_log_mv_ratio``, ``schedule_mv_diff``, ``sdiff_pa_entries_*``) are constant here and are left out
  (``parity_feature_columns``);
* cold-start NaNs are filled with the Premier League's league priors, as in the Premier League table.
"""

from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd

from src.features.build_features import add_interaction_features, compute_referee_features, build_team_match_history, compute_pre_match_features, merge_features_to_matches
from src.features.build_league_features import COUNT_TARGETS, _xi_features, build_league_features
from src.models.train_match_outcome import feature_set

PENALTY_XG = 0.78
# league statistic (see build_league_features.STAT_PATHS) -> the Premier League raw column it feeds, per side
RAW_COLUMNS = {"shots": "total_scoring_att", "sot": "ontarget_scoring_att", "big_chances": "big_chance_created", "touches_box": "touches_in_opp_box",
               "passes": "total_pass", "accurate_passes": "accurate_pass", "possession": "possession_percentage", "corners": "won_corners",
               "throws": "total_throws", "saves": "saves", "fouls": "fk_foul_lost", "offsides": "total_offside", "yellow": "total_yel_card",
               "red": "total_red_card"}
STRENGTH_COLUMNS = ["elo_home", "elo_away", "elo_diff", "elo_venue_home", "elo_venue_away", "elo_venue_diff", "ppg_home", "ppg_away", "ppg_diff",
                    "gdpg_home", "gdpg_away", "gdpg_diff", "home_rest_days", "away_rest_days"]
IDENTITY_COLUMNS = ["match_id", "season", "gameweek", "match_date", "time_label", "home_id", "away_id", "home_name", "away_name", "home_score",
                    "away_score", "status", "referee_name", "kickoff", "kickoff_millis"]


def _premier_league_frame(matches: pd.DataFrame, base: pd.DataFrame, player_lines: pd.DataFrame) -> pd.DataFrame:
    """The league's matches under the Premier League's raw column names (pre-match Elo, points and first-XI columns included)."""
    frame = base[IDENTITY_COLUMNS + STRENGTH_COLUMNS].copy()
    frame["match_date"] = pd.to_datetime(frame["kickoff"])
    frame["is_played"] = frame["home_score"].notna() & frame["away_score"].notna()
    raw = matches.set_index("match_id")
    for side in ("home", "away"):
        for stat, column in RAW_COLUMNS.items():
            frame[f"{side}_{column}"] = frame["match_id"].map(raw[f"{side}_{stat}"])
        frame[f"statsapi_{side}_xg"] = frame["match_id"].map(raw[f"{side}_xg"])  # the Premier League names this one with the side in the middle
        frame[f"{side}_penalty_attempts"] = np.maximum(0.0, ((raw[f"{side}_xg"] - raw[f"{side}_np_xg"]) / PENALTY_XG).round()).reindex(frame["match_id"]).to_numpy()
    xi = _xi_features(base.assign(**{}), player_lines, with_missing=True)
    for column in ("home_xi_att_vs_away_def", "away_xi_att_vs_home_def"):  # the Premier League goal-model feature set reads these two as well
        frame[column] = xi[column].to_numpy()
    for column in ("xi_rating_diff", "xi_att_vs_def_diff", "xi_continuity_diff", "xi_weighted_ov_diff", "xi_missing_reg_mins_diff"):
        frame[column.replace("xi_missing_reg_mins_diff", "missing_reg_mins_diff")] = xi[column].to_numpy()
    return frame


def build_parity_features(matches: pd.DataFrame, player_lines: pd.DataFrame) -> pd.DataFrame:
    """One row per match with the Premier League's feature columns (identity columns of ``build_league_features`` included)."""
    base = build_league_features(matches)
    frame = _premier_league_frame(matches, base, player_lines)
    long_history = compute_pre_match_features(build_team_match_history(frame))
    merged = merge_features_to_matches(frame, long_history)
    merged = add_interaction_features(merged)
    for target in COUNT_TARGETS:  # match totals of the count models, summed from this league's statistics
        merged[target] = merged["match_id"].map(base.set_index("match_id")[target])
    merged = compute_referee_features(merged)  # the Premier League's referee tendencies (its shrinkage and default values)
    merged = merged.sort_values(["kickoff", "match_id"], kind="mergesort").reset_index(drop=True)
    merged["kickoff_millis"] = merged["kickoff"].astype("int64") // 1_000_000
    return merged


# Built in the Premier League from data this league does not have. The market-value columns are constant; the penalty-area-entry
# columns are not (the default entry count is scaled by the opponent's Elo multiplier), but then they would be an Elo feature in
# disguise, so they are left out explicitly.
NO_SOURCE_COLUMNS = ("log_mv_ratio", "effective_log_mv_ratio", "schedule_mv_diff", "sdiff_pa_entries_e02", "sdiff_pa_entries_r10")


def parity_feature_columns(frame: pd.DataFrame) -> List[str]:
    """The Premier League's 1X2 feature list (``feature_set``) minus the columns this league has no data for."""
    played = frame["home_score"].notna()
    return [c for c in feature_set("1x2", list(frame.columns)) if c not in NO_SOURCE_COLUMNS and frame[c].notna().any() and frame.loc[played, c].nunique() > 1]
