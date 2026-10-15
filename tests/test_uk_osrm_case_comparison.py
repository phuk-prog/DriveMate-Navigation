"""Same-source, same-endpoint local OSRM comparison contract tests."""
from __future__ import annotations

from copy import deepcopy
import unittest

from benchmarks.uk_osrm_case_comparison import (
    compare_osrm_case, validate_osrm_case_results)


def original():
    return {
        "case_id": "dmn-mapcase-test123",
        "map_only_test_case": True,
        "independent_current_uk_road_legality": "UNKNOWN",
        "competitor_outcomes": "NOT_RUN",
        "map_snapshot": "geofabrik-test",
        "fastest_length_m": 120.5,
        "fastest_estimated_seconds": 12.0,
    }


def response(origin=2.0, finish=3.0):
    return {
        "code": "Ok",
        "waypoints": [{"distance": origin}, {"distance": finish}],
        "routes": [{"distance": 133.3, "duration": 15.3}],
    }


def fake_request(url):
    if not url.startswith("http://127.0.0.1:5000/route/v1/driving/"):
        raise AssertionError("Must use local reference only")
    return response()


class SameCaseLocalOSRMTests(unittest.TestCase):
    def setUp(self):
        self.case = original()
        self.origin = (53.4, -2.2)
        self.dest = (53.405, -2.19)

    def score(self, responder=fake_request):
        return compare_osrm_case(self.case, self.origin, self.dest, request=responder)

    def test_same_source_endpoint_pair_and_unverified_scores(self):
        row = self.score()
        self.assertEqual(row["status"], "ENDPOINTS_NEAR_DIFFERENT_PROFILES")
        self.assertEqual(row["osrm_distance_m"], 133.3)
        self.assertFalse(row["driver_navigation_quality_comparable"])
        self.assertEqual(row["independent_current_uk_road_legality"], "UNKNOWN")
        self.assertNotIn("coordinates", row)
        self.assertNotIn("origin", row)
        self.assertNotIn("destination", row)
        summary = validate_osrm_case_results([self.case], [row],
                                             snapshot="geofabrik-test")
        self.assertTrue(summary["complete_same_case_execution"])
        self.assertEqual(summary["cases_attempted"], 1)
        self.assertFalse(summary["route_quality_ranking_valid"])

    def test_far_away_osrm_snap_is_explicitly_unmatched(self):
        row = self.score(lambda _: response(origin=25.0))
        self.assertEqual(row["status"], "SNAP_MISMATCH_NOT_COMPARABLE")
        summary = validate_osrm_case_results([self.case], [row],
                                             snapshot="geofabrik-test")
        self.assertEqual(summary["osrm_routes_with_both_endpoint_snaps_within_15m"], 0)

    def test_osrm_no_route_and_no_segment_are_not_wins(self):
        for code in ("NoRoute", "NoSegment"):
            with self.subTest(code=code):
                row = self.score(lambda _: {"code": code})
                self.assertNotIn("osrm_distance_m", row)
                summary = validate_osrm_case_results([self.case], [row],
                                                     snapshot="geofabrik-test")
                self.assertFalse(summary["route_quality_ranking_valid"])

    def test_bad_osrm_shape_fails_not_ignored(self):
        for payload in ({"code": "Ok"}, {"code": "Bogus"},
                        {"code": "Ok", "routes": [{}], "waypoints": []},
                        {"code": "Ok", "routes": [{"distance": -1, "duration": 2}],
                         "waypoints": [{"distance": 0}, {"distance": 1}]}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.score(lambda _: payload)

    def test_incomplete_case_set_fails(self):
        with self.assertRaisesRegex(AssertionError, "Missing"):
            validate_osrm_case_results([self.case], [], snapshot="geofabrik-test")

    def test_duplicate_case_refused(self):
        row = self.score()
        with self.assertRaises(AssertionError):
            validate_osrm_case_results([self.case, self.case],
                                       [row, row], snapshot="geofabrik-test")

    def test_reordered_ids_refused(self):
        other = dict(self.case, case_id="dmn-mapcase-other")
        rows = [self.score(), compare_osrm_case(other, self.origin, self.dest,
                                               request=fake_request)]
        with self.assertRaises(AssertionError):
            validate_osrm_case_results([self.case, other], rows[::-1],
                                       snapshot="geofabrik-test")

    def test_forged_legal_truth_and_profile_match_rejected(self):
        row = self.score()
        row["driver_navigation_quality_comparable"] = True
        with self.assertRaises(AssertionError):
            validate_osrm_case_results([self.case], [row], snapshot="geofabrik-test")

    def test_mismatched_snapshot_and_snap_class_refused(self):
        row = self.score()
        row["same_map_snapshot"] = "another-era"
        with self.assertRaises(AssertionError):
            validate_osrm_case_results([self.case], [row], snapshot="geofabrik-test")
        row = self.score()
        row["origin_snap_m"] = 50.0
        with self.assertRaisesRegex(AssertionError, "snap"):
            validate_osrm_case_results([self.case], [row], snapshot="geofabrik-test")

    def test_large_same_endpoint_distance_gap_is_review_not_failure(self):
        from benchmarks.uk_osrm_case_comparison import distance_discrepancy_triage
        rows = [self.score()]
        rows[0]["osrm_distance_m"] = 40.0  # 80.5m deviation
        review = distance_discrepancy_triage(rows)
        self.assertEqual(review["high_gap_case_count"], 1)
        self.assertEqual(review["review_cases_in_priority_order"][0]["case_id"],
                         self.case["case_id"])
        self.assertEqual(review["independently_verified_navigation_failures"], 0)
        self.assertFalse(review["ranking_supported"])

    def test_tiny_distance_gap_does_not_trigger_investigation(self):
        row = self.score()
        row["osrm_distance_m"] = 121.0
        summary = validate_osrm_case_results([self.case], [row],
                                             snapshot="geofabrik-test")
        self.assertEqual(summary["distance_discrepancy_review"]["high_gap_case_count"], 0)

    def test_no_route_or_far_snap_never_looks_like_distance_gap_proof(self):
        from benchmarks.uk_osrm_case_comparison import distance_discrepancy_triage
        no_route = self.score(lambda _: {"code": "NoRoute"})
        far = self.score(lambda _: response(origin=30.0))
        self.assertEqual(distance_discrepancy_triage(
            [no_route, far])["high_gap_case_count"], 0)

    def test_distance_gap_review_sorted_in_priority_order(self):
        from benchmarks.uk_osrm_case_comparison import distance_discrepancy_triage
        a = self.score()
        b = deepcopy(a)
        b["case_id"] = "dmn-mapcase-different"
        a["osrm_distance_m"] = 60.0
        b["osrm_distance_m"] = 10.0
        report = distance_discrepancy_triage([a, b])
        self.assertEqual(report["high_gap_case_count"], 2)
        self.assertEqual(report["review_cases_in_priority_order"][0]["case_id"],
                         b["case_id"])

    def test_original_case_identity_required(self):
        self.case["competitor_outcomes"] = "PASS"
        with self.assertRaises(ValueError):
            self.score()

    def test_finite_measured_numbers_required(self):
        row = self.score()
        row["osrm_estimated_seconds"] = float("nan")
        with self.assertRaises(ValueError):
            validate_osrm_case_results([self.case], [row], snapshot="geofabrik-test")


if __name__ == "__main__":
    unittest.main()
