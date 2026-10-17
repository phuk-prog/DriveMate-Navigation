import unittest
from benchmarks.gps_progress_safety_baseline import execute

class GPSProgressSafetyBaselineTests(unittest.TestCase):
    def test_frozen_case_count_and_oracle(self):
        report=execute()
        self.assertEqual(report["total"],10)
        self.assertEqual(len(report["oracle_sha256"]),64)
    def test_baseline_preserves_exact_reverse_direction_coverage_failure(self):
        report=execute()
        failed=[x["case_id"] for x in report["cases"] if x["outcome"]=="FAIL"]
        self.assertEqual(failed,["reverse_directed_progress"])
        self.assertEqual((report["passed"],report["total"]),(9,10))
    def test_external_stateful_comparison_is_not_invented(self):
        report=execute()
        self.assertEqual(report["external_engines_executed"],0)
        self.assertFalse(report["independent_real_world_truth"])
