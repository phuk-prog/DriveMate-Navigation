import unittest
from dataclasses import replace
from benchmarks.comparison import Measurement, compare


def sample(engine="prototype"):
    return Measurement(
        engine=engine, engine_version="synthetic-1",
        graph_sha256="a" * 64, profile_sha256="b" * 64,
        scenario="fabricated junction", device="test-runner",
        environment="python311-no-cache", run_kind="warm",
        latency_ms=(1.0, 3.0, 5.0, 7.0, 9.0), classification="synthetic"
    )


class IndependentComparisonTests(unittest.TestCase):
    def test_identical_experimental_setup_allows_timing_only(self):
        result = compare(sample(), sample("benchmark-example"))
        self.assertTrue(result["comparable"])
        self.assertEqual(result["classification"], "synthetic")
        self.assertEqual(result["measurements"]["prototype"]["median_ms"], 5)
        self.assertIn("neither correctness nor legal", result["note"])

    def test_mismatched_graph_cannot_be_ranked(self):
        other = replace(sample("other"), graph_sha256="c" * 64)
        result = compare(sample(), other)
        self.assertFalse(result["comparable"])
        self.assertIn("graph_sha256", result["reasons"])
        self.assertIsNone(result["score"])

    def test_device_profile_and_scenario_differences_refused(self):
        other = replace(sample("other"), device="different-phone", profile_sha256="c" * 64,
                        scenario="different-place")
        result = compare(sample(), other)
        self.assertEqual(result["reasons"], ["device", "profile_sha256", "scenario"])

    def test_cold_and_warm_not_combined(self):
        self.assertFalse(compare(sample(), replace(sample("cold"), run_kind="cold"))["comparable"])

    def test_synthetic_not_misrepresented_as_validated(self):
        result = compare(sample(), replace(sample("other"), classification="independently-validated"))
        self.assertFalse(result["comparable"])
        self.assertIn("classification", result["reasons"])

    def test_invalid_measurement_rejected(self):
        with self.assertRaises(ValueError):
            replace(sample(), latency_ms=(float("nan"),)*5)
        with self.assertRaises(ValueError):
            replace(sample(), graph_sha256="not-a-hash")
        with self.assertRaises(ValueError):
            replace(sample(), latency_ms=(1., 2., 3.))


if __name__ == "__main__":
    unittest.main()
