"""Synthetic schema controls for local external MAP-001 route adapters."""
import unittest
from benchmarks.map001_additional_profiles import classify, endpoint_ok, VERSIONS


class Category1MoreEngines(unittest.TestCase):
    a = (53.0, -2.0)
    b = (53.001, -2.002)
    geometry = [[-2, 53], [-2.001, 53.0005], [-2.002, 53.001]]

    def test_schemas_route(self):
        osrm = {"code": "Ok", "routes": [{"distance": 100,
                                         "geometry": {"type": "LineString", "coordinates": self.geometry}}]}
        gh = {"paths": [{"distance": 100,
                          "points": {"type": "LineString", "coordinates": self.geometry}}]}
        self.assertEqual(classify("OSRM", 200, osrm, self.a, self.b), "ROUTE")
        self.assertEqual(classify("GraphHopper", 200, gh, self.a, self.b), "ROUTE")

    def test_noroute_vs_snapping(self):
        self.assertEqual(classify("OSRM", 200, {"code": "NoRoute"}, self.a, self.b), "NO_ROUTE")
        self.assertEqual(classify("OSRM", 400, {"code": "NoRoute"}, self.a, self.b), "NO_ROUTE")
        self.assertNotEqual(classify("OSRM", 400, {"code": "InvalidOptions"}, self.a, self.b), "NO_ROUTE")
        self.assertEqual(classify("OSRM", 200, {"code": "NoSegment"}, self.a, self.b),
                         "NOT_JUDGED_SNAPPING")
        self.assertEqual(classify("GraphHopper", 400, {"message": "Connection not found"}, self.a, self.b),
                         "NO_ROUTE")
        self.assertEqual(classify("GraphHopper", 400, {"message": "Connection between locations not found"}, self.a, self.b),
                         "NO_ROUTE")
        self.assertNotEqual(classify("GraphHopper", 400, {"message": "Point not found"}, self.a, self.b),
                            "NO_ROUTE")

    def test_endpoints_and_response_must_be_valid(self):
        self.assertFalse(endpoint_ok([], self.a, self.b))
        self.assertFalse(endpoint_ok(self.geometry[::-1], self.a, self.b))
        self.assertFalse(endpoint_ok([self.geometry[0], self.geometry[0]], self.a, self.b))
        self.assertEqual(classify("OSRM", 200, {"code": "Ok", "routes": []}, self.a, self.b),
                         "NOT_JUDGED_SCHEMA")
        self.assertEqual(classify("GraphHopper", 200, {"paths": [{"distance": 100}]}, self.a, self.b),
                         "NOT_JUDGED_ENDPOINT_CORRELATION")

    def test_scope_registry(self):
        self.assertEqual(set(VERSIONS), {"OSRM", "GraphHopper"})
        with self.assertRaises(ValueError):
            classify("CommercialCloudRouter", 200, {}, self.a, self.b)


if __name__ == "__main__":
    unittest.main()
