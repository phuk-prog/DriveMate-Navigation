"""Archive replay protects map-only research against silent route/cost drift."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from benchmarks.uk_archive_replay import COUNTERS, verify_archived_replay


ARCHIVE = json.loads((Path(__file__).resolve().parents[1] /
    "references/uk-route-preference-map-cases-20261015.json").read_text(encoding="utf-8"))


def matching_study():
    saved = deepcopy(ARCHIVE)
    study = {observed: saved[expected] for observed, expected in COUNTERS}
    study.update({
        "case_register_integrity_validated": True,
        "case_register_all_cases_have_unknown_legality": True,
        "independent_road_legality_verified": False,
        "external_engines_executed": 0,
        "discriminating_case_register": deepcopy(saved["cases"]),
    })
    return study


class ArchivedPublicRoadReplayTests(unittest.TestCase):
    def test_all_twenty_five_pinned_cases_match_when_reproduced(self):
        result = verify_archived_replay(matching_study(), ARCHIVE)
        self.assertTrue(result["replay_matches_pinned_archive"])
        self.assertEqual(result["matched_cases"], 25)
        self.assertEqual(result["matched_route_preference_pairs"], 144)
        self.assertEqual(result["matched_distinct_fastest_shortest"], 25)
        self.assertFalse(result["independent_uk_road_legality_verified"])

    def test_same_ids_but_different_selected_route_digest_fail(self):
        result = matching_study()
        result["discriminating_case_register"][0]["fastest_route_digest"] = "dmn:drift"
        with self.assertRaisesRegex(AssertionError, "fingerprints"):
            verify_archived_replay(result, ARCHIVE)

    def test_same_ids_but_different_estimated_duration_fail(self):
        result = matching_study()
        result["discriminating_case_register"][0]["fastest_estimated_seconds"] += 2
        with self.assertRaisesRegex(AssertionError, "costs"):
            verify_archived_replay(result, ARCHIVE)

    def test_reordering_cases_fails_even_when_id_checksum_matches(self):
        result = matching_study()
        result["discriminating_case_register"].reverse()
        with self.assertRaises(AssertionError):
            verify_archived_replay(result, ARCHIVE)

    def test_missing_case_and_fake_success_counter_fail(self):
        result = matching_study()
        result["discriminating_case_register"].pop()
        with self.assertRaises(AssertionError):
            verify_archived_replay(result, ARCHIVE)

    def test_incomplete_neighborhood_must_not_be_hidden(self):
        result = matching_study()
        result["unsupported_or_incomplete_neighborhoods"] = 0
        with self.assertRaisesRegex(AssertionError, "unsupported_or_incomplete"):
            verify_archived_replay(result, ARCHIVE)

    def test_source_snapshot_and_restrictions_cannot_drift(self):
        for field in ("source_snapshot", "restriction_source_sha256"):
            with self.subTest(field=field):
                result = matching_study()
                result[field] = "different-source"
                with self.assertRaises(AssertionError):
                    verify_archived_replay(result, ARCHIVE)

    def test_complete_paired_osrm_observations_preserve_archive_truth(self):
        from benchmarks.uk_osrm_case_comparison import (
            compare_osrm_case, validate_osrm_case_results)
        result = matching_study()
        cases = result["discriminating_case_register"]
        def reference(_url):
            return {"code": "Ok",
                    "waypoints": [{"distance": 1.0}, {"distance": 2.0}],
                    "routes": [{"distance": 200.0, "duration": 20.0}]}
        rows = [compare_osrm_case(c, (53.4, -2.2), (53.41, -2.19),
                                  request=reference) for c in cases]
        result["external_engines_executed"] = 1
        result["osrm_case_comparison"] = validate_osrm_case_results(
            cases, rows, snapshot=ARCHIVE["source_snapshot"])
        checked = verify_archived_replay(result, ARCHIVE)
        self.assertTrue(checked["replay_matches_pinned_archive"])
        self.assertEqual(checked["paired_osrm_cases"], 25)
        self.assertEqual(checked["external_competitors_executed"], 1)
        self.assertFalse(result["osrm_case_comparison"]["route_quality_ranking_valid"])

    def test_partial_osrm_evidence_cannot_pass_pinned_archive(self):
        from benchmarks.uk_osrm_case_comparison import (
            compare_osrm_case, validate_osrm_case_results)
        result = matching_study()
        cases = result["discriminating_case_register"]
        result["external_engines_executed"] = 1
        with self.assertRaisesRegex(AssertionError, "paired evidence"):
            verify_archived_replay(result, ARCHIVE)
        rows = [compare_osrm_case(c, (53.4, -2.2), (53.41, -2.19),
                                  request=lambda _: {"code": "NoRoute"})
                for c in cases]
        comparison = validate_osrm_case_results(
            cases, rows, snapshot=ARCHIVE["source_snapshot"])
        comparison["case_results"].pop()
        result["osrm_case_comparison"] = comparison
        with self.assertRaises(AssertionError):
            verify_archived_replay(result, ARCHIVE)

    def test_no_independent_legality_or_competitor_score_inferred(self):
        result = matching_study()
        result["independent_road_legality_verified"] = True
        with self.assertRaisesRegex(AssertionError, "verified road truth"):
            verify_archived_replay(result, ARCHIVE)
        result = matching_study()
        result["external_engines_executed"] = 1
        with self.assertRaises(AssertionError):
            verify_archived_replay(result, ARCHIVE)

    def test_missing_metadata_does_not_count_as_reproduction(self):
        result = matching_study()
        del result["neighborhoods_prepared"]
        with self.assertRaisesRegex(AssertionError, "missing"):
            verify_archived_replay(result, ARCHIVE)


if __name__ == "__main__":
    unittest.main()
