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
        self.assertEqual(result["route_edge_ids"], ["approach","unknown-service","shortcut","finish"])

    def test_registry_separates_measured_reference_from_unexecuted_targets(self):
        config = json.loads((Path(__file__).resolve().parents[1] / "benchmarks/reference-engines.json").read_text())
        engines={x['name']:x for x in config['candidate_engines']}
        self.assertEqual(len(engines),10)
        self.assertEqual(engines['GraphHopper']['status'],'actual-isolated-reference-executed')
        self.assertEqual(engines['GraphHopper']['version'],'11.1')
        self.assertTrue(engines['openrouteservice']['provisional_tenth'])
        self.assertTrue(all(x['status']!='verified' for x in engines.values()))

    def test_invalid_benchmark_repetitions_rejected(self):
        for repetitions in (0, -1, 100001):
            with self.assertRaises(ValueError):
                measure(repetitions)


if __name__ == "__main__":
    unittest.main()
