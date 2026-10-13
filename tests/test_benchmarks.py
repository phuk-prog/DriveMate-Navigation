import json
from pathlib import Path
import unittest

from benchmarks.run import measure


class BenchmarkIntegrityTests(unittest.TestCase):
    def test_synthetic_benchmark_reports_no_competitor_claim(self):
        result = measure(3)
        self.assertEqual(result["competitor_comparisons"], 0)
        self.assertFalse(result["benchmark_valid_for_real_world"])
        self.assertFalse(result["data_is_real_world"])
        self.assertEqual(result["route_edge_ids"], ["approach","legal","merge","finish"])

    def test_all_nine_external_candidates_are_unintegrated(self):
        config = json.loads((Path(__file__).resolve().parents[1] / "benchmarks/reference-engines.json").read_text())
        self.assertEqual(len(config["candidate_engines"]), 9)
        self.assertTrue(all(x["status"] != "verified" for x in config["candidate_engines"]))

    def test_invalid_benchmark_repetitions_rejected(self):
        for repetitions in (0, -1, 100001):
            with self.assertRaises(ValueError):
                measure(repetitions)


if __name__ == "__main__":
    unittest.main()
