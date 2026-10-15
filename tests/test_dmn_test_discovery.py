"""Unit tests of the adaptive study process, not navigation-system runs."""
import json
from copy import deepcopy
import unittest
from tools.dmn_test_discovery import MATRIX_PATH, batch_from_public_smoke, propose

class AdaptiveStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    def observation(self):
        return {
            "case_id": "nonpersonal-sample", "category_id": "NAV-008",
            "check_id": "NAV-008-A", "outcome": "UNKNOWN", "signal": "coverage_gap",
            "failure_signature": "missing_official_legal_truth", "reproduction": "Replay on nonpersonal, pinned public geometry",
            "expected": "Independently justified restriction verdict",
            "observed": "Legal ground truth missing", "oracle": None,
            "evidence_ref": "https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38726726953",
            "new_test": "Add separately supported legal turn evidence"
        }
    def batch(self, items):
        return {"schema_version": 1, "source_kind": "public_nonpersonal",
                "run_url": "https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38726726953",
                "observations": items}
    def test_unknown_becomes_proposal_not_failure_or_score(self):
        report = propose(self.batch([self.observation()]), self.matrix)
        self.assertEqual(report["new_candidate_count"], 1)
        one = report["candidates"][0]
        self.assertTrue(one["requires_independent_truth"])
        self.assertEqual(one["observed_outcome"], "UNKNOWN")
        self.assertEqual(one["status"], "candidate_needs_review")
        self.assertFalse(report["automatically_added_to_production_or_rankings"])
        self.assertNotIn("score", one)
    def test_same_problem_in_two_reruns_is_one_test(self):
        a = self.observation()
        b = deepcopy(a)
        b["case_id"] = "different-repetition"
        r = propose(self.batch([a,b]), self.matrix)
        self.assertEqual(r["new_candidate_count"], 1)
        self.assertEqual(len(r["duplicates_collapsed"]), 1)
        r2 = propose(self.batch([a]), self.matrix, existing=r["candidates"])
        self.assertEqual(r2["new_candidate_count"], 0)
    def test_clean_pass_does_not_generate_failure(self):
        a = self.observation()
        a["outcome"], a["signal"] = "PASS", "coverage_gap"
        self.assertEqual(propose(self.batch([a]), self.matrix)["new_candidate_count"], 0)
    def test_verified_failure_requires_oracle(self):
        a = self.observation()
        a["outcome"] = "FAIL"
        with self.assertRaisesRegex(ValueError, "FAIL requires"):
            propose(self.batch([a]), self.matrix)
        a["oracle"] = "independently checked official sign"
        self.assertEqual(propose(self.batch([a]), self.matrix)["candidates"][0]["observed_outcome"], "FAIL")
    def test_new_category_can_be_proposed_without_changing_baseline(self):
        a = self.observation()
        del a["category_id"]
        del a["check_id"]
        a["proposed_category"] = "Unexpected GPS source spoofing defense"
        a["proposed_group"] = "Future positioning"
        r = propose(self.batch([a]), self.matrix)
        self.assertTrue(r["candidates"][0]["requires_category_extension"])
        self.assertEqual(r["baseline_categories"], 72)
    def test_prohibited_personal_trace_fields(self):
        a = self.observation()
        a["gps_trace"] = [{"lat": 53.0, "lon": -2.2}]
        with self.assertRaisesRegex(ValueError,"personal"):
            propose(self.batch([a]), self.matrix)
    def test_wrong_existing_check_mapping_is_rejected(self):
        a = self.observation()
        a["check_id"] = "NAV-009-A"
        with self.assertRaisesRegex(ValueError,"selected category"):
            propose(self.batch([a]), self.matrix)
    def test_smoke_gap_is_not_claimed_as_illegal_turn(self):
        smoke = {"classification": "public-road-experimental-not-legality-verified",
                 "node_via_forbidden_turn_pairs": 0, "scenario_count": 8}
        batch = batch_from_public_smoke(smoke,
            "https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38726726953")
        r = propose(batch, self.matrix)
        self.assertEqual(r["new_candidate_count"], 1)
        self.assertEqual(r["candidates"][0]["observed_outcome"], "UNKNOWN")
        smoke["node_via_forbidden_turn_pairs"] = 1
        self.assertEqual(propose(batch_from_public_smoke(smoke, batch["run_url"]), self.matrix)["new_candidate_count"], 0)

if __name__ == "__main__":
    unittest.main()
