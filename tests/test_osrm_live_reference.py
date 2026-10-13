import unittest

from pathlib import Path
from benchmarks.osrm_live_reference import (
    benchmark_osrm_local, local_route_url, local_osrm_request,
)


FIXTURE = Path(__file__).resolve().parents[1] / "benchmarks/fixtures/synthetic-osm-junction.xml"


class LocalOSRMReferenceTests(unittest.TestCase):
    def test_loopback_only_endpoint_and_no_user_data_arguments(self):
        url = local_route_url((0.0, 0.0), (0.001, 0.001))
        self.assertTrue(url.startswith("http://127.0.0.1:5000/route/v1/driving/"))
        self.assertIn("overview=false", url)
        with self.assertRaises(ValueError):
            local_osrm_request("https://router.example.invalid/route/v1/driving/")
        with self.assertRaises(ValueError):
            local_route_url((91., 0.), (0., 1.))

    def test_synthetic_mock_does_not_claim_engine_was_executed(self):
        calls = []
        def fake_osrm(url):
            calls.append(url)
            return {"code": "Ok", "routes": [{"distance": 490.0, "duration": 50.0}]}
        result = benchmark_osrm_local(FIXTURE.read_bytes(), snapshot="fabricated-v1",
                                      samples=1, repeats=5, request=fake_osrm)
        self.assertFalse(result["valid_head_to_head_comparison"])
        self.assertEqual(result["scenarios_osrm_ok"], 1)
        self.assertEqual(len(calls), 5)
        self.assertTrue(result["public_data_only"])
        self.assertFalse(result["personal_journeys_used"])
        self.assertFalse(result["verified_safe_for_driving"])
        self.assertEqual(len(result["reason_not_comparable"]), 4)
        self.assertNotIn("origin", str(result).lower())
        self.assertNotIn("destination", str(result).lower())

    def test_unroutable_mock_fails_instead_of_inventing_benchmark(self):
        with self.assertRaises(AssertionError):
            benchmark_osrm_local(FIXTURE.read_bytes(), snapshot="fabricated-v1",
                                 samples=1, repeats=5,
                                 request=lambda url: {"code":"NoRoute"})

    def test_bad_api_format_fails_explicitly(self):
        with self.assertRaises(ValueError):
            benchmark_osrm_local(FIXTURE.read_bytes(), snapshot="fabricated-v1",
                                 samples=1, repeats=1,
                                 request=lambda url: {"code":"Ok","routes":[{}]})

    def test_bounded_repetition(self):
        with self.assertRaises(ValueError):
            benchmark_osrm_local(FIXTURE.read_bytes(), snapshot="fabricated-v1",
                                 samples=99, repeats=3,
                                 request=lambda url: {"code":"Ok"})


if __name__ == "__main__":
    unittest.main()
