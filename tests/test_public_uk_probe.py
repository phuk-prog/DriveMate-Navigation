import unittest
from pathlib import Path
from benchmarks.public_uk_probe import _public_file, check_public_graph


SYNTHETIC = (Path(__file__).resolve().parents[1] /
             "benchmarks/fixtures/synthetic-osm-junction.xml")


class PublicUKValidationTests(unittest.TestCase):
    def test_bounded_graph_matches_two_algorithms_no_personal_inputs(self):
        result = check_public_graph(SYNTHETIC.read_bytes(),
                                    snapshot="synthetic-v1", region="fabricated",
                                    samples=1)
        self.assertTrue(result["astar_matches_dijkstra_estimated_cost"])
        self.assertFalse(result["verified_safe_for_live_navigation"])
        self.assertFalse(result["user_location_information_used"])
        self.assertEqual(result["external_engines_executed"], 0)
        self.assertEqual(result["scenario_count"], 1)
        self.assertEqual(result["route_preference_profiles_checked"],1)
        self.assertIn(result["route_preference_discriminating_coverage"],
                      ("MAP_DIVERGENCE_OBSERVED","INSUFFICIENT"))
        self.assertFalse(result["independently_verified_traffic_legality_or_lane_truth"])
        self.assertTrue(result["route_preference_graph_rules_consistent"])
        self.assertFalse(result["driver_route_legality_independently_verified"])

    def test_only_git_ignored_results_area_allowed_as_real_input(self):
        with self.assertRaises(ValueError):
            _public_file(SYNTHETIC)

    def test_invalid_scenario_count_fails(self):
        with self.assertRaises(ValueError):
            check_public_graph(SYNTHETIC.read_bytes(), snapshot="synthetic",
                               region="fabricated", samples=0)


if __name__ == "__main__":
    unittest.main()
