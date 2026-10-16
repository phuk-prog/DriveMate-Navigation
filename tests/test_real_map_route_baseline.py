import unittest

from benchmarks.real_map_route_baseline import geometry_length, judge, numeric, scorecard


class RealMapRouteBaselineTests(unittest.TestCase):
    def test_judge_requires_complete_timed_route(self):
        case = {"id": "A", "start": [53.0, -2.0], "end": [53.001, -2.0]}
        row = judge(case, {"status": "ROUTE", "points": [case["start"], case["end"]],
                           "distance_m": 111.0, "duration_s": 10.0}, 1.25)
        self.assertEqual("PASS", row["outcome"])
        self.assertEqual(1.25, row["calculation_ms"])

    def test_missing_duration_fails(self):
        case = {"id": "A", "start": [53.0, -2.0], "end": [53.001, -2.0]}
        row = judge(case, {"status": "ROUTE", "points": [case["start"], case["end"]]}, 1.0)
        self.assertEqual("FAIL", row["outcome"])
        self.assertIn("positive_finite_duration", row["failures"])

    def test_scorecard_does_not_rank_incomplete_engine(self):
        base = {"test_id": "ROUTE-003", "system": "DMN", "manifest_sha256": "a",
                "map_xml_sha256": "b", "passed": 3, "failed": 0, "unresolved": 0,
                "judged_cases": 3, "total_cases": 3, "median_calculation_ms": 1.0,
                "cases": [{"outcome": "PASS"}] * 3}
        board = scorecard([base])
        self.assertEqual(10.0, board["rows"][0]["score_out_of_ten"])
        self.assertTrue(all(r["score_out_of_ten"] is None for r in board["rows"][1:]))

    def test_geometry_length_is_positive(self):
        self.assertGreater(geometry_length([[53.0, -2.0], [53.001, -2.0]]), 100)

    def test_provider_numeric_strings_are_normalized(self):
        self.assertEqual(12.5, numeric("12.5"))
        self.assertIsNone(numeric("unknown"))
        self.assertIsNone(numeric(True))


if __name__ == "__main__":
    unittest.main()
