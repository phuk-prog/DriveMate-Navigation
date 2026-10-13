import json
from pathlib import Path
import unittest
from benchmarks.valhalla_live_reference import (
    ROUTE_URL, benchmark_valhalla_local, route_request_body, valhalla_local_request,
)
from benchmarks.public_uk_probe import _public_file


FIXTURE = (Path(__file__).resolve().parents[1] /
           "benchmarks/fixtures/synthetic-osm-junction.xml")


class ValhallaReferenceTests(unittest.TestCase):
    def test_request_is_public_graph_derived_with_fixed_local_server(self):
        self.assertEqual(ROUTE_URL, "http://127.0.0.1:8002/route")
        request = json.loads(route_request_body((0.01, 0.02), (0.03, 0.04)))
        self.assertEqual(request["costing"], "auto")
        self.assertEqual(len(request["locations"]), 2)
        self.assertEqual(request["directions_options"]["units"], "kilometers")
        with self.assertRaises(ValueError):
            route_request_body((float("nan"), 0.0), (0.0, 0.0))
        with self.assertRaises(ValueError):
            valhalla_local_request(b"x" * 1001)

    def test_fabricated_adapter_response_never_claims_actual_execution(self):
        calls = []
        def fake_valhalla(body: bytes) -> dict:
            self.assertIsInstance(body, bytes)
            calls.append(1)
            return {"trip": {"summary": {"length": 0.49, "time": 50.0},
                              "units": "kilometers"}}
        result = benchmark_valhalla_local(
            FIXTURE.read_bytes(), snapshot="fabricated-v1",
            samples=1, repeats=5, request=fake_valhalla,
        )
        self.assertFalse(result["real_valhalla_execution"])
        self.assertFalse(result["head_to_head_valid"])
        self.assertFalse(result["approved_for_driving"])
        self.assertFalse(result["contains_personal_journeys"])
        self.assertEqual(result["scenarios_ok"], 1)
        self.assertEqual(result["scenarios_unroutable"], 0)
        self.assertEqual(len(calls), 5)
        self.assertNotIn("latitude", result)
        self.assertNotIn("longitude", result)

    def test_unroutable_fabricated_response_fails_rather_than_invents_success(self):
        with self.assertRaises(AssertionError):
            benchmark_valhalla_local(
                FIXTURE.read_bytes(), snapshot="fabricated-v1",
                samples=1, repeats=2,
                request=lambda body: {"route_unavailable": True},
            )

    def test_broken_route_summary_fails(self):
        with self.assertRaises(ValueError):
            benchmark_valhalla_local(
                FIXTURE.read_bytes(), snapshot="fabricated-v1",
                samples=1, repeats=1,
                request=lambda body: {"trip": {"summary": {"length": 0, "time": 50}}},
            )

    def test_public_uk_source_must_be_inside_ignored_results(self):
        with self.assertRaises(ValueError):
            _public_file(FIXTURE)

    def test_bounded_workload(self):
        with self.assertRaises(ValueError):
            benchmark_valhalla_local(
                FIXTURE.read_bytes(), snapshot="fabricated",
                samples=300, repeats=1, request=lambda _: {},
            )


if __name__ == "__main__":
    unittest.main()
