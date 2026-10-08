import unittest
from backend.engine.optimizer import optimize_lineup


class OptimizerHighSourceTests(unittest.TestCase):
    def test_production_predictor_high_field(self):
        players = [
            {"player_id": "q", "position": "QB", "projection": {"median_fantasy_points": 22, "low": 10, "high": 33}},
            {"player_id": "rb", "position": "RB", "projection": {"median_fantasy_points": 15, "low": 8, "high": 25}},
        ]
        result = optimize_lineup(players, ["QB", "RB"])
        self.assertEqual(result["median_points"], 37)
        self.assertEqual(result["high_points"], 58)
        self.assertEqual([a["high_fantasy_points"] for a in result["assignment"]], [33, 25])

    def test_legacy_alias_still_supported(self):
        result = optimize_lineup([{"player_id": "q", "position": "QB", "projection": {"median_fantasy_points": 20, "high_fantasy_points": 31}}], ["QB"])
        self.assertEqual(result["high_points"], 31)

    def test_missing_high_does_not_invent_total(self):
        result = optimize_lineup([{"player_id": "q", "position": "QB", "projection": {"median_fantasy_points": 20}}], ["QB"])
        self.assertIsNone(result["high_points"])

    def test_median_selection_unchanged(self):
        players = [
            {"player_id": "q1", "position": "QB", "projection": {"median_fantasy_points": 20, "high": 25}},
            {"player_id": "q2", "position": "QB", "projection": {"median_fantasy_points": 19, "high": 45}},
        ]
        result = optimize_lineup(players, ["QB"])
        self.assertEqual(result["assignment"][0]["player_id"], "q1")
        self.assertEqual(result["high_points"], 25)


if __name__ == "__main__":
    unittest.main()
