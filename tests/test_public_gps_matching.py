"""Synthetic OSM fixture contract for a public-road-geometry replay harness."""
import unittest
from pathlib import Path
from benchmarks.public_gps_matching import evaluate

RAW=(Path(__file__).resolve().parents[1]/
    "benchmarks/fixtures/synthetic-osm-junction.xml").read_bytes()

class PublicGPSMatchingHarnessTests(unittest.TestCase):
    def test_simulated_fix_variants_with_no_device_claim(self):
        report=evaluate(RAW,snapshot="synthetic fixture only",limit=5)
        self.assertGreaterEqual(report["sampled_distinct_directed_edges"],5)
        self.assertEqual(report["normal_fix_cases"],3*report["sampled_distinct_directed_edges"])
        self.assertEqual(report["adversarial_cases"],3*report["sampled_distinct_directed_edges"])
        self.assertEqual(report["adversarial_confident_matches"],0)
        self.assertEqual(report["actual_phone_GPS_measurements"],0)
        self.assertIsNone(report["navigation_score"])
    def test_invalid_sample_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(RAW,snapshot="synthetic",limit=0)
        with self.assertRaises(ValueError):
            evaluate(RAW,snapshot="synthetic",limit=101)


    def test_bidirectional_and_recovery_cohorts_have_truthful_denominators(self):
        report=evaluate(RAW,snapshot="synthetic fixture only",limit=8)
        self.assertEqual(report["bidirectional_moving_total"],
                         report["bidirectional_moving_correct"]+
                         report["bidirectional_moving_wrong"]+
                         report["bidirectional_moving_withheld"])
        self.assertEqual(report["post_spike_recovery_cases"],
                         report["post_spike_recovery_correct"]+
                         report["post_spike_recovery_wrong"]+
                         report["post_spike_recovery_withheld"])
        self.assertEqual(report["post_spike_recovery_cases"],
                         report["post_spike_rejected_correctly"])
        self.assertEqual(report["bidirectional_stopped_confident"],0)

if __name__=="__main__":
    unittest.main()
