"""Contract checks for additional real-road HTTP benchmark adapters.

These tests use artificial JSON replies to verify adapters. Artificial data
NEVER enters measured real-road scorecards.
"""
import io
import json
from unittest import TestCase
from unittest.mock import patch

from benchmarks.real_english_speed import query, NOT_YET_COMPARABLE


CASE = {"source": "a", "target": "b"}
COORDS = {"a": (53.53, -2.64), "b": (53.531, -2.64)}


class _Reply(io.BytesIO):
    def __init__(self, object_value):
        super().__init__(json.dumps(object_value).encode())


class RealRoadAdditionalEngineTests(TestCase):
    def test_openrouteservice_validated_real_path_response_shape(self):
        route = {"features": [{"geometry": {"coordinates":
                 [[-2.64, 53.53], [-2.64, 53.531]]}}]}
        with patch("benchmarks.real_english_speed.urlopen", return_value=_Reply(route)) as opened:
            self.assertIsNone(query("openrouteservice", CASE, COORDS, 1234, None))
            sent = opened.call_args.args[0]
            self.assertEqual(sent.full_url,
                 "http://127.0.0.1:8080/ors/v2/directions/driving-car/geojson")
            self.assertEqual(sent.get_method(), "POST")
            self.assertEqual(json.loads(sent.data)["coordinates"],
                             [[-2.64, 53.53], [-2.64, 53.531]])

    def test_genuine_shorter_urban_route_is_not_falsely_rejected(self):
        # Constructed adapter contract; not claimed as a new measured road.
        # A legitimate 50m shortest route can be much shorter than the
        # independent 250m graph walk that selected these endpoints.
        coords={"a": (53.53, -2.64), "b": (53.53045, -2.64)}
        route={"features":[{"geometry":{"coordinates":[[-2.64,53.53],[-2.64,53.53045]]}}]}
        with patch("benchmarks.real_english_speed.urlopen",return_value=_Reply(route)):
            self.assertIsNone(query("openrouteservice",CASE,coords,1234,None))

    def test_degenerate_but_endpoint_nearby_polyline_is_rejected(self):
        # Tiny/coincident shapes cannot silently become successful routes.
        coords={"a": (53.53,-2.64), "b":(53.53002,-2.64)}
        route={"features":[{"geometry":{"coordinates":[[-2.64,53.53],[-2.64,53.53]]}}]}
        with patch("benchmarks.real_english_speed.urlopen",return_value=_Reply(route)):
            with self.assertRaisesRegex(ValueError,"too short"):
                query("openrouteservice",CASE,coords,1234,None)

    def test_openrouteservice_wrong_destination_not_timed(self):
        reply = {"features": [{"geometry": {"coordinates":
                 [[-2.64, 53.53], [-2.65, 53.531]]}}]}
        with patch("benchmarks.real_english_speed.urlopen", return_value=_Reply(reply)):
            with self.assertRaisesRegex(ValueError, "Endpoint"):
                query("openrouteservice", CASE, COORDS, 1234, None)

    def test_valhalla_empty_geometry_unresolved(self):
        with patch("benchmarks.real_english_speed.urlopen",
                   return_value=_Reply({"trip": {"legs": []}})) as opened:
            with self.assertRaisesRegex(ValueError, "Missing route geometry"):
                query("valhalla", CASE, COORDS, 1234, None)
            self.assertEqual(opened.call_args.args[0].get_method(), "POST")

    def test_unbuilt_brouter_not_awarded_a_speed_rank(self):
        self.assertIn("brouter", NOT_YET_COMPARABLE)
        self.assertIn(".rd5", NOT_YET_COMPARABLE["brouter"])
