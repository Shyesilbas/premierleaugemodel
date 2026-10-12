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

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

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
    "big_chances_for", "touches_in_opp_box",
    "fouls_committed", "fouls_drawn",
    "cards_for", "cards_against",
    "xg_for", "xg_against",
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
    "big_chances_for": 1.8, "touches_in_opp_box": 24.5,
    "fouls_committed": 10.5, "fouls_drawn": 10.5,
    "cards_for": 2.1, "cards_against": 2.1,
    "xg_for": 1.45, "xg_against": 1.45,
}
# Priors for interaction features: per-team side (exp_home_* / exp_away_*) and match totals (exp_match_*)
EXP_SIDE_PRIORS = {"corners": 5.15, "shots": 13.0, "offsides": 1.63, "cards": 2.1, "xg": 1.45}
EXP_MATCH_PRIORS = {"corners": 10.3, "throws": 32.9, "shots": 26.0, "offsides": 3.26, "cards": 4.2, "xg": 2.9}

# Team strength (Elo + season-to-date table) parameters
ELO_INIT = 1500.0
ELO_NEWCOMER = 1430.0        # Promoted teams entering after the first season
ELO_K = 20.0
ELO_HOME_ADV = 60.0
ELO_SEASON_REGRESS = 0.20    # Pull ratings 20% towards the mean at each new season
PPG_PRIOR = 1.37             # League-average points per game
PRIOR_GAMES = 3.0            # Shrinkage strength for season-to-date ppg / goal difference

REFEREE_DEFAULTS = {"referee_avg_cards": 4.15, "referee_avg_fouls": 21.5, "referee_prior_matches": 0}


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

        # Update last match dates
        team_last_date[h_id] = cur_date
        team_last_date[a_id] = cur_date

    df["home_rest_days"] = home_rest_days
    df["away_rest_days"] = away_rest_days
    return df


