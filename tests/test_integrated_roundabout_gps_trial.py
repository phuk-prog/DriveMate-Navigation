"""Synthetic integrated roundabout/GPS controls; no field or app evidence."""
import unittest

from benchmarks.integrated_journey_trial import scorecard
from benchmarks.integrated_roundabout_gps_trial import run_dmn


class IntegratedRoundaboutGpsTests(unittest.TestCase):
    def test_frozen_three_case_baseline(self):
        report=run_dmn()
        self.assertEqual((report["passed"],report["failed"],report["total"]),(3,0,3))

    def test_uncertain_and_stale_fixes_never_emit_guidance_or_arrival(self):
        rows={row["case_id"]:row for row in run_dmn()["cases"]}
        for case_id in ("INTEGRATED-002-weak-gps-withholds","INTEGRATED-002-stale-gps-rejected"):
            actual=rows[case_id]["actual"]
            self.assertEqual(actual["instruction_phase"],"WITHHOLD")
            self.assertNotIn(actual["arrival_state"],("CANDIDATE","ARRIVED"))

    def test_static_references_remain_unranked(self):
        rows=scorecard(run_dmn())["rows"]
        self.assertEqual(len(rows),13)
        self.assertTrue(all(row["rank"] is None for row in rows[1:]))


if __name__=="__main__":unittest.main()
