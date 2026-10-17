"""Synthetic integration evidence controls; no app or real-road claim."""
import unittest

from benchmarks.integrated_journey_trial import run_dmn, scorecard


class IntegratedJourneyTrialTests(unittest.TestCase):
    def test_frozen_three_case_baseline(self):
        report=run_dmn()
        self.assertEqual((report["passed"],report["failed"],report["total"]),(3,0,3))
        self.assertEqual([case["outcome"] for case in report["cases"]],["PASS"]*3)

    def test_all_families_and_no_mocked_external_rank(self):
        rows=scorecard(run_dmn())["rows"]
        self.assertEqual(len(rows),13)
        self.assertEqual((rows[0]["system"],rows[0]["score_out_of_ten"]),("DMN",10))
        self.assertTrue(all(row["rank"] is None for row in rows[1:]))
        self.assertTrue(all(case["outcome"] in ("UNSUPPORTED","NOT_RUN")
                            for row in rows[1:] for case in row["cases"]))


if __name__=="__main__":unittest.main()
