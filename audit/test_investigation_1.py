"""
Audit Investigation 1: Forensic Verification of Rolling Feature Calculations
Tests multi-team isolation, shift lag, boundary conditions, duplicate timestamps,
and simultaneous kickoff behavior in src.features.build_features.
"""
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.features.build_features import (
    _lagged_team_state,
    compute_pre_match_features,
    prepare_matches,
    build_team_match_history,
)

def run_synthetic_team_isolation_test():
    print("=== TEST 1: Synthetic 3-Team Isolation & Rolling Verification ===")
    
    # 3 teams: Team 101, Team 102, Team 103
    # Distinct values:
    # Team 101 has xg_for = [10.0, 20.0, 30.0, 40.0]
    # Team 102 has xg_for = [1.0, 2.0, 3.0, 4.0]
    # Team 103 has xg_for = [100.0, 200.0, 300.0, 400.0]
    
    dates = [
        datetime(2025, 8, 10, 15, 0),
        datetime(2025, 8, 17, 15, 0),
        datetime(2025, 8, 24, 15, 0),
        datetime(2025, 8, 31, 15, 0),
    ]
    
    rows = []
    # Team 101
    for i, (d, v) in enumerate(zip(dates, [10.0, 20.0, 30.0, 40.0])):
        rows.append({"match_id": 1000 + i, "team_id": 101, "match_date": d, "xg_for": v, "is_played": True, "goals_for": v})
    # Team 102
    for i, (d, v) in enumerate(zip(dates, [1.0, 2.0, 3.0, 4.0])):
        rows.append({"match_id": 2000 + i, "team_id": 102, "match_date": d, "xg_for": v, "is_played": True, "goals_for": v})
    # Team 103
    for i, (d, v) in enumerate(zip(dates, [100.0, 200.0, 300.0, 400.0])):
        rows.append({"match_id": 3000 + i, "team_id": 103, "match_date": d, "xg_for": v, "is_played": True, "goals_for": v})
        
    df_long = pd.DataFrame(rows)
    df_long = df_long.sort_values(by=["team_id", "match_date", "match_id"]).reset_index(drop=True)
    played = df_long["is_played"]
    
    # Run _lagged_team_state with window=2 mean
    roll_w2 = _lagged_team_state(
        df_long, "xg_for", played, lambda s: s.rolling(2, min_periods=1).mean()
    )
    df_long["xg_roll_2"] = roll_w2
    
    print("\nResulting Data Table:")
    print(df_long[["team_id", "match_date", "xg_for", "xg_roll_2"]])
    
    # Assertions
    # Match 0 for each team MUST be NaN (first match has no prior history)
    t101 = df_long[df_long["team_id"] == 101]["xg_roll_2"].tolist()
    t102 = df_long[df_long["team_id"] == 102]["xg_roll_2"].tolist()
    t103 = df_long[df_long["team_id"] == 103]["xg_roll_2"].tolist()
    
    assert np.isnan(t101[0]), f"Team 101 match 0 should be NaN, got {t101[0]}"
    assert np.isnan(t102[0]), f"Team 102 match 0 should be NaN, got {t102[0]}"
    assert np.isnan(t103[0]), f"Team 103 match 0 should be NaN, got {t103[0]}"
    
    # Match 1 should be value of match 0
    assert t101[1] == 10.0, f"Expected 10.0, got {t101[1]}"
    assert t102[1] == 1.0, f"Expected 1.0, got {t102[1]}"
    assert t103[1] == 100.0, f"Expected 100.0, got {t103[1]}"
    
    # Match 2 should be mean of match 0 and match 1
    assert t101[2] == 15.0, f"Expected 15.0, got {t101[2]}" # (10+20)/2
    assert t102[2] == 1.5, f"Expected 1.5, got {t102[2]}"   # (1+2)/2
    assert t103[2] == 150.0, f"Expected 150.0, got {t103[2]}" # (100+200)/2
    
    # Match 3 should be mean of match 1 and match 2 (window=2)
    assert t101[3] == 25.0, f"Expected 25.0, got {t101[3]}" # (20+30)/2
    assert t102[3] == 2.5, f"Expected 2.5, got {t102[3]}"   # (2+3)/2
    assert t103[3] == 250.0, f"Expected 250.0, got {t103[3]}" # (200+300)/2
    
    print("\n>>> TEST 1 PASSED: Zero cross-team contamination verified.")

