"""Test inference logic and dynamic home/away share splits."""

import unittest
from fastapi.testclient import TestClient
from src.api.server import app


class TestInferenceLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_predict_shares_sum_and_bounds(self):
        """Verify dynamic shares sum to 1.0 and stay within valid bounds."""
        response = self.client.get("/api/predict?home_id=1&away_id=2")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check outcome probabilities sum to ~100%
        outcome = data.get("outcome", {})
        prob_sum = outcome.get("home_win_pct", 0) + outcome.get("draw_pct", 0) + outcome.get("away_win_pct", 0)
        self.assertAlmostEqual(prob_sum, 100.0, delta=1.0)

        # Check sub-markets
        markets = ["corners", "cards", "throws", "saves", "offsides"]
        for market in markets:
            if market in data:
                m_data = data[market]
                exp_total = m_data.get("expected_total")
                exp_home = m_data.get("expected_home")
                exp_away = m_data.get("expected_away")

                self.assertIsNotNone(exp_total, f"Missing expected_total in {market}")
                self.assertIsNotNone(exp_home, f"Missing expected_home in {market}")
                self.assertIsNotNone(exp_away, f"Missing expected_away in {market}")

                # Home + Away must equal Total (within rounding error)
                self.assertAlmostEqual(
                    exp_home + exp_away, exp_total, delta=0.2,
                    msg=f"{market} breakdown ({exp_home} + {exp_away}) != total ({exp_total})"
                )

                # Positive values
                self.assertGreater(exp_home, 0.0)
                self.assertGreater(exp_away, 0.0)


if __name__ == "__main__":
    unittest.main()
