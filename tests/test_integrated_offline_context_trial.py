"""Synthetic offline route-context integration; no Android storage claim."""
import unittest

from benchmarks.integrated_journey_trial import scorecard
from benchmarks.integrated_offline_context_trial import run_dmn


class IntegratedOfflineContextTests(unittest.TestCase):
    def test_frozen_three_case_baseline(self):
        report=run_dmn()
        self.assertEqual((report["passed"],report["failed"],report["total"]),(3,0,3))

    def test_replacement_and_rejection_have_opposite_context_results(self):
        rows={row["case_id"]:row["actual"] for row in run_dmn()["cases"]}
        self.assertFalse(rows["INTEGRATED-003-valid-replacement-invalidates-old-route-context"]["old_route_matches_active"])
        self.assertTrue(rows["INTEGRATED-003-corrupt-update-retains-route-context"]["old_route_matches_active"])
        self.assertTrue(rows["INTEGRATED-003-new-route-binds-replacement"]["new_route_matches_active"])

    def test_external_families_have_no_fabricated_score(self):
        rows=scorecard(run_dmn())["rows"]
        self.assertEqual(len(rows),13)
        self.assertTrue(all(row["score_out_of_ten"] is None for row in rows[1:]))


if __name__=="__main__":unittest.main()
