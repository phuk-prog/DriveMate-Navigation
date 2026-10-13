import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from benchmarks.graphhopper_live_reference import (
    INFO_URL, ROUTE_ENDPOINT, benchmark_graphhopper_local,
    local_graphhopper_request, route_url,
)
from benchmarks.public_uk_probe import _public_file


FIXTURE = (Path(__file__).resolve().parents[1] /
           "benchmarks/fixtures/synthetic-osm-junction.xml")


class GraphHopperReferenceTests(unittest.TestCase):
    def test_loopback_only_public_point_query(self):
        self.assertEqual(INFO_URL, "http://127.0.0.1:8989/info")
        u = route_url((0.01, 0.02), (0.03, 0.04))
        self.assertTrue(u.startswith(ROUTE_ENDPOINT + "?"))
        p = parse_qs(urlparse(u).query)
        self.assertEqual(p["point"], ["0.0100000,0.0200000", "0.0300000,0.0400000"])
        self.assertEqual(p["profile"], ["car"])
        self.assertEqual(p["calc_points"], ["false"])
        with self.assertRaises(ValueError):
            local_graphhopper_request("https://routing.example.invalid/route")
        with self.assertRaises(ValueError):
            route_url((float("nan"), 0), (0, 0))

    def test_fabricated_response_not_reported_as_a_real_gh_run(self):
        requested = []
        def fake(url):
            requested.append(True)
            return {"paths": [{"distance": 470.0, "time": 50000.0}]}
        result = benchmark_graphhopper_local(
            FIXTURE.read_bytes(), snapshot="synthetic-v1", samples=1, repeats=5,
            request=fake)
        self.assertEqual(len(requested), 5)
        self.assertFalse(result["graphhopper_executed"])
        self.assertFalse(result["fair_engine_speed_ranking"])
        self.assertEqual(result["graphhopper_scenarios_ok"], 1)
        self.assertFalse(result["personal_journeys_used"])
        self.assertFalse(result["verified_safe_for_driving"])
        self.assertEqual(len(result["comparison_limitations"]), 4)
        self.assertNotIn("coordinates", str(result))

    def test_no_route_never_invented_as_success(self):
        with self.assertRaises(AssertionError):
            benchmark_graphhopper_local(FIXTURE.read_bytes(), snapshot="synthetic",
                                        samples=1, repeats=2,
                                        request=lambda url: {"route_unavailable": True})

    def test_malformed_summary_rejected(self):
        with self.assertRaises(ValueError):
            benchmark_graphhopper_local(FIXTURE.read_bytes(), snapshot="synthetic",
                                        samples=1, repeats=1,
                                        request=lambda url: {"paths":[{}]})

    def test_local_input_is_restricted_to_untracked_results(self):
        with self.assertRaises(ValueError):
            _public_file(FIXTURE)

    def test_bounded_samples_and_repeats(self):
        with self.assertRaises(ValueError):
            benchmark_graphhopper_local(FIXTURE.read_bytes(), snapshot="synthetic",
                                        samples=25, repeats=1,
                                        request=lambda url: {})


if __name__ == "__main__":
    unittest.main()
