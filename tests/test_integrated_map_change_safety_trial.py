"""Preserve the known active-route/map-change integration failure."""
import unittest

from benchmarks.integrated_journey_trial import scorecard
from benchmarks.integrated_map_change_safety_trial import run_dmn


class IntegratedMapChangeSafetyTests(unittest.TestCase):
    def test_frozen_baseline_retains_one_safety_failure(self):
        report=run_dmn()
        self.assertEqual((report["passed"],report["failed"],report["total"]),(2,1,3))
        failed=[case for case in report["cases"] if case["outcome"]=="FAIL"]
        self.assertEqual([case["case_id"] for case in failed],
                         ["INTEGRATED-004-valid-replacement-invalidates-active-route"])
        self.assertEqual(failed[0]["failures"],["controller_active","installed_route"])

    def test_rejected_update_and_explicit_stop_controls_pass(self):
        rows={row["case_id"]:row for row in run_dmn()["cases"]}
        self.assertEqual(rows["INTEGRATED-004-rejected-update-retains-active-route"]["outcome"],"PASS")
        self.assertEqual(rows["INTEGRATED-004-explicit-stop-fallback"]["outcome"],"PASS")

    def test_external_results_are_not_invented(self):
        rows=scorecard(run_dmn())["rows"]
        self.assertEqual(len(rows),13)
        self.assertTrue(all(row["score_out_of_ten"] is None for row in rows[1:]))


if __name__=="__main__":unittest.main()
