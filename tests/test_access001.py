"""ACCESS-001 harness: road groups, test geometry and verdicts. Invented fixtures."""
import unittest

import benchmarks.access001_route as harness
from benchmarks.access001_route import (AccessClip, case_geometry, oneway_class, opened, road_class, uses_way,
                                        verdict)

#  1 - 2 = 3 = 4 = 5 - 6     roads 1-2 and 5-6 open to cars; way 20 (2-3-4-5) is the tested road
#      |____ 8 ____|         detour 2-8-5 open to cars


def clip(test_tags='<tag k="highway" v="unclassified"/><tag k="motor_vehicle" v="no"/><tag k="bus" v="yes"/>'):
    lons = {1: -2.008, 2: -2.005, 3: -2.004, 4: -2.003, 5: -2.002, 6: -1.999}
    parts = ['<osm version="0.6">']
    parts += [f'<node id="{n}" lat="53.0" lon="{lon}"/>' for n, lon in lons.items()]
    parts.append('<node id="8" lat="53.004" lon="-2.0035"/>')
    parts.append('<way id="10"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/></way>')
    parts.append(f'<way id="20"><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="5"/>{test_tags}</way>')
    parts.append('<way id="30"><nd ref="5"/><nd ref="6"/><tag k="highway" v="residential"/></way>')
    parts.append('<way id="40"><nd ref="2"/><nd ref="8"/><nd ref="5"/><tag k="highway" v="residential"/></way>')
    return AccessClip(("".join(parts) + "</osm>").encode())


CASE = {"way": 20, "stratum": ["closed", "bus_gate"], "refs": [2, 3, 4, 5]}


class Groups(unittest.TestCase):
    def test_groups(self):
        self.assertEqual(road_class({"highway": "service", "motor_vehicle": "no", "psv": "yes"}),
                         ("closed", "bus_gate"))
        self.assertEqual(road_class({"highway": "residential", "access": "no"}), ("closed", "no_cars"))
        self.assertEqual(road_class({"highway": "busway"}), ("closed", "busway"))
        self.assertEqual(road_class({"highway": "pedestrian"}), ("closed", "pedestrian"))
        self.assertIsNone(road_class({"highway": "pedestrian", "motor_vehicle": "destination"}))
        self.assertEqual(road_class({"highway": "service", "access": "private"}), ("restricted", "private"))
        self.assertEqual(road_class({"highway": "service", "vehicle": "private", "bus": "yes"}),
                         ("restricted", "bus_private"))
        self.assertIsNone(road_class({"highway": "residential"}))
        self.assertIsNone(road_class({"highway": "residential", "motorcar": "yes", "access": "no"}))
        self.assertIsNone(road_class({"highway": "residential", "motor_vehicle:conditional": "no @ (07:00-10:00)",
                                      "motor_vehicle": "no"}))
        self.assertIsNone(road_class({"highway": "pedestrian", "area": "yes"}))


class Geometry(unittest.TestCase):
    def test_points_on_the_car_roads_either_side(self):
        g = case_geometry(CASE, clip())
        self.assertEqual(g["status"], "TESTABLE")
        self.assertEqual(g["origin_segment"], ["1", "2"])
        self.assertEqual(g["destination_segment"], ["5", "6"])
        self.assertEqual(g["direct_path"], ["1", "2", "3", "4", "5", "6"])

    def test_one_way_road_is_tested_in_its_own_direction(self):
        g = case_geometry(CASE, clip('<tag k="highway" v="busway"/><tag k="oneway" v="-1"/>'))
        self.assertEqual(g["origin_segment"], ["6", "5"])
        self.assertEqual(g["way_nodes"], ["5", "4", "3", "2"])

    def test_changed_way_is_not_testable(self):
        self.assertEqual(case_geometry({**CASE, "refs": [2, 3, 5]}, clip())["status"], "WAY_CHANGED_IN_CLIP")

    def test_control_opens_the_road_to_cars(self):
        raw = (b'<osm version="0.6"><way id="20"><nd ref="2"/><tag k="highway" v="busway"/>'
               b'<tag k="access" v="no"/><tag k="bus" v="yes"/></way></osm>')
        out = opened(raw, "20")
        self.assertNotIn(b"busway", out)
        self.assertNotIn(b'k="access"', out)
        self.assertIn(b'v="unclassified"', out)
        self.assertIn(b'k="bus"', out)


