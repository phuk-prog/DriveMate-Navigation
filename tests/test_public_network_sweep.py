"""Aggregate coverage accounting; no public map needed for unit checks."""
import unittest

from benchmarks.public_network_sweep import PUBLIC_AREAS, summarise
from tools.public_osm_extract import parse_bbox


class PublicNetworkSweepTests(unittest.TestCase):
    def test_each_independently_selected_area_is_bounded_and_unique(self):
        self.assertEqual(len({slug for slug, _ in PUBLIC_AREAS}), len(PUBLIC_AREAS))
        for slug, bbox in PUBLIC_AREAS:
            self.assertTrue(slug)
            self.assertEqual(parse_bbox(bbox), bbox)

    def test_zero_diversity_is_not_marked_success(self):
        result = summarise([
            {"area": "one", "status": "SUPPORTED",
             "metrics": {"route_preference_discriminating_coverage": "INSUFFICIENT"}},
            {"area": "two", "status": "UNSUPPORTED"}])
        self.assertEqual(result["result"], "INSUFFICIENT_OR_UNSUPPORTED")
        self.assertEqual(result["areas_supported"], 1)
        self.assertEqual(result["areas_unsupported"], 1)
        self.assertEqual(result["areas_with_observed_fastest_shortest_divergence"], 0)
        self.assertFalse(result["independently_verified_legal_or_lane_truth"])
        self.assertEqual(result["external_engines_executed"], 0)

    def test_only_measured_diversity_counts(self):
        report = summarise([
            {"area": "one", "status": "SUPPORTED",
             "metrics": {"route_preference_discriminating_coverage": "MAP_DIVERGENCE_OBSERVED"}},
            {"area": "two", "status": "SUPPORTED",
             "metrics": {"route_preference_discriminating_coverage": "INSUFFICIENT"}}])
        self.assertEqual(report["areas_with_observed_fastest_shortest_divergence"], 1)
        self.assertEqual(report["result"], "MAP_DIVERGENCE_OBSERVED")
        self.assertFalse(report["independently_verified_legal_or_lane_truth"])

    def test_missing_or_invalid_status_is_rejected(self):
        for cases in ([], [{"area": "unknown"}], [{"status": "PASS", "area": "x"}]):
            with self.assertRaises(ValueError):
                summarise(cases)


if __name__ == "__main__":
    unittest.main()
