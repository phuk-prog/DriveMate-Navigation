"""Test the scoring/evidence contracts; synthetic fixture not field truth."""
from pathlib import Path
import unittest

from benchmarks.public_temporal_gps import evaluate, verify_nonregression

RAW=(Path(__file__).resolve().parents[1]/
     "benchmarks/fixtures/synthetic-osm-junction.xml").read_bytes()

class TemporalBenchmarkTests(unittest.TestCase):
    def test_same_case_denominators_and_no_claimed_field_accuracy(self):
        report=evaluate(RAW,snapshot="synthetic unit fixture",limit=8)
        n=report["same_candidate_journeys"]
        self.assertGreater(n,0)
        self.assertEqual(n,report["single_correct"]+report["single_confident_wrong"]+report["single_withheld"])
        self.assertEqual(n,report["temporal_correct"]+report["temporal_confident_wrong"]+report["temporal_withheld"])
        self.assertEqual(report["implausible_speed_rejected"],n)
        self.assertEqual(report["weak_fix_safely_withheld"],n)
        self.assertIsNone(report["score_out_of_ten"])
        self.assertEqual(report["actual_phone_GPS_measurements"],0)
        self.assertEqual(len(report['case_diagnostics']), n)
        self.assertEqual(len({c['case_id'] for c in report['case_diagnostics']}), n)
    def test_bad_limit(self):
        with self.assertRaises(ValueError):
            evaluate(RAW,snapshot="synthetic",limit=0)


    def test_confidently_wrong_regression_blocks_comparison(self):
        fake={"same_candidate_journeys":4,"single_correct":2,
              "single_confident_wrong":0,"single_withheld":2,
              "temporal_correct":3,"temporal_confident_wrong":1,
              "temporal_withheld":0}
        with self.assertRaisesRegex(AssertionError,"wrong-road"):
            verify_nonregression(fake)
    def test_wrong_denominator_is_not_reported_as_success(self):
        fake={"same_candidate_journeys":4,"single_correct":2,
              "single_confident_wrong":0,"single_withheld":2,
              "temporal_correct":4,"temporal_confident_wrong":0,
              "temporal_withheld":1}
        with self.assertRaisesRegex(AssertionError,"denominators"):
            verify_nonregression(fake)

if __name__=="__main__":
    unittest.main()
