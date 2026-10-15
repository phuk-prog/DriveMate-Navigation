"""Permanent public-map preference archive regression gate (not road truth).

The archived real-UK OSM-source cases are reproducible experiment identifiers,
not independently validated legal directions or users' trip records.
"""
import json
from hashlib import sha256
from pathlib import Path
import unittest

from benchmarks.uk_preference_case_register import validate_case_register


ARCHIVE = (Path(__file__).resolve().parents[1] /
           "references/uk-route-preference-map-cases-20261015.json")
EXPECTED_SHA256 = "e8b3d5be13ca83b3e8679e8fda87d10d9ab2d152eb759b152c779b44189e4cc1"


class ArchivedUKRoutePreferenceEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.study = json.loads(ARCHIVE.read_text(encoding="utf-8"))

    def test_exact_count_and_crypto_chain_survive_future_code_changes(self):
        d = self.study
        self.assertEqual(d["schema"], "DMN-PUBLIC-UK-PREFERENCE-COMPARISON-v1")
        self.assertEqual(d["source_snapshot"], "geofabrik-260901")
        self.assertEqual(d["route_preference_pairs_checked"], 144)
        self.assertEqual(d["route_preference_pairs_with_alternates"], 139)
        self.assertEqual(d["fastest_shortest_distinct_paths"], 25)
        self.assertEqual(d["case_register_count"], 25)
        self.assertEqual(d["case_register_sha256"], EXPECTED_SHA256)
        verified = validate_case_register(d["cases"], expected_count=25)
        self.assertTrue(verified["case_register_valid"])
        self.assertEqual(verified["case_register_sha256"], EXPECTED_SHA256)

    def test_unsupported_area_and_mapped_turns_never_claim_uk_law(self):
        d = self.study
        self.assertEqual(d["areas_attempted"], 4)
        self.assertEqual(d["areas_with_mapped_restrictions_checked"], 3)
        self.assertEqual(d["areas_unsupported"], 1)
        self.assertEqual(d["mapped_restriction_pairs_checked"], 3)
        self.assertEqual(d["mapped_restriction_detours_found"], 3)
        self.assertFalse(d["independently_verified_current_road_law"])
        self.assertFalse(d["live_traffic_observed"])
        self.assertEqual(d["competitor_routes_executed"], 0)
        self.assertEqual(d["balanced_distinct_from_both"], 0)

    def test_archived_cases_retain_source_and_uncertainty_metadata(self):
        d = self.study
        self.assertRegex(d["restriction_source_sha256"], "^[a-f0-9]{64}$")
        self.assertIn("OpenStreetMap contributors", d["source_attribution"])
        for case in d["cases"]:
            self.assertEqual(case["map_snapshot"], d["source_snapshot"])
            self.assertRegex(case["map_sha256"], "^[a-f0-9]{64}$")
            self.assertNotEqual(case["fastest_route_digest"],
                                case["shortest_route_digest"])
            self.assertEqual(case["independent_current_uk_road_legality"],
                             "UNKNOWN")
            self.assertEqual(case["competitor_outcomes"], "NOT_RUN")
            self.assertTrue(case["map_only_test_case"])
            self.assertFalse(case["traffic_observed"])

    def test_no_trip_coordinates_or_raw_road_identifiers_archived(self):
        forbidden = {"source", "destination", "origin", "way_id",
                     "edge_ids", "gps", "latitude", "longitude",
                     "lat", "lon", "user", "uid", "changeset"}
        def walk(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value),
                                 "Archive contains route/person-identifying keys")
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(self.study)


if __name__ == "__main__":
    unittest.main()