def run_simultaneous_and_unplayed_fixtures_test():
    print("\n=== TEST 2: Simultaneous Kickoff & Unplayed Fixture Test ===")
    
    # Team 1 plays Team 2 at 15:00 on Day 1
    # Team 3 plays Team 4 at 15:00 on Day 1
    # Team 1 plays Team 3 at 15:00 on Day 2 (UNPLAYED)
    
    matches = [
        {
            "match_id": 501,
            "match_date": datetime(2025, 9, 1, 15, 0),
            "home_id": 1,
            "home_name": "Team 1",
            "away_id": 2,
            "away_name": "Team 2",
            "season": "2025_26",
            "home_score": 2,
            "away_score": 1,
            "statsapi_home_xg": 2.2,
            "statsapi_away_xg": 1.1,
            "home_won_corners": 6,
            "away_won_corners": 4,
            "total_yellow_cards": 3,
            "total_red_cards": 0,
            "referee_name": "Oliver",
            "is_played": True,
        },
        {
            "match_id": 502,
            "match_date": datetime(2025, 9, 1, 15, 0),
            "home_id": 3,
            "home_name": "Team 3",
            "away_id": 4,
            "away_name": "Team 4",
            "season": "2025_26",
            "home_score": 0,
            "away_score": 0,
            "statsapi_home_xg": 0.5,
            "statsapi_away_xg": 0.6,
            "home_won_corners": 3,
            "away_won_corners": 5,
            "total_yellow_cards": 1,
            "total_red_cards": 0,
            "referee_name": "Taylor",
            "is_played": True,
        },
        {
            "match_id": 503,
            "match_date": datetime(2025, 9, 8, 15, 0),
            "home_id": 1,
            "home_name": "Team 1",
            "away_id": 3,
            "away_name": "Team 3",
            "season": "2025_26",
            "home_score": np.nan,
            "away_score": np.nan,
            "statsapi_home_xg": np.nan,
            "statsapi_away_xg": np.nan,
            "home_won_corners": np.nan,
            "away_won_corners": np.nan,
            "total_yellow_cards": np.nan,
            "total_red_cards": np.nan,
            "referee_name": "Tierney",
            "is_played": False,
        }
    ]
    
    df_matches = pd.DataFrame(matches)
    long_df = build_team_match_history(df_matches)
    featured_long = compute_pre_match_features(long_df)
    
    # Check pre-match stats for match 503 (unplayed fixture)
    t1_unplayed = featured_long[(featured_long["team_id"] == 1) & (featured_long["match_id"] == 503)]
    t3_unplayed = featured_long[(featured_long["team_id"] == 3) & (featured_long["match_id"] == 503)]
    
    print("\nTeam 1 pre-match xg_for_roll_3 for unplayed match 503:", t1_unplayed["xg_for_roll_3"].values[0])
    print("Team 3 pre-match xg_for_roll_3 for unplayed match 503:", t3_unplayed["xg_for_roll_3"].values[0])
    
    assert t1_unplayed["xg_for_roll_3"].values[0] == 2.2, f"Expected 2.2, got {t1_unplayed['xg_for_roll_3'].values[0]}"
    assert t3_unplayed["xg_for_roll_3"].values[0] == 0.5, f"Expected 0.5, got {t3_unplayed['xg_for_roll_3'].values[0]}"
    
    # Check that in match 501 and 502, pre-match stats were NaN
    t1_m501 = featured_long[(featured_long["team_id"] == 1) & (featured_long["match_id"] == 501)]
    assert np.isnan(t1_m501["xg_for_roll_3"].values[0]), "Match 501 should be NaN for team 1"
    
    print(">>> TEST 2 PASSED: Simultaneous kickoffs and unplayed match form inheritance verified.")

if __name__ == "__main__":
    run_synthetic_team_isolation_test()
    run_simultaneous_and_unplayed_fixtures_test()
