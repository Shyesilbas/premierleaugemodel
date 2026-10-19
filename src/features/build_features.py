#!/usr/bin/env python3
"""
Premier League Leakage-Free Feature Engineering Pipeline
Constructs match-level rolling statistics (EWMA / rolling windows), opponent-adjusted metrics,
rest days, team form and team strength (Elo, season-to-date points) for predictive modeling.

Strict Leakage-Free Principle:
For any match t, team features are calculated using ONLY matches played before t (strictly historical).

Train/serve consistency:
The same helpers (team states, strength states, prior filling, interaction features) are used both
to build the training dataset and to build live prediction rows in the API (see build_prediction_row).
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pandas as pd
import numpy as np
from src.features.draw_features import DrawFeatureState, add_draw_features
from src.db.database import attach_statsapi_xg
from src.config import DB_PATH, FEATURES_PATH, MATCHES_RAW_DIR, MATCHES_SUMMARY_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("build_features")

ROLLING_WINDOWS = [3, 5, 10]
EWMA_ALPHAS = [0.2, 0.4]

STAT_COLS = [
    "goals_for", "goals_against",
    "corners_for", "corners_against",
    "throws", "opponent_throws",
    "shots_for", "shots_against",
    "shots_ontarget_for", "shots_ontarget_against",
    "saves", "possession",
    "offsides_for", "offsides_against",
    "big_chances_for", "big_chances_against",
    "touches_in_opp_box", "touches_in_opp_box_against",
    "fouls_committed", "fouls_drawn",
    "cards_for", "cards_against",
    "xg_for", "xg_against",
    "opponent_elo", "opponent_mv",
    "pass_pct", "inacc_fwd_pass", "tackle_int",
]

# Strictly historical league priors used to fill cold-start NaNs (NO FUTURE LEAKAGE)
LEAGUE_PRIORS = {
    "corners_for": 5.15, "corners_against": 5.15,
    "throws": 16.45, "opponent_throws": 16.45,
    "shots_for": 13.0, "shots_against": 13.0,
    "shots_ontarget_for": 4.5, "shots_ontarget_against": 4.5,
    "saves": 3.1, "possession": 50.0,
    "goals_for": 1.45, "goals_against": 1.45,
    "offsides_for": 1.63, "offsides_against": 1.63,
    "big_chances_for": 1.8, "big_chances_against": 1.8,
    "touches_in_opp_box": 24.5, "touches_in_opp_box_against": 24.5,
    "fouls_committed": 10.5, "fouls_drawn": 10.5,
    "cards_for": 2.1, "cards_against": 2.1,
    "xg_for": 1.35, "xg_against": 1.35,
    "opponent_elo": 1500.0, "opponent_mv": 600.0,
    "pass_pct": 81.5, "inacc_fwd_pass": 72.0, "tackle_int": 25.25,
    "xg_diff_10": 0.0, "abs_xg_diff_10": 0.5,
}
# Priors for interaction features: per-team side (exp_home_* / exp_away_*) and match totals (exp_match_*)
EXP_SIDE_PRIORS = {"corners": 5.15, "shots": 13.0, "offsides": 1.63, "cards": 2.1, "xg": 1.35}
EXP_MATCH_PRIORS = {"corners": 10.3, "throws": 32.9, "shots": 26.0, "offsides": 3.26, "cards": 4.2, "xg": 2.70}

# Team strength (Elo + season-to-date table) parameters
ELO_INIT = 1500.0
ELO_NEWCOMER = 1430.0        # Promoted teams entering after the first season
ELO_K = 20.0
ELO_HOME_ADV = 60.0
ELO_SEASON_REGRESS = 0.20    # Pull ratings 20% towards the mean at each new season
PPG_PRIOR = 1.37             # League-average points per game
PRIOR_GAMES = 3.0            # Shrinkage strength for season-to-date ppg / goal difference

REFEREE_DEFAULTS = {"referee_avg_cards": 4.15, "referee_avg_fouls": 21.5, "referee_prior_matches": 0}
REFEREE_SHRINKAGE_MATCHES = 10.0


def prepare_matches(df: pd.DataFrame) -> pd.DataFrame:
    """Adds match_date / is_played, clears outcome labels of unplayed fixtures and sorts chronologically."""
    df = df.copy()
    if "match_date" not in df.columns:
        if "kickoff_millis" in df.columns:
            df["match_date"] = pd.to_datetime(df["kickoff_millis"], unit="ms")
        else:
            df["match_date"] = pd.to_datetime(df["kickoff_label"])

    df["is_played"] = df["home_score"].notna() & df["away_score"].notna()
    # Unplayed fixtures must never carry an outcome label (previously defaulted to "D")
    if "match_result" in df.columns:
        df["match_result"] = df["match_result"].astype(object)
        df.loc[~df["is_played"], "match_result"] = None
    if "over_2_5_goals" in df.columns:
        df.loc[~df["is_played"], "over_2_5_goals"] = np.nan

    sort_cols = ["match_date", "match_id"] if "match_id" in df.columns else ["match_date"]
    return df.sort_values(by=sort_cols, kind="mergesort").reset_index(drop=True)


def calculate_rest_days(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates rest days since previous match for both home and away teams."""
    df = prepare_matches(df)

    team_last_date: Dict[int, pd.Timestamp] = {}
    home_rest_days: List[float] = []
    away_rest_days: List[float] = []

    for _, row in df.iterrows():
        h_id = row["home_id"]
        a_id = row["away_id"]
        cur_date = row["match_date"]

        # Home team rest days
        if h_id in team_last_date:
            h_rest = (cur_date - team_last_date[h_id]).total_seconds() / 86400.0
        else:
            h_rest = 14.0  # Default season start / long rest
        home_rest_days.append(min(h_rest, 30.0))

        # Away team rest days
        if a_id in team_last_date:
            a_rest = (cur_date - team_last_date[a_id]).total_seconds() / 86400.0
        else:
            a_rest = 14.0
        away_rest_days.append(min(a_rest, 30.0))

        # A scheduled but unplayed fixture is not a previous match. In particular,
        # postponed fixtures must not reset rest days for later completed matches.
        if bool(row["is_played"]):
            team_last_date[h_id] = cur_date
            team_last_date[a_id] = cur_date

    df["home_rest_days"] = home_rest_days
    df["away_rest_days"] = away_rest_days
    return df


