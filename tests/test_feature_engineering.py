import unittest
import pandas as pd
import numpy as np

from src.features.build_features import (
    _run_strength,
    _team_strength,
    add_interaction_features,
    fill_feature_priors,
    build_prediction_row,
    compute_team_states,
    build_team_match_history,
)


class TestFeatureEngineering(unittest.TestCase):
    def test_venue_elo_tracks_home_and_away(self):
        # Create a small toy dataframe of matches
        df = pd.DataFrame([
            {"match_id": 1, "match_date": pd.Timestamp("2024-08-10"), "season": "2024_25",
             "home_id": 1, "away_id": 2, "home_score": 3.0, "away_score": 0.0, "is_played": True},
            {"match_id": 2, "match_date": pd.Timestamp("2024-08-17"), "season": "2024_25",
             "home_id": 2, "away_id": 1, "home_score": 1.0, "away_score": 1.0, "is_played": True},
        ])
        pre, state = _run_strength(df)

        self.assertIn("elo_venue_home", pre.columns)
        self.assertIn("elo_venue_away", pre.columns)
        self.assertIn("elo_venue_diff", pre.columns)

        # After match 1, home team 1 won 3-0, so its home venue Elo should increase above 1500
        self.assertGreater(state["elo_home_venue"][1], 1500.0)
        # Away team 2 lost 3-0, so its away venue Elo should decrease below 1500
        self.assertLess(state["elo_away_venue"][2], 1500.0)

    def test_exp_match_xg_interaction(self):
        df = pd.DataFrame([{
            "home_xg_for_roll_10": 1.8,
            "away_xg_against_roll_10": 1.4,
            "away_xg_for_roll_10": 1.2,
            "home_xg_against_roll_10": 1.0,
            "elo_diff": 50.0,
            "elo_venue_diff": 40.0,
            "ppg_diff": 0.5,
            "gdpg_diff": 0.8,
        }])
        out = add_interaction_features(df)
        self.assertIn("exp_match_xg_10", out.columns)
        self.assertIn("xg_diff_10", out.columns)
        self.assertIn("abs_xg_diff_10", out.columns)
        self.assertIn("abs_elo_venue_diff", out.columns)

        # exp_home_xg = (1.8 + 1.4) / 2 = 1.6
        # exp_away_xg = (1.2 + 1.0) / 2 = 1.1
        # exp_match_xg = 1.6 + 1.1 = 2.7
        self.assertAlmostEqual(out["exp_match_xg_10"].iloc[0], 2.7)
        self.assertAlmostEqual(out["xg_diff_10"].iloc[0], 0.5)
        self.assertAlmostEqual(out["abs_xg_diff_10"].iloc[0], 0.5)
        self.assertAlmostEqual(out["abs_elo_venue_diff"].iloc[0], 40.0)


if __name__ == "__main__":
    unittest.main()