class Verdicts(unittest.TestCase):
    def setUp(self):
        self.clip = clip()
        self.geom = case_geometry(CASE, self.clip)

    def test_route_matching_sees_the_closed_road(self):
        self.assertIn("20", self.clip.node_ways["3"])
        self.assertEqual(self.clip.drivable_ways("2"), ["10", "40"])

    def test_through_closed_is_fail_and_detour_is_pass(self):
        self.assertEqual(verdict(self.clip, self.geom, ["1", "2", "3", "4", "5", "6"])["verdict"],
                         "FAIL_THROUGH_NO_CAR_ROAD")
        detour = verdict(self.clip, self.geom, ["1", "2", "8", "5", "6"])
        self.assertEqual(detour["verdict"], "PASS")
        self.assertEqual(detour["route_legal"], "LEGAL")

    def test_using_part_of_the_closed_road_is_a_fail(self):
        self.assertTrue(uses_way(["1", "2", "3", "2", "8"], ["2", "3", "4", "5"]))
        self.assertFalse(uses_way(["1", "2", "8", "5"], ["2", "3", "4", "5"]))

    def test_restricted_road_is_reported_not_judged(self):
        geom = {**self.geom, "group": "restricted"}
        self.assertEqual(verdict(self.clip, geom, ["1", "2", "3", "4", "5", "6"])["verdict"], "USED_RESTRICTED")
        self.assertEqual(verdict(self.clip, geom, ["1", "2", "8", "5", "6"])["verdict"], "AVOIDED_RESTRICTED")

    def test_no_route_and_off_target(self):
        self.assertEqual(verdict(self.clip, self.geom, None)["verdict"], "SAFE_NO_ROUTE")
        self.assertEqual(verdict(self.clip, self.geom, ["2", "8", "5", "6"])["verdict"], "UNRESOLVED_SNAP")

    def test_other_closed_road_on_route_makes_it_illegal(self):
        c = clip()
        c.ways["40"][1]["access"] = "no"
        c.no_car["40"] = ("closed", "no_cars")
        result = verdict(c, self.geom, ["1", "2", "8", "5", "6"])
        self.assertEqual(result["route_legal"], "ILLEGAL")
        self.assertIn("road:40:no_cars", result["violations"])


ONEWAY = {"way": 20, "stratum": ["closed", "oneway_residential"], "refs": [2, 3, 4, 5]}


class OneWay(unittest.TestCase):
    """ONEWAY-002 shares the harness: way 20 made a one-way residential road (2 -> 5)."""

    def setUp(self):
        harness.use("oneway002")
        self.addCleanup(harness.use, "access001")
        self.clip = clip('<tag k="highway" v="residential"/><tag k="oneway" v="yes"/>')
        self.geom = case_geometry(ONEWAY, self.clip)

    def test_groups(self):
        self.assertEqual(oneway_class({"highway": "residential", "oneway": "yes"}), ("closed", "oneway_residential"))
        self.assertEqual(oneway_class({"highway": "primary", "oneway": "-1"}), ("closed", "oneway_major"))
        self.assertEqual(oneway_class({"highway": "secondary", "junction": "roundabout"}),
                         ("closed", "oneway_roundabout"))
        self.assertIsNone(oneway_class({"highway": "residential"}))
        self.assertIsNone(oneway_class({"highway": "residential", "oneway": "no", "junction": "roundabout"}))
        self.assertIsNone(oneway_class({"highway": "motorway", "oneway": "yes"}))
        self.assertIsNone(oneway_class({"highway": "service", "oneway": "yes", "access": "private"}))
        self.assertIsNone(oneway_class({"highway": "residential", "oneway": "yes",
                                        "oneway:conditional": "no @ (19:00-07:00)"}))

    def test_request_runs_against_the_one_way(self):
        self.assertEqual(self.geom["status"], "TESTABLE")
        self.assertTrue(self.geom["against_oneway"])
        self.assertEqual(self.geom["way_nodes"], ["5", "4", "3", "2"])
        self.assertEqual(self.geom["origin_segment"], ["6", "5"])
        self.assertEqual(self.geom["destination_segment"], ["2", "1"])

    def test_wrong_way_is_fail_right_way_or_detour_is_not(self):
        self.assertEqual(verdict(self.clip, self.geom, ["6", "5", "4", "3", "2", "1"])["verdict"],
                         "FAIL_AGAINST_ONEWAY")
        self.assertEqual(verdict(self.clip, self.geom, ["6", "5", "8", "2", "1"])["verdict"], "PASS")
        self.assertFalse(uses_way(["2", "3", "4"], ["5", "4", "3", "2"], directed=True))

    def test_two_way_road_in_clip_is_not_testable(self):
        self.assertEqual(case_geometry(ONEWAY, clip())["status"], "NOT_ONE_WAY_IN_CLIP")

    def test_control_makes_the_road_two_way(self):
        raw = (b'<osm version="0.6"><way id="20"><nd ref="2"/><tag k="highway" v="primary"/>'
               b'<tag k="junction" v="roundabout"/><tag k="oneway" v="yes"/></way></osm>')
        out = opened(raw, "20")
        self.assertIn(b'<tag k="oneway" v="no"', out)
        self.assertNotIn(b'v="roundabout"', out)
        self.assertNotIn(b'v="yes" /><tag k="oneway" v="yes"', out)


if __name__ == "__main__":
    unittest.main()