def _safe_float(val: Any, default: float) -> float:
    """Safe extraction of numeric stat values, preserving valid 0.0 while falling back to default on None/NaN."""
    if val is None or pd.isna(val):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def build_team_match_history(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms match dataframe into a long team-match perspective dataframe
    where each row represents one team's performance in a single match.
    Stats of unplayed fixtures are forced to NaN so they never enter rolling windows.
    Applies point-in-time opponent-strength normalization to shots, shots-on-target,
    xG, and box touches to eliminate Strength-of-Schedule (SoS) bias.
    """
    if "is_played" not in df.columns or "match_date" not in df.columns:
        df = prepare_matches(df)

    # Ensure pre-match point-in-time Elo ratings are attached for opponent adjustments
    if "elo_home" not in df.columns or "elo_away" not in df.columns:
        pre, _ = _run_strength(df)
        df = df.copy()
        for c in pre.columns:
            df[c] = pre[c].values

    records = []
    mv_map = get_team_market_values_map()
    for _, row in df.iterrows():
        m_id = row["match_id"]
        m_date = row["match_date"]
        gw = row.get("gameweek", 0)
        season = row.get("season")
        played = bool(row["is_played"])

        # Point-in-time opponent strength multipliers (league average Elo = 1500)
        h_elo = float(row.get("elo_home", 1500.0))
        a_elo = float(row.get("elo_away", 1500.0))
        mult_away = float(np.clip(np.exp((a_elo - 1500.0) / 600.0), 0.60, 1.80))
        mult_home = float(np.clip(np.exp((h_elo - 1500.0) / 600.0), 0.60, 1.80))

        # Home perspective: team is home, opponent is away (strength mult_away)
        h_s_for = _safe_float(row.get("home_total_scoring_att"), 0.0) * mult_away
        h_s_against = _safe_float(row.get("away_total_scoring_att"), 0.0) / mult_away
        h_sot_for = _safe_float(row.get("home_ontarget_scoring_att"), 0.0) * mult_away
        h_sot_against = _safe_float(row.get("away_ontarget_scoring_att"), 0.0) / mult_away
        h_bc_for = _safe_float(row.get("home_big_chance_created"), 1.8) * mult_away
        h_bc_against = _safe_float(row.get("away_big_chance_created"), 1.8) / mult_away
        h_touch_for = _safe_float(row.get("home_touches_in_opp_box"), 24.0) * mult_away
        h_touch_against = _safe_float(row.get("away_touches_in_opp_box"), 24.0) / mult_away
        h_xg_for = (
            float(row["statsapi_home_xg"]) * mult_away
            if played and pd.notnull(row.get("statsapi_home_xg"))
            else np.nan
        )
        h_xg_against = (
            float(row["statsapi_away_xg"]) / mult_away
            if played and pd.notnull(row.get("statsapi_away_xg"))
            else np.nan
        )

        h_tot_p = _safe_float(row.get("home_total_pass"), 0.0)
        h_acc_p = _safe_float(row.get("home_accurate_pass"), 0.0)
        h_pass_pct = (h_acc_p / h_tot_p * 100.0) if h_tot_p > 0 else 81.5
        h_fwd_p = _safe_float(row.get("home_total_fwd_zone_pass"), 0.0)
        h_acc_fwd_p = _safe_float(row.get("home_accurate_fwd_zone_pass"), 0.0)
        h_inacc_fwd_p = max(0.0, h_fwd_p - h_acc_fwd_p) if h_fwd_p > 0 else 72.0
        h_tkl_int = _safe_float(row.get("home_total_tackle"), 16.0) + _safe_float(row.get("home_interception"), 9.25)

        records.append({
            "match_id": m_id,
            "match_date": m_date,
            "gameweek": gw,
            "season": season,
            "is_played": played,
            "team_id": row["home_id"],
            "team_name": row["home_name"],
            "opponent_id": row["away_id"],
            "is_home": 1,
            # Targets & metrics for this team
            "goals_for": row["home_score"],
            "goals_against": row["away_score"],
            "corners_for": _safe_float(row.get("home_won_corners"), 0.0),
            "corners_against": _safe_float(row.get("away_won_corners"), 0.0),
            "throws": _safe_float(row.get("home_total_throws"), 0.0),
            "opponent_throws": _safe_float(row.get("away_total_throws"), 0.0),
            "shots_for": h_s_for,
            "shots_against": h_s_against,
            "shots_ontarget_for": h_sot_for,
            "shots_ontarget_against": h_sot_against,
            "saves": _safe_float(row.get("home_saves"), 0.0),
            "possession": _safe_float(row.get("home_possession_percentage"), 50.0),
            "passes": h_tot_p,
            "pass_pct": h_pass_pct,
            "inacc_fwd_pass": h_inacc_fwd_p,
            "tackle_int": h_tkl_int,
            "fouls_committed": _safe_float(row.get("home_fk_foul_lost"), 10.0),
            "fouls_drawn": _safe_float(row.get("home_fk_foul_won"), 10.0),
            "offsides_for": _safe_float(row.get("home_total_offside"), 1.6),
            "offsides_against": _safe_float(row.get("away_total_offside"), 1.6),
            "big_chances_for": h_bc_for,
            "big_chances_against": h_bc_against,
            "touches_in_opp_box": h_touch_for,
            "touches_in_opp_box_against": h_touch_against,
            "cards_for": _safe_float(row.get("home_total_yel_card"), 0.0) + _safe_float(row.get("home_total_red_card"), 0.0),
            "cards_against": _safe_float(row.get("away_total_yel_card"), 0.0) + _safe_float(row.get("away_total_red_card"), 0.0),
            "xg_for": h_xg_for,
            "xg_against": h_xg_against,
            "opponent_elo": a_elo,
            "opponent_mv": float(mv_map.get((int(row["away_id"]), str(season)), mv_map.get(int(row["away_id"]), 600.0))),
        })

        # Away perspective: team is away, opponent is home (strength mult_home)
        a_s_for = _safe_float(row.get("away_total_scoring_att"), 0.0) * mult_home
        a_s_against = _safe_float(row.get("home_total_scoring_att"), 0.0) / mult_home
        a_sot_for = _safe_float(row.get("away_ontarget_scoring_att"), 0.0) * mult_home
        a_sot_against = _safe_float(row.get("home_ontarget_scoring_att"), 0.0) / mult_home
        a_bc_for = _safe_float(row.get("away_big_chance_created"), 1.8) * mult_home
        a_bc_against = _safe_float(row.get("home_big_chance_created"), 1.8) / mult_home
        a_touch_for = _safe_float(row.get("away_touches_in_opp_box"), 24.0) * mult_home
        a_touch_against = _safe_float(row.get("home_touches_in_opp_box"), 24.0) / mult_home
        a_xg_for = (
            float(row["statsapi_away_xg"]) * mult_home
            if played and pd.notnull(row.get("statsapi_away_xg"))
            else np.nan
        )
        a_xg_against = (
            float(row["statsapi_home_xg"]) / mult_home
            if played and pd.notnull(row.get("statsapi_home_xg"))
            else np.nan
        )

        a_tot_p = _safe_float(row.get("away_total_pass"), 0.0)
        a_acc_p = _safe_float(row.get("away_accurate_pass"), 0.0)
        a_pass_pct = (a_acc_p / a_tot_p * 100.0) if a_tot_p > 0 else 81.5
        a_fwd_p = _safe_float(row.get("away_total_fwd_zone_pass"), 0.0)
        a_acc_fwd_p = _safe_float(row.get("away_accurate_fwd_zone_pass"), 0.0)
        a_inacc_fwd_p = max(0.0, a_fwd_p - a_acc_fwd_p) if a_fwd_p > 0 else 72.0
        a_tkl_int = _safe_float(row.get("away_total_tackle"), 16.0) + _safe_float(row.get("away_interception"), 9.25)

        records.append({
            "match_id": m_id,
            "match_date": m_date,
            "gameweek": gw,
            "season": season,
            "is_played": played,
            "team_id": row["away_id"],
            "team_name": row["away_name"],
            "opponent_id": row["home_id"],
            "is_home": 0,
            # Targets & metrics for this team
            "goals_for": row["away_score"],
            "goals_against": row["home_score"],
            "corners_for": _safe_float(row.get("away_won_corners"), 0.0),
            "corners_against": _safe_float(row.get("home_won_corners"), 0.0),
            "throws": _safe_float(row.get("away_total_throws"), 0.0),
            "opponent_throws": _safe_float(row.get("home_total_throws"), 0.0),
            "shots_for": a_s_for,
            "shots_against": a_s_against,
            "shots_ontarget_for": a_sot_for,
            "shots_ontarget_against": a_sot_against,
            "saves": _safe_float(row.get("away_saves"), 0.0),
            "possession": _safe_float(row.get("away_possession_percentage"), 50.0),
            "passes": a_tot_p,
            "pass_pct": a_pass_pct,
            "inacc_fwd_pass": a_inacc_fwd_p,
            "tackle_int": a_tkl_int,
            "fouls_committed": _safe_float(row.get("away_fk_foul_lost"), 10.0),
            "fouls_drawn": _safe_float(row.get("away_fk_foul_won"), 10.0),
            "offsides_for": _safe_float(row.get("away_total_offside"), 1.6),
            "offsides_against": _safe_float(row.get("home_total_offside"), 1.6),
            "big_chances_for": a_bc_for,
            "big_chances_against": a_bc_against,
            "touches_in_opp_box": a_touch_for,
            "touches_in_opp_box_against": a_touch_against,
            "cards_for": _safe_float(row.get("away_total_yel_card"), 0.0) + _safe_float(row.get("away_total_red_card"), 0.0),
            "cards_against": _safe_float(row.get("home_total_yel_card"), 0.0) + _safe_float(row.get("home_total_red_card"), 0.0),
            "xg_for": a_xg_for,
            "xg_against": a_xg_against,
            "opponent_elo": h_elo,
            "opponent_mv": float(mv_map.get((int(row["home_id"]), str(season)), mv_map.get(int(row["home_id"]), 600.0))),
        })

    long_df = pd.DataFrame(records)
    metric_cols = [c for c in STAT_COLS + ["passes"] if c in long_df.columns]
    long_df.loc[~long_df["is_played"], metric_cols] = np.nan
    long_df = long_df.sort_values(by=["team_id", "match_date", "match_id"], kind="mergesort").reset_index(drop=True)
    # Detect gap years (> 200 days between matches for the same team, e.g. relegation to Championship & re-promotion)
    prev_dates = long_df.groupby("team_id")["match_date"].shift(1)
    gap_days = (long_df["match_date"] - prev_dates).dt.total_seconds() / 86400.0
    long_df["stint_id"] = (gap_days > 200.0).fillna(False).cumsum()
    return long_df


def _alpha_str(a: float) -> str:
    return str(a).replace(".", "")


def _lagged_team_state(
    long_df: pd.DataFrame, col: str, played: pd.Series, fn: Callable[[pd.Series], pd.Series],
    reset_each_season: bool = False,
    group_by_venue: bool = False,
) -> pd.Series:
    """
    For every team-match row returns the statistic computed over the team's PLAYED matches strictly
    before that row. Unplayed fixtures inherit the state after the team's latest played match.
    Stints separated by gap-years (> 200 days absence from PL) are cleanly partitioned.
    When group_by_venue=True, partitions matches by is_home so home and away form are tracked separately.
    """
    out = pd.Series(np.nan, index=long_df.index)
    if reset_each_season and "season" in long_df.columns:
        group_cols = ["team_id", "season"]
    elif "stint_id" in long_df.columns:
        group_cols = ["team_id", "stint_id"]
    else:
        group_cols = ["team_id"]
    if group_by_venue and "is_home" in long_df.columns:
        group_cols = group_cols + ["is_home"]

    for _, idx in long_df.groupby(group_cols, sort=False, dropna=False).groups.items():
        s = long_df.loc[idx, col]
        s_played = s[played.loc[idx]].dropna()
        if s_played.empty:
            continue
        state_after = fn(s_played).reindex(idx).ffill()  # state including each row
        out.loc[idx] = state_after.shift(1).values       # strictly before each row
    return out


def compute_pre_match_features(long_df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes strictly lagging rolling statistics (mean, EWMA) for each team.
    Using a one-step lag guarantees NO DATA LEAKAGE from current match.
    Also computes venue-specific form (home vs away) with Bayesian shrinkage.
    """
    long_df = long_df.sort_values(by=["team_id", "match_date", "match_id"], kind="mergesort").reset_index(drop=True)
    played = long_df["is_played"].astype(bool) if "is_played" in long_df.columns else long_df["goals_for"].notna()

    new_cols: Dict[str, pd.Series] = {}
    for col in STAT_COLS:
        # Rolling means
        for w in ROLLING_WINDOWS:
            new_cols[f"{col}_roll_{w}"] = _lagged_team_state(
                long_df, col, played, lambda s, w=w: s.rolling(w, min_periods=1).mean(),
                reset_each_season=False)
        # EWMA
        for a in EWMA_ALPHAS:
            new_cols[f"{col}_ewma_{_alpha_str(a)}"] = _lagged_team_state(
                long_df, col, played, lambda s, a=a: s.ewm(alpha=a, min_periods=1).mean(),
                reset_each_season=False)

    # Venue-specific form features with Bayesian sample-size shrinkage
    venue_n = _lagged_team_state(
        long_df, "goals_for", played, lambda s: s.expanding().count(),
        group_by_venue=True).fillna(0.0)
    lam = (venue_n / (venue_n + 4.0)).astype(float)

    # 1. Venue xG (EWMA 0.2)
    raw_v_xg_for = _lagged_team_state(
        long_df, "xg_for", played, lambda s: s.ewm(alpha=0.2, min_periods=1).mean(),
        group_by_venue=True)
    new_cols["venue_xg_for_ewma_02"] = lam * raw_v_xg_for.fillna(new_cols["xg_for_ewma_02"]) + (1.0 - lam) * new_cols["xg_for_ewma_02"]

    raw_v_xg_against = _lagged_team_state(
        long_df, "xg_against", played, lambda s: s.ewm(alpha=0.2, min_periods=1).mean(),
        group_by_venue=True)
    new_cols["venue_xg_against_ewma_02"] = lam * raw_v_xg_against.fillna(new_cols["xg_against_ewma_02"]) + (1.0 - lam) * new_cols["xg_against_ewma_02"]

    # 2. Venue Goals (Roll 5)
    raw_v_gf = _lagged_team_state(
        long_df, "goals_for", played, lambda s: s.rolling(5, min_periods=1).mean(),
        group_by_venue=True)
    new_cols["venue_goals_for_roll_5"] = lam * raw_v_gf.fillna(new_cols["goals_for_roll_5"]) + (1.0 - lam) * new_cols["goals_for_roll_5"]

    raw_v_ga = _lagged_team_state(
        long_df, "goals_against", played, lambda s: s.rolling(5, min_periods=1).mean(),
        group_by_venue=True)
    new_cols["venue_goals_against_roll_5"] = lam * raw_v_ga.fillna(new_cols["goals_against_roll_5"]) + (1.0 - lam) * new_cols["goals_against_roll_5"]

    # 3. Venue Shots on Target (Roll 5)
    raw_v_sot_for = _lagged_team_state(
        long_df, "shots_ontarget_for", played, lambda s: s.rolling(5, min_periods=1).mean(),
        group_by_venue=True)
    new_cols["venue_shots_ontarget_for_roll_5"] = lam * raw_v_sot_for.fillna(new_cols["shots_ontarget_for_roll_5"]) + (1.0 - lam) * new_cols["shots_ontarget_for_roll_5"]

    raw_v_sot_against = _lagged_team_state(
        long_df, "shots_ontarget_against", played, lambda s: s.rolling(5, min_periods=1).mean(),
        group_by_venue=True)
    new_cols["venue_shots_ontarget_against_roll_5"] = lam * raw_v_sot_against.fillna(new_cols["shots_ontarget_against_roll_5"]) + (1.0 - lam) * new_cols["shots_ontarget_against_roll_5"]

    return pd.concat([
        long_df,
        pd.DataFrame(new_cols, index=long_df.index),
    ], axis=1)


def compute_team_states(long_df: pd.DataFrame, until: Optional[pd.Timestamp] = None) -> pd.DataFrame:
    """
    Current form state of each team AFTER its latest played match (optionally up to `until`).
    Same definitions as compute_pre_match_features, so it is the exact feature vector of the team's next match.
    Only matches from the team's latest Premier League stint are considered (matching training).
    """
    played = long_df["is_played"].astype(bool) if "is_played" in long_df.columns else long_df["goals_for"].notna()
    d = long_df[played]
    if until is not None:
        d = d[d["match_date"] <= until]

    rows: Dict[int, Dict[str, Any]] = {}
    for tid, g in d.sort_values(["match_date", "match_id"], kind="mergesort").groupby("team_id"):
        if "stint_id" in g.columns:
            g = g[g["stint_id"] == g["stint_id"].max()]
        rec: Dict[str, Any] = {"last_match_date": g["match_date"].max()}
        # Overall form
        for col in STAT_COLS:
            state = g
            s = state[col].dropna()
            for w in ROLLING_WINDOWS:
                rec[f"{col}_roll_{w}"] = float(s.tail(w).mean()) if len(s) else np.nan
            for a in EWMA_ALPHAS:
                rec[f"{col}_ewma_{_alpha_str(a)}"] = float(s.ewm(alpha=a, min_periods=1).mean().iloc[-1]) if len(s) else np.nan

        # Venue-specific form (home vs away)
        g_h = g[g["is_home"] == 1]
        g_a = g[g["is_home"] == 0]
        n_h = len(g_h["goals_for"].dropna())
        n_a = len(g_a["goals_for"].dropna())
        lam_h = n_h / (n_h + 4.0)
        lam_a = n_a / (n_a + 4.0)

        base_xg_f = rec.get("xg_for_ewma_02", np.nan)
        base_xg_a = rec.get("xg_against_ewma_02", np.nan)
        base_gf = rec.get("goals_for_roll_5", np.nan)
        base_ga = rec.get("goals_against_roll_5", np.nan)
        base_sot_f = rec.get("shots_ontarget_for_roll_5", np.nan)
        base_sot_a = rec.get("shots_ontarget_against_roll_5", np.nan)

        # 1. Home venue
        s_xg_h = g_h["xg_for"].dropna()
        raw_xg_h = float(s_xg_h.ewm(alpha=0.2, min_periods=1).mean().iloc[-1]) if len(s_xg_h) else base_xg_f
        rec["home_venue_xg_for_ewma_02"] = lam_h * raw_xg_h + (1.0 - lam_h) * base_xg_f

        s_xga_h = g_h["xg_against"].dropna()
        raw_xga_h = float(s_xga_h.ewm(alpha=0.2, min_periods=1).mean().iloc[-1]) if len(s_xga_h) else base_xg_a
        rec["home_venue_xg_against_ewma_02"] = lam_h * raw_xga_h + (1.0 - lam_h) * base_xg_a

        s_gf_h = g_h["goals_for"].dropna()
        raw_gf_h = float(s_gf_h.tail(5).mean()) if len(s_gf_h) else base_gf
        rec["home_venue_goals_for_roll_5"] = lam_h * raw_gf_h + (1.0 - lam_h) * base_gf

        s_ga_h = g_h["goals_against"].dropna()
        raw_ga_h = float(s_ga_h.tail(5).mean()) if len(s_ga_h) else base_ga
        rec["home_venue_goals_against_roll_5"] = lam_h * raw_ga_h + (1.0 - lam_h) * base_ga

        s_sot_h = g_h["shots_ontarget_for"].dropna()
        raw_sot_h = float(s_sot_h.tail(5).mean()) if len(s_sot_h) else base_sot_f
        rec["home_venue_shots_ontarget_for_roll_5"] = lam_h * raw_sot_h + (1.0 - lam_h) * base_sot_f

        s_sota_h = g_h["shots_ontarget_against"].dropna()
        raw_sota_h = float(s_sota_h.tail(5).mean()) if len(s_sota_h) else base_sot_a
        rec["home_venue_shots_ontarget_against_roll_5"] = lam_h * raw_sota_h + (1.0 - lam_h) * base_sot_a

        # 2. Away venue
        s_xg_a = g_a["xg_for"].dropna()
        raw_xg_a = float(s_xg_a.ewm(alpha=0.2, min_periods=1).mean().iloc[-1]) if len(s_xg_a) else base_xg_f
        rec["away_venue_xg_for_ewma_02"] = lam_a * raw_xg_a + (1.0 - lam_a) * base_xg_f

        s_xga_a = g_a["xg_against"].dropna()
        raw_xga_a = float(s_xga_a.ewm(alpha=0.2, min_periods=1).mean().iloc[-1]) if len(s_xga_a) else base_xg_a
        rec["away_venue_xg_against_ewma_02"] = lam_a * raw_xga_a + (1.0 - lam_a) * base_xg_a

        s_gf_a = g_a["goals_for"].dropna()
        raw_gf_a = float(s_gf_a.tail(5).mean()) if len(s_gf_a) else base_gf
        rec["away_venue_goals_for_roll_5"] = lam_a * raw_gf_a + (1.0 - lam_a) * base_gf

        s_ga_a = g_a["goals_against"].dropna()
        raw_ga_a = float(s_ga_a.tail(5).mean()) if len(s_ga_a) else base_ga
        rec["away_venue_goals_against_roll_5"] = lam_a * raw_ga_a + (1.0 - lam_a) * base_ga

        s_sot_a = g_a["shots_ontarget_for"].dropna()
        raw_sot_a = float(s_sot_a.tail(5).mean()) if len(s_sot_a) else base_sot_f
        rec["away_venue_shots_ontarget_for_roll_5"] = lam_a * raw_sot_a + (1.0 - lam_a) * base_sot_f

        s_sota_a = g_a["shots_ontarget_against"].dropna()
        raw_sota_a = float(s_sota_a.tail(5).mean()) if len(s_sota_a) else base_sot_a
        rec["away_venue_shots_ontarget_against_roll_5"] = lam_a * raw_sota_a + (1.0 - lam_a) * base_sot_a

        rows[int(tid)] = rec
    return pd.DataFrame.from_dict(rows, orient="index")


_XI_MATCH_CACHE: Optional[Tuple[Dict[int, Dict[int, List[Tuple[int, str]]]], Dict[int, Dict[int, List[Tuple[int, str, float, float, float]]]]]] = None


def _get_xi_match_lookup():
    """Pre-indexes match starters and single-match player scores once for fast O(1) chronological replay."""
    global _XI_MATCH_CACHE
    if _XI_MATCH_CACHE is not None:
        return _XI_MATCH_CACHE
    from collections import defaultdict
    from src.analytics.player_ratings import (
        get_all_player_logs,
        get_all_players_registry,
        get_match_bookings_map,
        calculate_single_match_score,
    )
    logs_by_player = get_all_player_logs()
    reg = get_all_players_registry()
    bmap = get_match_bookings_map()

    match_starters: Dict[int, Dict[int, List[Tuple[int, str]]]] = defaultdict(lambda: defaultdict(list))
    match_scores: Dict[int, Dict[int, List[Tuple[int, str, float, float, float]]]] = defaultdict(lambda: defaultdict(list))

    for pid_str, plogs in logs_by_player.items():
        try:
            pid = int(pid_str)
        except (ValueError, TypeError):
            continue
        pos = str(reg.get(pid, {}).get("position", "M"))
        for l in plogs:
            mid = int(l.get("match_id") or 0)
            tid = int(l.get("team_id") or 0)
            if not mid or not tid:
                continue
            if l.get("started"):
                match_starters[mid][tid].append((pid, pos))
            sc = calculate_single_match_score(l, pos, bmap, pid)
            if sc is not None:
                match_scores[mid][tid].append((pid, pos, float(sc["overall"]), float(sc["attack"]), float(sc["defense"])))

    _XI_MATCH_CACHE = (match_starters, match_scores)
    return _XI_MATCH_CACHE


_XI_RECENT_WEIGHTS_5 = (0.10, 0.15, 0.20, 0.25, 0.30)


def _compute_pre_match_player_rating(
    player_history: Dict[int, List[Tuple[str, float, float, float]]],
    pid: int,
    s_str: str,
) -> Tuple[float, float, float]:
    hist = player_history.get(pid)
    if not hist:
        return (6.0, 6.0, 6.0)
    s_hist = [h for h in hist if h[0] == s_str]
    if len(s_hist) < 3:
        s_hist = hist
    n_s = len(s_hist)
    s_ov = sum(h[1] for h in s_hist) / n_s
    s_at = sum(h[2] for h in s_hist) / n_s
    s_df = sum(h[3] for h in s_hist) / n_s
    rec = hist[-5:]
    n_r = len(rec)
    if n_r == 5:
        w = _XI_RECENT_WEIGHTS_5
    else:
        denom = n_r * (n_r + 1) / 2.0
        w = tuple((i + 1) / denom for i in range(n_r))
    r_ov = sum(wi * h[1] for wi, h in zip(w, rec))
    r_at = sum(wi * h[2] for wi, h in zip(w, rec))
    r_df = sum(wi * h[3] for wi, h in zip(w, rec))
    return (0.70 * r_ov + 0.30 * s_ov, 0.70 * r_at + 0.30 * s_at, 0.70 * r_df + 0.30 * s_df)


def _aggregate_xi_ratings(
    starters: List[Tuple[int, str]],
    player_history: Dict[int, List[Tuple[str, float, float, float]]],
    s_str: str,
) -> Tuple[float, float, float]:
    p_rats = [(pos, *_compute_pre_match_player_rating(player_history, pid, s_str)) for pid, pos in starters]
    ov = float(np.mean([x[1] for x in p_rats]))
    att_p = [x[2] for x in p_rats if x[0].upper() in ("F", "M", "FW", "MID", "AM", "RW", "LW", "ST", "CF")]
    def_p = [x[3] for x in p_rats if x[0].upper() in ("D", "G", "GK", "DEF", "CB", "LB", "RB")]
    att = float(np.mean(att_p)) if att_p else ov
    df_r = float(np.mean(def_p)) if def_p else ov
    return (ov, att, df_r)


def load_official_match_starters(match_id: Optional[int]) -> Dict[int, List[Tuple[int, str]]]:
    """Reads official starting XIs (team_id -> [(player_id, position), ...]) from cached match details JSON."""
    if not match_id:
        return {}
    path = MATCHES_RAW_DIR / f"{int(match_id)}_details.json"
    if not path.exists():
        return {}
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    teams_info = d.get("teams") or []
    result: Dict[int, List[Tuple[int, str]]] = {}
    for idx, tl in enumerate(d.get("teamLists") or []):
        if not tl or not isinstance(tl, dict):
            continue
        t_id = tl.get("teamId")
        if not t_id and idx < len(teams_info):
            t_id = (teams_info[idx].get("team") or {}).get("id")
        if not t_id:
            continue
        lineup = tl.get("lineup") or []
        if len(lineup) >= 7:
            starters = [
                (int(p["id"]), str(p.get("matchPosition") or "M"))
                for p in lineup
                if p.get("id") is not None
            ]
            if len(starters) >= 7:
                result[int(t_id)] = starters
    return result


def _run_strength(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Sequential Elo + season-to-date table + point-in-time Starting XI dynamic player ratings.
    Returns strictly pre-match strength features per match and the final state for live predictions.
    """
    df = df if "is_played" in df.columns else prepare_matches(df)
    has_season = "season" in df.columns
    first_season = df["season"].iloc[0] if has_season and len(df) else None

    match_starters, match_scores = _get_xi_match_lookup()
    player_history: Dict[int, List[Tuple[str, float, float, float]]] = {}
    team_last_xi: Dict[int, Tuple[float, float, float]] = {}
    team_last_xi_starters: Dict[int, List[Tuple[int, str]]] = {}

    elo: Dict[int, float] = {}
    elo_home_venue: Dict[int, float] = {}
    elo_away_venue: Dict[int, float] = {}
    table: Dict[int, List[float]] = {}  # team -> [points, goal_diff, matches] in current season
    all_time_played: Dict[int, int] = {}
    current_season = first_season
    pre: List[Dict[str, float]] = []

    def season_form(t: int) -> Tuple[float, float]:
        pts, gd, n = table.get(t, [0.0, 0.0, 0.0])
        return (pts + PPG_PRIOR * PRIOR_GAMES) / (n + PRIOR_GAMES), gd / (n + PRIOR_GAMES)

    teams_in_prev_season: set[int] = set()
    for _, row in df.iterrows():
        season = row["season"] if has_season else None
        s_str = str(season or "all")
        if season != current_season:
            teams_in_prev_season = set(table.keys())
            for t in elo:
                elo[t] = (1 - ELO_SEASON_REGRESS) * elo[t] + ELO_SEASON_REGRESS * ELO_INIT
            for t in elo_home_venue:
                elo_home_venue[t] = (1 - ELO_SEASON_REGRESS) * elo_home_venue[t] + ELO_SEASON_REGRESS * ELO_INIT
            for t in elo_away_venue:
                elo_away_venue[t] = (1 - ELO_SEASON_REGRESS) * elo_away_venue[t] + ELO_SEASON_REGRESS * ELO_INIT
            table = {}
            current_season = season

        h, a = int(row["home_id"]), int(row["away_id"])
        mid = int(row["match_id"]) if "match_id" in row and pd.notnull(row["match_id"]) else 0
        for t in (h, a):
            is_new_entrant = (t not in elo) or (current_season != first_season and t not in teams_in_prev_season and t not in table)
            if is_new_entrant:
                elo[t] = ELO_INIT if season == first_season else ELO_NEWCOMER
                elo_home_venue[t] = ELO_INIT if season == first_season else ELO_NEWCOMER
                elo_away_venue[t] = ELO_INIT if season == first_season else ELO_NEWCOMER

        # Compute pre-match Starting XI ratings for home and away
        xi_vals: Dict[int, Tuple[float, float, float]] = {}
        official_unplayed = load_official_match_starters(mid) if (mid and not row["is_played"]) else {}
        for tid in (h, a):
            starters = match_starters.get(mid, {}).get(tid, []) if mid else []
            if not starters and tid in official_unplayed:
                starters = official_unplayed[tid]
            if len(starters) >= 7:
                ov, att, df_r = _aggregate_xi_ratings(starters, player_history, s_str)
                if row["is_played"]:
                    team_last_xi[tid] = (ov, att, df_r)
                    team_last_xi_starters[tid] = list(starters)
                xi_vals[tid] = (ov, att, df_r)
            else:
                xi_vals[tid] = team_last_xi.get(tid, (6.15, 6.15, 6.15))

        h_xi_ov, h_xi_att, h_xi_def = xi_vals[h]
        a_xi_ov, a_xi_att, a_xi_def = xi_vals[a]

        h_ppg, h_gd = season_form(h)
        a_ppg, a_gd = season_form(a)
        pre.append({
            "elo_home": elo[h], "elo_away": elo[a], "elo_diff": elo[h] - elo[a],
            "elo_venue_home": elo_home_venue[h], "elo_venue_away": elo_away_venue[a],
            "elo_venue_diff": elo_home_venue[h] - elo_away_venue[a],
            "ppg_home": h_ppg, "ppg_away": a_ppg, "ppg_diff": h_ppg - a_ppg,
            "gdpg_home": h_gd, "gdpg_away": a_gd, "gdpg_diff": h_gd - a_gd,
            "home_xi_rating": h_xi_ov,
            "away_xi_rating": a_xi_ov,
            "xi_rating_diff": h_xi_ov - a_xi_ov,
            "home_xi_att_vs_away_def": h_xi_att - a_xi_def,
            "away_xi_att_vs_home_def": a_xi_att - h_xi_def,
            "xi_att_vs_def_diff": (h_xi_att - a_xi_def) - (a_xi_att - h_xi_def),
        })

        if not row["is_played"]:
            continue

        # Update player rating histories AFTER pre-match features are recorded
        if mid:
            for tid in (h, a):
                for pid, _pos, sc_ov, sc_at, sc_df in match_scores.get(mid, {}).get(tid, []):
                    player_history.setdefault(pid, []).append((s_str, sc_ov, sc_at, sc_df))

        hs, as_ = float(row["home_score"]), float(row["away_score"])
        # Overall Elo update
        exp_h = 1.0 / (1.0 + 10 ** ((elo[a] - (elo[h] + ELO_HOME_ADV)) / 400.0))
        s_h = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
        margin = abs(hs - as_)
        mult = np.log(margin + 1.0) + 1.0 if margin > 0 else 1.0
        delta = ELO_K * mult * (s_h - exp_h)
        elo[h] += delta
        elo[a] -= delta

        # Venue-specific Elo update
        exp_h_v = 1.0 / (1.0 + 10 ** ((elo_away_venue[a] - (elo_home_venue[h] + ELO_HOME_ADV)) / 400.0))
        delta_v = ELO_K * mult * (s_h - exp_h_v)
        elo_home_venue[h] += delta_v
        elo_away_venue[a] -= delta_v

        h_pts = 3.0 if hs > as_ else (1.0 if hs == as_ else 0.0)
        a_pts = 3.0 if as_ > hs else (1.0 if hs == as_ else 0.0)
        for t, pts, gd in ((h, h_pts, hs - as_), (a, a_pts, as_ - hs)):
            rec = table.setdefault(t, [0.0, 0.0, 0.0])
            rec[0] += pts
            rec[1] += gd
            rec[2] += 1.0
        all_time_played[h] = all_time_played.get(h, 0) + 1
        all_time_played[a] = all_time_played.get(a, 0) + 1

    state = {
        "elo": dict(elo),
        "elo_home_venue": dict(elo_home_venue),
        "elo_away_venue": dict(elo_away_venue),
        "table": {k: list(v) for k, v in table.items()},
        "all_time_played": dict(all_time_played),
        "xi_ratings": dict(team_last_xi),
        "last_xi_starters": {k: list(v) for k, v in team_last_xi_starters.items()},
        "player_history": {k: list(v) for k, v in player_history.items()},
        "season": current_season,
    }
    return pd.DataFrame(pre, index=df.index), state


def compute_strength_features(df: pd.DataFrame) -> pd.DataFrame:
    """Adds strictly pre-match Elo and season-to-date points / goal-difference features."""
    df = df.copy()
    pre, _ = _run_strength(df)
    for c in pre.columns:
        df[c] = pre[c].values
    return df


def compute_strength_state(df: pd.DataFrame, until: Optional[pd.Timestamp] = None) -> Dict[str, Any]:
    """Strength state after all played matches (optionally up to `until`)."""
    d = df if "is_played" in df.columns else prepare_matches(df)
    if until is not None:
        d = d[d["match_date"] <= until]
    d = d[d["is_played"]]
    _, state = _run_strength(d)
    return state


def advance_strength_state_to_season(
    state: Dict[str, Any], target_season: Optional[str]
) -> Dict[str, Any]:
    """Apply training's Elo regression and table reset before a new season starts."""
    if not target_season or not state.get("season"):
        return state
    try:
        current_year = int(str(state["season"]).split("_")[0])
        target_year = int(str(target_season).split("_")[0])
    except (TypeError, ValueError):
        return state
    if target_year <= current_year:
        return state

    advanced = {
        **state,
        "elo": dict(state.get("elo", {})),
        "elo_home_venue": dict(state.get("elo_home_venue", {})),
        "elo_away_venue": dict(state.get("elo_away_venue", {})),
        "all_time_played": dict(state.get("all_time_played", {})),
        "xi_ratings": dict(state.get("xi_ratings", {})),
        "last_xi_starters": dict(state.get("last_xi_starters", {})),
        "player_history": dict(state.get("player_history", {})),
        "table": {},
    }
    for _ in range(target_year - current_year):
        advanced["elo"] = {
            team_id: (1.0 - ELO_SEASON_REGRESS) * rating + ELO_SEASON_REGRESS * ELO_INIT
            for team_id, rating in advanced["elo"].items()
        }
        advanced["elo_home_venue"] = {
            team_id: (1.0 - ELO_SEASON_REGRESS) * rating + ELO_SEASON_REGRESS * ELO_INIT
            for team_id, rating in advanced["elo_home_venue"].items()
        }
        advanced["elo_away_venue"] = {
            team_id: (1.0 - ELO_SEASON_REGRESS) * rating + ELO_SEASON_REGRESS * ELO_INIT
            for team_id, rating in advanced["elo_away_venue"].items()
        }
    advanced["season"] = str(target_season)
    return advanced


def _team_strength(state: Dict[str, Any], team_id: int, is_home: bool = True) -> Dict[str, float]:
    elo = state.get("elo", {}).get(int(team_id), ELO_NEWCOMER)
    venue_dict = state.get("elo_home_venue" if is_home else "elo_away_venue", {})
    elo_venue = venue_dict.get(int(team_id), ELO_NEWCOMER)
    pts, gd, n = state.get("table", {}).get(int(team_id), [0.0, 0.0, 0.0])
    xi_ov, xi_att, xi_def = state.get("xi_ratings", {}).get(int(team_id), (6.15, 6.15, 6.15))
    return {
        "elo": float(elo),
        "elo_venue": float(elo_venue),
        "ppg": (pts + PPG_PRIOR * PRIOR_GAMES) / (n + PRIOR_GAMES),
        "gdpg": gd / (n + PRIOR_GAMES),
        "xi_rating": float(xi_ov),
        "xi_attack": float(xi_att),
        "xi_defense": float(xi_def),
    }


def get_team_market_values_map() -> Dict[Any, float]:
    """Returns (team_id, season) -> market_value_eur in Millions, plus fallback team_id -> market_value_eur."""
    mv_map = {}
    try:
        db_file = DB_PATH
        if db_file.exists():
            con = sqlite3.connect(db_file)
            cur = con.cursor()
            cur.execute("SELECT team_id, season, market_value_eur FROM team_market_values ORDER BY season ASC")
            for r in cur.fetchall():
                t_id = int(r[0])
                s = str(r[1])
                val = float(r[2])
                mv_map[(t_id, s)] = val
                mv_map[t_id] = val
            con.close()
    except Exception as e:
        logger.warning(f"Could not load team market values: {e}")
    return mv_map


def compute_market_value_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes squad market value features, Bayesian dynamic sample-size prior decay weights,
    and newcomer/promoted team status flags.
    """
    df = df.copy()
    mv_map = get_team_market_values_map()
    default_median_mv = 600.0

    sort_cols = [c for c in ["match_date", "match_id"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(by=sort_cols, kind="mergesort").reset_index(drop=True)

    season_played_counts: Dict[str, Dict[int, int]] = {}
    all_time_played: Dict[int, int] = {}

    home_mv_list = []
    away_mv_list = []
    log_ratio_list = []
    eff_log_ratio_list = []
    mv_diff_list = []
    prior_w_h_list = []
    prior_w_a_list = []
    promoted_h_list = []
    promoted_a_list = []

    for _, row in df.iterrows():
        s = str(row.get("season", "all"))
        if s not in season_played_counts:
            season_played_counts[s] = {}

        h_id = int(row["home_id"])
        a_id = int(row["away_id"])

        n_h = season_played_counts[s].get(h_id, 0)
        n_a = season_played_counts[s].get(a_id, 0)

        mv_h = mv_map.get((h_id, s), mv_map.get(h_id, default_median_mv))
        mv_a = mv_map.get((a_id, s), mv_map.get(a_id, default_median_mv))

        # Bayesian prior weight: w = K / (K + N), where K = 8 matches half-life
        w_h = 8.0 / (8.0 + n_h)
        w_a = 8.0 / (8.0 + n_a)
        w_match = np.sqrt(w_h * w_a)

        log_ratio = float(np.log(max(mv_h, 10.0) / max(mv_a, 10.0)))
        eff_log_ratio = float(log_ratio * w_match)
        diff = float(mv_h - mv_a)

        tot_h = all_time_played.get(h_id, 0)
        tot_a = all_time_played.get(a_id, 0)
        is_prom_h = 1.0 if (n_h < 10 and tot_h < 10) else 0.0
        is_prom_a = 1.0 if (n_a < 10 and tot_a < 10) else 0.0

        home_mv_list.append(mv_h)
        away_mv_list.append(mv_a)
        log_ratio_list.append(log_ratio)
        eff_log_ratio_list.append(eff_log_ratio)
        mv_diff_list.append(diff)
        prior_w_h_list.append(w_h)
        prior_w_a_list.append(w_a)
        promoted_h_list.append(is_prom_h)
        promoted_a_list.append(is_prom_a)

        if bool(row.get("is_played", False)):
            season_played_counts[s][h_id] = n_h + 1
            season_played_counts[s][a_id] = n_a + 1
            all_time_played[h_id] = tot_h + 1
            all_time_played[a_id] = tot_a + 1

    df["mv_home"] = home_mv_list
    df["mv_away"] = away_mv_list
    df["log_mv_ratio"] = log_ratio_list
    df["effective_log_mv_ratio"] = eff_log_ratio_list
    df["mv_diff"] = mv_diff_list
    df["mv_prior_weight_home"] = prior_w_h_list
    df["mv_prior_weight_away"] = prior_w_a_list
    df["is_promoted_home"] = promoted_h_list
    df["is_promoted_away"] = promoted_a_list

    return df


def _prior_for(col: str) -> float:
    """Returns the historical league prior for a feature column."""
    if col.startswith("exp_"):
        body = col[len("exp_"):]
        if body.startswith("match_"):
            for k, v in EXP_MATCH_PRIORS.items():
                if body.startswith(f"match_{k}"):
                    return v
        else:
            for k, v in EXP_SIDE_PRIORS.items():
                if body.startswith(f"home_{k}") or body.startswith(f"away_{k}"):
                    return v
        return 5.0
    # Longest key wins (e.g. "opponent_throws" over "throws", "shots_ontarget_for" over "shots_for")
    matches = [k for k in LEAGUE_PRIORS if k in col]
    if matches:
        return LEAGUE_PRIORS[max(matches, key=len)]
    return 5.0


def fill_feature_priors(df: pd.DataFrame) -> pd.DataFrame:
    """Fills cold-start NaNs of rolling / EWMA / interaction features, scaled by team market value if available."""
    cols = [
        c for c in df.columns
        if ("_roll_" in c or "_ewma_" in c or c.startswith("exp_") or "xg_diff" in c)
    ]
    median_mv = 600.0
    has_mv_h = "mv_home" in df.columns
    has_mv_a = "mv_away" in df.columns

    if has_mv_h:
        h_scale = np.clip((df["mv_home"] / median_mv) ** 0.35, 0.65, 1.60)
    else:
        h_scale = pd.Series(1.0, index=df.index)

    if has_mv_a:
        a_scale = np.clip((df["mv_away"] / median_mv) ** 0.35, 0.65, 1.60)
    else:
        a_scale = pd.Series(1.0, index=df.index)

    for c in cols:
        if df[c].isna().any():
            base_prior = _prior_for(c)
            if c.startswith("home_"):
                if any(k in c for k in ("xg_for", "goals_for", "shots_for", "shots_ontarget_for", "big_chances_for")):
                    fill_val = base_prior * h_scale
                elif any(k in c for k in ("xg_against", "goals_against", "shots_against", "shots_ontarget_against", "big_chances_against", "touches_in_opp_box_against")):
                    fill_val = base_prior / h_scale
                elif "touches_in_opp_box" in c:
                    fill_val = base_prior * h_scale
                else:
                    fill_val = base_prior
            elif c.startswith("away_"):
                if any(k in c for k in ("xg_for", "goals_for", "shots_for", "shots_ontarget_for", "big_chances_for")):
                    fill_val = base_prior * a_scale
                elif any(k in c for k in ("xg_against", "goals_against", "shots_against", "shots_ontarget_against", "big_chances_against", "touches_in_opp_box_against")):
                    fill_val = base_prior / a_scale
                elif "touches_in_opp_box" in c:
                    fill_val = base_prior * a_scale
                else:
                    fill_val = base_prior
            else:
                fill_val = base_prior
            df[c] = df[c].fillna(fill_val)
    return df


def add_interaction_features(merged: pd.DataFrame) -> pd.DataFrame:
    """Opponent adjustments & interaction features built from home_/away_ rolling metrics."""
    # Expected corners interaction: (home attack corners + away defense corners)
    if "home_corners_for_roll_5" in merged.columns and "away_corners_against_roll_5" in merged.columns:
        merged["exp_home_corners_5"] = (merged["home_corners_for_roll_5"] + merged["away_corners_against_roll_5"]) / 2.0
        merged["exp_away_corners_5"] = (merged["away_corners_for_roll_5"] + merged["home_corners_against_roll_5"]) / 2.0
        merged["exp_match_corners_5"] = merged["exp_home_corners_5"] + merged["exp_away_corners_5"]

    # Expected throws interaction
    if "home_throws_roll_5" in merged.columns and "away_throws_roll_5" in merged.columns:
        if "away_opponent_throws_roll_5" in merged.columns and "home_opponent_throws_roll_5" in merged.columns:
            merged["exp_home_throws_5"] = (
                merged["home_throws_roll_5"] + merged["away_opponent_throws_roll_5"]
            ) / 2.0
            merged["exp_away_throws_5"] = (
                merged["away_throws_roll_5"] + merged["home_opponent_throws_roll_5"]
            ) / 2.0
            merged["exp_match_throws_5"] = merged["exp_home_throws_5"] + merged["exp_away_throws_5"]
        else:
            merged["exp_match_throws_5"] = merged["home_throws_roll_5"] + merged["away_throws_roll_5"]

    # Expected shots interaction
    if "home_shots_for_roll_5" in merged.columns and "away_shots_against_roll_5" in merged.columns:
        merged["exp_home_shots_5"] = (merged["home_shots_for_roll_5"] + merged["away_shots_against_roll_5"]) / 2.0
        merged["exp_away_shots_5"] = (merged["away_shots_for_roll_5"] + merged["home_shots_against_roll_5"]) / 2.0
        merged["exp_match_shots_5"] = merged["exp_home_shots_5"] + merged["exp_away_shots_5"]

    # Expected offsides interaction (offside trap vs caught offside)
    if "home_offsides_for_roll_5" in merged.columns and "away_offsides_against_roll_5" in merged.columns:
        merged["exp_home_offsides_5"] = (merged["home_offsides_for_roll_5"] + merged["away_offsides_against_roll_5"]) / 2.0
        merged["exp_away_offsides_5"] = (merged["away_offsides_for_roll_5"] + merged["home_offsides_against_roll_5"]) / 2.0
        merged["exp_match_offsides_5"] = merged["exp_home_offsides_5"] + merged["exp_away_offsides_5"]

    # Expected cards interaction
    if "home_cards_for_roll_5" in merged.columns and "away_cards_against_roll_5" in merged.columns:
        merged["exp_home_cards_5"] = (merged["home_cards_for_roll_5"] + merged["away_cards_against_roll_5"]) / 2.0
        merged["exp_away_cards_5"] = (merged["away_cards_for_roll_5"] + merged["home_cards_against_roll_5"]) / 2.0
        merged["exp_match_cards_5"] = merged["exp_home_cards_5"] + merged["exp_away_cards_5"]

    # Expected match total xG and xG differential
    if "home_xg_for_roll_10" in merged.columns and "away_xg_against_roll_10" in merged.columns:
        exp_h_xg = (merged["home_xg_for_roll_10"] + merged["away_xg_against_roll_10"]) / 2.0
        exp_a_xg = (merged["away_xg_for_roll_10"] + merged["home_xg_against_roll_10"]) / 2.0
        merged["exp_match_xg_10"] = exp_h_xg + exp_a_xg
        merged["xg_diff_10"] = exp_h_xg - exp_a_xg
        merged["abs_xg_diff_10"] = merged["xg_diff_10"].abs()

    for difference in ("elo_diff", "elo_venue_diff", "ppg_diff", "gdpg_diff"):
        if difference in merged.columns:
            merged[f"abs_{difference}"] = merged[difference].abs()

    # Strength of Schedule (Fikstür Zorluğu): Opponent Elo and Market Value differences over last 5 matches
    if "home_opponent_elo_roll_5" in merged.columns and "away_opponent_elo_roll_5" in merged.columns:
        merged["schedule_difficulty_diff"] = merged["home_opponent_elo_roll_5"] - merged["away_opponent_elo_roll_5"]
    if "home_opponent_mv_roll_5" in merged.columns and "away_opponent_mv_roll_5" in merged.columns:
        merged["schedule_mv_diff"] = merged["home_opponent_mv_roll_5"] - merged["away_opponent_mv_roll_5"]

    # Venue-specific form differentials (home team's home form vs away team's away form)
    if "home_venue_xg_for_ewma_02" in merged.columns and "away_venue_xg_against_ewma_02" in merged.columns:
        merged["venue_xg_diff"] = (
            (merged["home_venue_xg_for_ewma_02"] - merged["home_venue_xg_against_ewma_02"]) -
            (merged["away_venue_xg_for_ewma_02"] - merged["away_venue_xg_against_ewma_02"])
        )
    if "home_venue_goals_for_roll_5" in merged.columns and "away_venue_goals_against_roll_5" in merged.columns:
        merged["venue_goals_diff"] = (
            (merged["home_venue_goals_for_roll_5"] - merged["home_venue_goals_against_roll_5"]) -
            (merged["away_venue_goals_for_roll_5"] - merged["away_venue_goals_against_roll_5"])
        )
    if "home_venue_shots_ontarget_for_roll_5" in merged.columns and "away_venue_shots_ontarget_against_roll_5" in merged.columns:
        merged["venue_sot_diff"] = (
            (merged["home_venue_shots_ontarget_for_roll_5"] - merged["home_venue_shots_ontarget_against_roll_5"]) -
            (merged["away_venue_shots_ontarget_for_roll_5"] - merged["away_venue_shots_ontarget_against_roll_5"])
        )

    # Venue-specific match pace & total expected xG (vital signal for Over/Under goals)
    if (
        "home_venue_xg_for_ewma_02" in merged.columns
        and "away_venue_xg_against_ewma_02" in merged.columns
        and "away_venue_xg_for_ewma_02" in merged.columns
        and "home_venue_xg_against_ewma_02" in merged.columns
    ):
        exp_v_h_xg = (merged["home_venue_xg_for_ewma_02"] + merged["away_venue_xg_against_ewma_02"]) / 2.0
        exp_v_a_xg = (merged["away_venue_xg_for_ewma_02"] + merged["home_venue_xg_against_ewma_02"]) / 2.0
        merged["exp_venue_match_xg"] = exp_v_h_xg + exp_v_a_xg

    # Home-minus-away net strength differentials (used by the outcome models).
    # Names intentionally avoid "_roll_"/"_ewma_" so other models' feature filters are unaffected.
    for stat, tag in (("goals", "goals"), ("shots_ontarget", "sot")):
        for suffix, short in (("ewma_02", "e02"), ("roll_10", "r10")):
            cols = [f"home_{stat}_for_{suffix}", f"home_{stat}_against_{suffix}",
                    f"away_{stat}_for_{suffix}", f"away_{stat}_against_{suffix}"]
            if all(c in merged.columns for c in cols):
                merged[f"sdiff_{tag}_{short}"] = (
                    (merged[cols[0]] - merged[cols[1]]) - (merged[cols[2]] - merged[cols[3]])
                )

    # Defensive line depth & mutual high defensive line risk (offside trap / high-line vulnerability)
    if "home_offsides_against_roll_10" in merged.columns and "away_offsides_against_roll_10" in merged.columns:
        h_line = merged["home_offsides_against_roll_10"].fillna(1.63)
        a_line = merged["away_offsides_against_roll_10"].fillna(1.63)
        merged["home_high_line"] = h_line
        merged["away_high_line"] = a_line
        merged["mutual_high_line_risk"] = h_line * a_line
    elif "home_high_line" not in merged.columns:
        merged["home_high_line"] = 1.63
        merged["away_high_line"] = 1.63
        merged["mutual_high_line_risk"] = 2.66

    return merged


def merge_features_to_matches(df_matches: pd.DataFrame, long_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merges historical rolling metrics back into the match-level dataframe
    for both home and away teams.
    """
    # Filter features created in long_df
    feature_cols = [
        c for c in long_df.columns
        if "_roll_" in c or "_ewma_" in c or c.endswith("_obs_age_days")
    ]

    # Home features
    home_lookup = long_df[long_df["is_home"] == 1][["match_id", "team_id"] + feature_cols].copy()
    home_rename = {c: f"home_{c}" for c in feature_cols}
    home_lookup = home_lookup.rename(columns=home_rename)

    # Away features
    away_lookup = long_df[long_df["is_home"] == 0][["match_id", "team_id"] + feature_cols].copy()
    away_rename = {c: f"away_{c}" for c in feature_cols}
    away_lookup = away_lookup.rename(columns=away_rename)

    merged = df_matches.merge(home_lookup.drop(columns=["team_id"]), on="match_id", how="left")
    merged = merged.merge(away_lookup.drop(columns=["team_id"]), on="match_id", how="left")

    # Compute squad market value features and Bayesian prior decay weights
    merged = compute_market_value_features(merged)

    # Fill initial season NaNs with strictly historical league priors (scaled by market values),
    # then derive interaction features so they never mix priors with wrong fallbacks.
    merged = fill_feature_priors(merged).copy()
    merged = add_interaction_features(merged)
    merged = fill_feature_priors(merged)
    return merged


def compute_referee_features(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates strictly historical (leakage-free) referee tendency features."""
    df = df.copy()
    if "match_date" not in df.columns:
        if "kickoff_millis" in df.columns:
            df["match_date"] = pd.to_datetime(df["kickoff_millis"], unit="ms")
        else:
            df["match_date"] = pd.to_datetime(df["kickoff_label"])

    sort_cols = ["match_date", "match_id"] if "match_id" in df.columns else ["match_date"]
    df = df.sort_values(by=sort_cols, kind="mergesort").reset_index(drop=True)

    ref_avg_cards = [np.nan] * len(df)
    ref_avg_fouls = [np.nan] * len(df)
    ref_prior_matches = [0] * len(df)

    # Historical state: referee_name -> list of (cards, fouls)
    ref_history: Dict[str, List[Tuple[float, float]]] = {}

    for _, batch in df.groupby("match_date", sort=False, dropna=False):
        # All matches at the same kickoff use the history from before that batch.
        for index, row in batch.iterrows():
            ref_name = row.get("referee_name") or "Unknown"
            hist = ref_history.get(ref_name, [])
            count = len(hist)
            sum_cards = sum(item[0] for item in hist)
            sum_fouls = sum(item[1] for item in hist)
            ref_avg_cards[index] = (
                sum_cards + REFEREE_SHRINKAGE_MATCHES * REFEREE_DEFAULTS["referee_avg_cards"]
            ) / (count + REFEREE_SHRINKAGE_MATCHES)
            ref_avg_fouls[index] = (
                sum_fouls + REFEREE_SHRINKAGE_MATCHES * REFEREE_DEFAULTS["referee_avg_fouls"]
            ) / (count + REFEREE_SHRINKAGE_MATCHES)
            ref_prior_matches[index] = int(count)

        # Update referee histories only after every feature in the kickoff batch is read.
        for _, row in batch.iterrows():
            ref_name = row.get("referee_name") or "Unknown"
            cards = row.get("total_cards")
            fouls = row.get("total_fouls")
            if ref_name != "Unknown" and pd.notna(cards) and pd.notna(fouls):
                ref_history.setdefault(ref_name, []).append((float(cards), float(fouls)))

    df["referee_avg_cards"] = ref_avg_cards
    df["referee_avg_fouls"] = ref_avg_fouls
    df["referee_prior_matches"] = ref_prior_matches
    return df


def build_prediction_row(
    team_states: pd.DataFrame,
    strength_state: Dict[str, Any],
    home_id: int,
    away_id: int,
    match_date: pd.Timestamp,
    referee: Optional[Dict[str, Any]] = None,
    season: Optional[str] = None,
    draw_state: Optional[DrawFeatureState] = None,
    gameweek: Optional[float] = None,
    match_id: Optional[int] = None,
    use_official_xi: bool = True,
) -> pd.DataFrame:
    """
    Builds a single live feature row for (home_id vs away_id) from each team's CURRENT state,
    using exactly the same feature definitions as the training dataset.
    """
    strength_state = advance_strength_state_to_season(strength_state, season)
    s_str = str(season or strength_state.get("season") or "2026_27")
    official_starters = load_official_match_starters(match_id) if (use_official_xi and match_id) else {}
    player_history = strength_state.get("player_history") or {}

    form_cols = [
        c for c in team_states.columns
        if ("_roll_" in c or "_ewma_" in c) and not c.startswith("home_venue_") and not c.startswith("away_venue_")
    ]
    row: Dict[str, Any] = {"home_id": home_id, "away_id": away_id, "match_date": match_date}

    for side, tid in (("home", home_id), ("away", away_id)):
        st = team_states.loc[tid] if tid in team_states.index else None
        for c in form_cols:
            row[f"{side}_{c}"] = float(st[c]) if st is not None else np.nan
        if st is not None and pd.notnull(st["last_match_date"]):
            rest = (match_date - st["last_match_date"]).total_seconds() / 86400.0
        else:
            rest = 14.0
        row[f"{side}_rest_days"] = float(min(max(rest, 0.0), 30.0))

        strength = _team_strength(strength_state, tid, is_home=(side == "home"))
        row[f"elo_{side}"] = strength["elo"]
        row[f"elo_venue_{side}"] = strength["elo_venue"]
        row[f"ppg_{side}"] = strength["ppg"]
        row[f"gdpg_{side}"] = strength["gdpg"]
        if tid in official_starters and player_history:
            xi_ov, xi_att, xi_def = _aggregate_xi_ratings(official_starters[tid], player_history, s_str)
            row[f"{side}_xi_rating"] = xi_ov
            row[f"_{side}_xi_att"] = xi_att
            row[f"_{side}_xi_def"] = xi_def
        else:
            row[f"{side}_xi_rating"] = strength["xi_rating"]
            row[f"_{side}_xi_att"] = strength["xi_attack"]
            row[f"_{side}_xi_def"] = strength["xi_defense"]

    # Assign venue-specific form to matching side
    st_h = team_states.loc[home_id] if home_id in team_states.index else None
    st_a = team_states.loc[away_id] if away_id in team_states.index else None
    venue_stat_suffixes = [
        "venue_xg_for_ewma_02", "venue_xg_against_ewma_02",
        "venue_goals_for_roll_5", "venue_goals_against_roll_5",
        "venue_shots_ontarget_for_roll_5", "venue_shots_ontarget_against_roll_5",
    ]
    for v_suf in venue_stat_suffixes:
        row[f"home_{v_suf}"] = float(st_h.get(f"home_{v_suf}", np.nan)) if st_h is not None else np.nan
        row[f"away_{v_suf}"] = float(st_a.get(f"away_{v_suf}", np.nan)) if st_a is not None else np.nan

    row["elo_diff"] = row["elo_home"] - row["elo_away"]
    row["elo_venue_diff"] = row["elo_venue_home"] - row["elo_venue_away"]
    row["ppg_diff"] = row["ppg_home"] - row["ppg_away"]
    row["gdpg_diff"] = row["gdpg_home"] - row["gdpg_away"]
    row["xi_rating_diff"] = row["home_xi_rating"] - row["away_xi_rating"]
    h_att_vs_a_def = row.pop("_home_xi_att") - row.pop("_away_xi_def")
    a_att_vs_h_def = row.pop("_away_xi_att") - row.pop("_home_xi_def")
    row["home_xi_att_vs_away_def"] = h_att_vs_a_def
    row["away_xi_att_vs_home_def"] = a_att_vs_h_def
    row["xi_att_vs_def_diff"] = h_att_vs_a_def - a_att_vs_h_def

    # Squad market values and dynamic Bayesian sample-size prior decay weights
    mv_map = get_team_market_values_map()
    default_median_mv = 600.0
    s_val = str(season or "2026_27")
    mv_h = mv_map.get((home_id, s_val), mv_map.get(home_id, default_median_mv))
    mv_a = mv_map.get((away_id, s_val), mv_map.get(away_id, default_median_mv))
    row["mv_home"] = mv_h
    row["mv_away"] = mv_a
    row["log_mv_ratio"] = float(np.log(max(mv_h, 10.0) / max(mv_a, 10.0)))
    row["mv_diff"] = float(mv_h - mv_a)

    n_h = int(strength_state.get("table", {}).get(home_id, [0, 0, 0])[2]) if "table" in strength_state else 0
    n_a = int(strength_state.get("table", {}).get(away_id, [0, 0, 0])[2]) if "table" in strength_state else 0
    w_h = 8.0 / (8.0 + n_h)
    w_a = 8.0 / (8.0 + n_a)
    row["mv_prior_weight_home"] = w_h
    row["mv_prior_weight_away"] = w_a
    row["effective_log_mv_ratio"] = float(row["log_mv_ratio"] * np.sqrt(w_h * w_a))
    all_time = strength_state.get("all_time_played", {})
    tot_h = int(all_time.get(home_id, 0))
    tot_a = int(all_time.get(away_id, 0))
    row["is_promoted_home"] = 1.0 if (n_h < 10 and tot_h < 10) else 0.0
    row["is_promoted_away"] = 1.0 if (n_a < 10 and tot_a < 10) else 0.0

    row.update(REFEREE_DEFAULTS)
    row["referee_name"] = None
    if referee:
        row.update({k: v for k, v in referee.items() if v is not None})
    if draw_state is not None:
        row.update(draw_state.features(home_id, away_id, gameweek))

    out = pd.DataFrame([row])
    out = fill_feature_priors(out)
    out = add_interaction_features(out)
    return fill_feature_priors(out)


def build_feature_dataset(
    input_matches_path: Union[str, Path],
    output_path: Union[str, Path],
) -> pd.DataFrame:
    """Main feature construction flow."""
    input_matches_path = Path(input_matches_path)
    output_path = Path(output_path)
    logger.info(f"Loading match dataset from {input_matches_path}...")
    df = pd.read_parquet(input_matches_path)
    df = attach_statsapi_xg(df)
    # Keep only explicitly sourced provider xG in the feature dataset. Legacy
    # aggregate-stat proxy columns are neither provider xG nor model inputs.
    df = df.drop(columns=[c for c in ("home_xg", "away_xg", "total_xg") if c in df.columns])
    logger.info(f"Loaded {len(df)} matches.")

    df = calculate_rest_days(df)
    long_df = build_team_match_history(df)
    long_df = compute_pre_match_features(long_df)
    featured_matches = merge_features_to_matches(df, long_df)
    featured_matches = compute_referee_features(featured_matches)
    featured_matches = compute_strength_features(featured_matches)
    featured_matches = add_interaction_features(featured_matches)
    featured_matches = add_draw_features(featured_matches)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    featured_matches.to_parquet(output_path, index=False)
    logger.info(f"Saved featured dataset with {featured_matches.shape[1]} columns to {output_path}.")
    return featured_matches


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default=str(MATCHES_SUMMARY_PATH))
    parser.add_argument("--output", type=str, default=str(FEATURES_PATH))
    args = parser.parse_args()

    build_feature_dataset(Path(args.input), Path(args.output))
