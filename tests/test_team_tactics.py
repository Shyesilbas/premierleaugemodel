import unittest
from src.analytics.team_tactics import TACTICAL_METRICS, get_team_tactical_profile, load_team_match_rows

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


if __name__ == "__main__":
    unittest.main()
