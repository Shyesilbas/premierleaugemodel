import unittest
from src.analytics.team_tactics import TACTICAL_METRICS, get_team_tactical_profile

import pytest

pytestmark = pytest.mark.needs_data


class TestTeamTactics(unittest.TestCase):
    def test_shots_conceded_metric_defined(self):
        self.assertIn("shots_conceded_per_match", TACTICAL_METRICS)
        metric = TACTICAL_METRICS["shots_conceded_per_match"]
        self.assertEqual(metric["label"], "İzin verilen şut")
        self.assertEqual(metric["unit"], "maç başına")

    def test_shots_conceded_in_profile(self):
        # Arsenal team_id = 1
        profile = get_team_tactical_profile(1, "2026_27")
        self.assertIn("shots_conceded_per_match", profile["metrics"])
        m = profile["metrics"]["shots_conceded_per_match"]
        self.assertIsNotNone(m["value"])
        self.assertIsNotNone(m["league_average"])
        self.assertGreater(m["value"], 0)
        self.assertGreater(m["league_average"], 0)
        self.assertEqual(m["coverage_pct"], 100.0)

    def test_redundant_metrics_removed(self):
        for key in ("outside_box_shot_share", "controlled_possession_losses", "final_third_passes", "ball_recoveries"):
            self.assertNotIn(key, TACTICAL_METRICS)

    def test_difference_matches_unrounded_comparison(self):
        profile = get_team_tactical_profile(1, "2026_27")
        for key, metric in profile["metrics"].items():
            if metric["value"] is None or metric["league_average"] is None:
                continue
            decimals = TACTICAL_METRICS[key].get("decimals", 1)
            tolerance = 10 ** -decimals
            self.assertAlmostEqual(
                metric["difference"], metric["value"] - metric["league_average"], delta=tolerance, msg=key
            )

    def test_team_excluded_from_league_comparison(self):
        profile = get_team_tactical_profile(1, "2026_27")
        self.assertEqual(profile["metrics"]["possession"]["league_teams"], 19)

    def test_new_metrics_and_formations(self):
        profile = get_team_tactical_profile(1, "2026_27")
        for key in (
            "xg_per_match",
            "xga_per_match",
            "conceded_inside_box_share",
            "pen_area_entries",
            "losses_per_100_touches",
            "fouls_committed",
            "yellow_cards",
        ):
            self.assertIsNotNone(profile["metrics"][key]["value"], key)
        self.assertTrue(profile["formations"])
        self.assertRegex(profile["formations"][0]["formation"], r"^\d(-\d)+$")


if __name__ == "__main__":
    unittest.main()
