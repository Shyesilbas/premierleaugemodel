#!/usr/bin/env python3
"""
Premier League Leakage-Free Feature Engineering Pipeline
Constructs match-level rolling statistics (EWMA / rolling windows), opponent-adjusted metrics,
rest days, and team form for predictive modeling.

Strict Leakage-Free Principle:
For any match t, team features are calculated using ONLY matches played before t (strictly historical).
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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


def calculate_rest_days(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates rest days since previous match for both home and away teams."""
    df = df.copy()
    if "kickoff_millis" in df.columns:
        df["match_date"] = pd.to_datetime(df["kickoff_millis"], unit="ms")
    else:
        df["match_date"] = pd.to_datetime(df["kickoff_label"])

    df = df.sort_values(by="match_date").reset_index(drop=True)

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
    """
    records = []
    for _, row in df.iterrows():
        m_id = row["match_id"]
        m_date = row["match_date"]
        gw = row.get("gameweek", 0)

        # Home perspective
        records.append({
            "match_id": m_id,
            "match_date": m_date,
            "gameweek": gw,
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
    long_df = long_df.sort_values(by=["team_id", "match_date"]).reset_index(drop=True)
    return long_df


def compute_pre_match_features(long_df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes strictly lagging rolling statistics (mean, EWMA) for each team.
    Using shift(1) guarantees NO DATA LEAKAGE from current match.
    """
    stat_cols = [
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

    grouped = long_df.groupby("team_id")

    # Shift each metric by 1 so match t only sees history up to t-1
    for col in stat_cols:
        shifted = grouped[col].shift(1)

        # Rolling means
        for w in ROLLING_WINDOWS:
            rolling_series = grouped[col].transform(lambda s: s.shift(1).rolling(w, min_periods=1).mean())
            long_df[f"{col}_roll_{w}"] = rolling_series

        # EWMA
        for a in EWMA_ALPHAS:
            alpha_str = str(a).replace(".", "")
            ewma_series = grouped[col].transform(lambda s: s.shift(1).ewm(alpha=a, min_periods=1).mean())
            long_df[f"{col}_ewma_{alpha_str}"] = ewma_series

    return long_df


def compute_referee_features(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates strictly historical (leakage-free) referee tendency features."""
    df = df.copy()
    if "match_date" not in df.columns:
        if "kickoff_millis" in df.columns:
            df["match_date"] = pd.to_datetime(df["kickoff_millis"], unit="ms")
        else:
            df["match_date"] = pd.to_datetime(df["kickoff_label"])

    df = df.sort_values(by="match_date").reset_index(drop=True)

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
            avg_c = 4.15  # Premier League historical mean cards/match
            avg_f = 21.5  # Premier League historical mean fouls/match
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

    # Opponent adjustments & Interaction Features
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

    # Fill initial season NaNs with strictly historical league priors (NO FUTURE LEAKAGE)
    league_priors = {
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

    numeric_feature_cols = [c for c in merged.columns if "_roll_" in c or "_ewma_" in c or "exp_" in c]
    for c in numeric_feature_cols:
        prior_val = 5.0
        for k, v in league_priors.items():
            if k in c:
                prior_val = v
                break
        if "exp_match_corners" in c:
            prior_val = 10.3
        elif "exp_match_throws" in c:
            prior_val = 32.9
        elif "exp_match_shots" in c:
            prior_val = 26.0
        elif "exp_match_offsides" in c:
            prior_val = 3.26
        elif "exp_match_cards" in c:
            prior_val = 4.2
        elif "exp_match_xg" in c:
            prior_val = 2.9

        merged[c] = merged[c].fillna(prior_val)

    return merged


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