def build_team_match_history(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms match dataframe into a long team-match perspective dataframe
    where each row represents one team's performance in a single match.
    Stats of unplayed fixtures are forced to NaN so they never enter rolling windows.
    """
    if "is_played" not in df.columns or "match_date" not in df.columns:
        df = prepare_matches(df)

    records = []
    for _, row in df.iterrows():
        m_id = row["match_id"]
        m_date = row["match_date"]
        gw = row.get("gameweek", 0)
        season = row.get("season")
        played = bool(row["is_played"])

        # Home perspective
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
            "corners_for": row.get("home_won_corners", 0.0),
            "corners_against": row.get("away_won_corners", 0.0),
            "throws": row.get("home_total_throws", 0.0),
            "opponent_throws": row.get("away_total_throws", 0.0),
            "shots_for": row.get("home_total_scoring_att", 0.0),
            "shots_against": row.get("away_total_scoring_att", 0.0),
            "shots_ontarget_for": row.get("home_ontarget_scoring_att", 0.0),
            "shots_ontarget_against": row.get("away_ontarget_scoring_att", 0.0),
            "saves": row.get("home_saves", 0.0),
            "possession": row.get("home_possession_percentage", 50.0),
            "passes": row.get("home_total_pass", 0.0),
            "fouls_committed": row.get("home_fk_foul_lost", 10.0),
            "fouls_drawn": row.get("home_fk_foul_won", 10.0),
            "offsides_for": row.get("home_total_offside", 1.6),
            "offsides_against": row.get("away_total_offside", 1.6),
            "big_chances_for": row.get("home_big_chance_created", 1.8),
            "touches_in_opp_box": row.get("home_touches_in_opp_box", 24.0),
            "cards_for": row.get("home_total_yel_card", 0.0) + row.get("home_total_red_card", 0.0),
            "cards_against": row.get("away_total_yel_card", 0.0) + row.get("away_total_red_card", 0.0),
            "xg_for": row.get("home_xg", 1.4),
            "xg_against": row.get("away_xg", 1.2),
        })

        # Away perspective
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
            "corners_for": row.get("away_won_corners", 0.0),
            "corners_against": row.get("home_won_corners", 0.0),
            "throws": row.get("away_total_throws", 0.0),
            "opponent_throws": row.get("home_total_throws", 0.0),
            "shots_for": row.get("away_total_scoring_att", 0.0),
            "shots_against": row.get("home_total_scoring_att", 0.0),
            "shots_ontarget_for": row.get("away_ontarget_scoring_att", 0.0),
            "shots_ontarget_against": row.get("home_ontarget_scoring_att", 0.0),
            "saves": row.get("away_saves", 0.0),
            "possession": row.get("away_possession_percentage", 50.0),
            "passes": row.get("away_total_pass", 0.0),
            "fouls_committed": row.get("away_fk_foul_lost", 10.0),
            "fouls_drawn": row.get("away_fk_foul_won", 10.0),
            "offsides_for": row.get("away_total_offside", 1.6),
            "offsides_against": row.get("home_total_offside", 1.6),
            "big_chances_for": row.get("away_big_chance_created", 1.8),
            "touches_in_opp_box": row.get("away_touches_in_opp_box", 24.0),
            "cards_for": row.get("away_total_yel_card", 0.0) + row.get("away_total_red_card", 0.0),
            "cards_against": row.get("home_total_yel_card", 0.0) + row.get("home_total_red_card", 0.0),
            "xg_for": row.get("away_xg", 1.2),
            "xg_against": row.get("home_xg", 1.4),
        })

    long_df = pd.DataFrame(records)
    metric_cols = [c for c in STAT_COLS + ["passes"] if c in long_df.columns]
    long_df.loc[~long_df["is_played"], metric_cols] = np.nan
    long_df = long_df.sort_values(by=["team_id", "match_date", "match_id"], kind="mergesort").reset_index(drop=True)
    return long_df


def _alpha_str(a: float) -> str:
    return str(a).replace(".", "")


def _lagged_team_state(
    long_df: pd.DataFrame, col: str, played: pd.Series, fn: Callable[[pd.Series], pd.Series]
) -> pd.Series:
    """
    For every team-match row returns the statistic computed over the team's PLAYED matches strictly
    before that row. Unplayed fixtures inherit the state after the team's latest played match.
    """
    out = pd.Series(np.nan, index=long_df.index)
    for _, idx in long_df.groupby("team_id", sort=False).groups.items():
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
    """
    long_df = long_df.sort_values(by=["team_id", "match_date", "match_id"], kind="mergesort").reset_index(drop=True)
    played = long_df["is_played"].astype(bool) if "is_played" in long_df.columns else long_df["goals_for"].notna()

    new_cols: Dict[str, pd.Series] = {}
    for col in STAT_COLS:
        # Rolling means
        for w in ROLLING_WINDOWS:
            new_cols[f"{col}_roll_{w}"] = _lagged_team_state(
                long_df, col, played, lambda s, w=w: s.rolling(w, min_periods=1).mean())
        # EWMA
        for a in EWMA_ALPHAS:
            new_cols[f"{col}_ewma_{_alpha_str(a)}"] = _lagged_team_state(
                long_df, col, played, lambda s, a=a: s.ewm(alpha=a, min_periods=1).mean())

    return pd.concat([long_df, pd.DataFrame(new_cols, index=long_df.index)], axis=1)


def compute_team_states(long_df: pd.DataFrame, until: Optional[pd.Timestamp] = None) -> pd.DataFrame:
    """
    Current form state of each team AFTER its latest played match (optionally up to `until`).
    Same definitions as compute_pre_match_features, so it is the exact feature vector of the team's next match.
    """
    played = long_df["is_played"].astype(bool) if "is_played" in long_df.columns else long_df["goals_for"].notna()
    d = long_df[played]
    if until is not None:
        d = d[d["match_date"] <= until]

    rows: Dict[int, Dict[str, Any]] = {}
    for tid, g in d.sort_values(["match_date", "match_id"], kind="mergesort").groupby("team_id"):
        rec: Dict[str, Any] = {"last_match_date": g["match_date"].max()}
        for col in STAT_COLS:
            s = g[col].dropna()
            for w in ROLLING_WINDOWS:
                rec[f"{col}_roll_{w}"] = float(s.tail(w).mean()) if len(s) else np.nan
            for a in EWMA_ALPHAS:
                rec[f"{col}_ewma_{_alpha_str(a)}"] = float(s.ewm(alpha=a, min_periods=1).mean().iloc[-1]) if len(s) else np.nan
        rows[int(tid)] = rec
    return pd.DataFrame.from_dict(rows, orient="index")


def _run_strength(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Sequential Elo + season-to-date table. Returns strictly pre-match strength features per match
    and the final state (after the last played match) for live predictions.
    """
    df = df if "is_played" in df.columns else prepare_matches(df)
    has_season = "season" in df.columns
    first_season = df["season"].iloc[0] if has_season and len(df) else None

    elo: Dict[int, float] = {}
    table: Dict[int, List[float]] = {}  # team -> [points, goal_diff, matches] in current season
    current_season = first_season
    pre: List[Dict[str, float]] = []

    def season_form(t: int) -> Tuple[float, float]:
        pts, gd, n = table.get(t, [0.0, 0.0, 0.0])
        return (pts + PPG_PRIOR * PRIOR_GAMES) / (n + PRIOR_GAMES), gd / (n + PRIOR_GAMES)

    for _, row in df.iterrows():
        season = row["season"] if has_season else None
        if season != current_season:
            for t in elo:
                elo[t] = (1 - ELO_SEASON_REGRESS) * elo[t] + ELO_SEASON_REGRESS * ELO_INIT
            table = {}
            current_season = season

        h, a = int(row["home_id"]), int(row["away_id"])
        for t in (h, a):
            if t not in elo:
                elo[t] = ELO_INIT if season == first_season else ELO_NEWCOMER

        h_ppg, h_gd = season_form(h)
        a_ppg, a_gd = season_form(a)
        pre.append({
            "elo_home": elo[h], "elo_away": elo[a], "elo_diff": elo[h] - elo[a],
            "ppg_home": h_ppg, "ppg_away": a_ppg, "ppg_diff": h_ppg - a_ppg,
            "gdpg_home": h_gd, "gdpg_away": a_gd, "gdpg_diff": h_gd - a_gd,
        })

        if not row["is_played"]:
            continue
        hs, as_ = float(row["home_score"]), float(row["away_score"])
        exp_h = 1.0 / (1.0 + 10 ** ((elo[a] - (elo[h] + ELO_HOME_ADV)) / 400.0))
        s_h = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
        margin = abs(hs - as_)
        mult = np.log(margin + 1.0) + 1.0 if margin > 0 else 1.0
        delta = ELO_K * mult * (s_h - exp_h)
        elo[h] += delta
        elo[a] -= delta

        h_pts = 3.0 if hs > as_ else (1.0 if hs == as_ else 0.0)
        a_pts = 3.0 if as_ > hs else (1.0 if hs == as_ else 0.0)
        for t, pts, gd in ((h, h_pts, hs - as_), (a, a_pts, as_ - hs)):
            rec = table.setdefault(t, [0.0, 0.0, 0.0])
            rec[0] += pts
            rec[1] += gd
            rec[2] += 1.0

    state = {"elo": dict(elo), "table": {k: list(v) for k, v in table.items()}, "season": current_season}
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


def _team_strength(state: Dict[str, Any], team_id: int) -> Dict[str, float]:
    elo = state.get("elo", {}).get(int(team_id), ELO_NEWCOMER)
    pts, gd, n = state.get("table", {}).get(int(team_id), [0.0, 0.0, 0.0])
    return {
        "elo": float(elo),
        "ppg": (pts + PPG_PRIOR * PRIOR_GAMES) / (n + PRIOR_GAMES),
        "gdpg": gd / (n + PRIOR_GAMES),
    }


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
    """Fills cold-start NaNs of rolling / EWMA / interaction features with fixed league priors."""
    cols = [c for c in df.columns if "_roll_" in c or "_ewma_" in c or c.startswith("exp_")]
    for c in cols:
        if df[c].isna().any():
            df[c] = df[c].fillna(_prior_for(c))
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
        merged["exp_match_throws_5"] = (merged["home_throws_roll_5"] + merged["away_throws_roll_5"])

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

    # Expected xG interaction
    if "home_xg_for_roll_5" in merged.columns and "away_xg_against_roll_5" in merged.columns:
        merged["exp_home_xg_5"] = (merged["home_xg_for_roll_5"] + merged["away_xg_against_roll_5"]) / 2.0
        merged["exp_away_xg_5"] = (merged["away_xg_for_roll_5"] + merged["home_xg_against_roll_5"]) / 2.0
        merged["exp_match_xg_5"] = merged["exp_home_xg_5"] + merged["exp_away_xg_5"]

    # Home-minus-away net strength differentials (used by the outcome models).
    # Names intentionally avoid "_roll_"/"_ewma_" so other models' feature filters are unaffected.
    for stat, tag in (("xg", "xg"), ("goals", "goals"), ("shots_ontarget", "sot")):
        for suffix, short in (("ewma_02", "e02"), ("roll_10", "r10")):
            cols = [f"home_{stat}_for_{suffix}", f"home_{stat}_against_{suffix}",
                    f"away_{stat}_for_{suffix}", f"away_{stat}_against_{suffix}"]
            if all(c in merged.columns for c in cols):
                merged[f"sdiff_{tag}_{short}"] = (
                    (merged[cols[0]] - merged[cols[1]]) - (merged[cols[2]] - merged[cols[3]])
                )
    return merged


def merge_features_to_matches(df_matches: pd.DataFrame, long_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merges historical rolling metrics back into the match-level dataframe
    for both home and away teams.
    """
    # Filter features created in long_df
    feature_cols = [c for c in long_df.columns if "_roll_" in c or "_ewma_" in c]

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

    # Fill initial season NaNs with strictly historical league priors (NO FUTURE LEAKAGE),
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

    ref_avg_cards = []
    ref_avg_fouls = []
    ref_prior_matches = []

    # Historical state: referee_name -> list of (cards, fouls)
    ref_history: Dict[str, List[Tuple[float, float]]] = {}

    for _, row in df.iterrows():
        ref_name = row.get("referee_name") or "Unknown"
        cards = row.get("total_cards")
        fouls = row.get("total_fouls")

        # Compute strictly pre-match statistics for this referee
        if ref_name in ref_history and len(ref_history[ref_name]) > 0:
            hist = ref_history[ref_name]
            avg_c = np.mean([h[0] for h in hist])
            avg_f = np.mean([h[1] for h in hist])
            count = len(hist)
        else:
            avg_c = REFEREE_DEFAULTS["referee_avg_cards"]  # Premier League historical mean cards/match
            avg_f = REFEREE_DEFAULTS["referee_avg_fouls"]  # Premier League historical mean fouls/match
            count = 0

        ref_avg_cards.append(float(avg_c))
        ref_avg_fouls.append(float(avg_f))
        ref_prior_matches.append(int(count))

        # Update state after match if target data is not null
        if ref_name != "Unknown" and pd.notnull(cards) and pd.notnull(fouls):
            if ref_name not in ref_history:
                ref_history[ref_name] = []
            ref_history[ref_name].append((float(cards), float(fouls)))

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
) -> pd.DataFrame:
    """
    Builds a single live feature row for (home_id vs away_id) from each team's CURRENT state,
    using exactly the same feature definitions as the training dataset.
    """
    form_cols = [c for c in team_states.columns if "_roll_" in c or "_ewma_" in c]
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

        strength = _team_strength(strength_state, tid)
        row[f"elo_{side}"] = strength["elo"]
        row[f"ppg_{side}"] = strength["ppg"]
        row[f"gdpg_{side}"] = strength["gdpg"]

    row["elo_diff"] = row["elo_home"] - row["elo_away"]
    row["ppg_diff"] = row["ppg_home"] - row["ppg_away"]
    row["gdpg_diff"] = row["gdpg_home"] - row["gdpg_away"]

    row.update(REFEREE_DEFAULTS)
    row["referee_name"] = None
    if referee:
        row.update({k: v for k, v in referee.items() if v is not None})

    out = pd.DataFrame([row])
    out = fill_feature_priors(out)
    out = add_interaction_features(out)
    return fill_feature_priors(out)


def build_feature_dataset(
    input_matches_path: Path,
    output_path: Path,
) -> pd.DataFrame:
    """Main feature construction flow."""
    logger.info(f"Loading match dataset from {input_matches_path}...")
    df = pd.read_parquet(input_matches_path)
    logger.info(f"Loaded {len(df)} matches.")

    df = calculate_rest_days(df)
    long_df = build_team_match_history(df)
    long_df = compute_pre_match_features(long_df)
    featured_matches = merge_features_to_matches(df, long_df)
    featured_matches = compute_referee_features(featured_matches)
    featured_matches = compute_strength_features(featured_matches)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    featured_matches.to_parquet(output_path, index=False)
    logger.info(f"Saved featured dataset with {featured_matches.shape[1]} columns to {output_path}.")
    return featured_matches


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="data/processed/matches_summary_all.parquet")
    parser.add_argument("--output", type=str, default="data/processed/features_matches_all.parquet")
    args = parser.parse_args()

    build_feature_dataset(Path(args.input), Path(args.output))
