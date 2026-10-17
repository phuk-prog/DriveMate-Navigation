"""BARRIER-001 harness: barrier groups, test geometry and verdicts. Invented fixtures."""
import unittest

from benchmarks.barrier001_route import BarrierClip, barrier_class, case_geometry, verdict, without_barrier

#  1 - 2 - 3 - B - 5 - 6 - 7   one residential road, barrier B (node 4) in the middle
#      |___ 8 ___|             detour 2-8-5


def clip(barrier_tags='<tag k="barrier" v="bollard"/>', oneway=""):
    nodes = {1: -2.006, 2: -2.005, 3: -2.004, 4: -2.003, 5: -2.002, 6: -2.001, 7: -2.0}
    parts = ['<osm version="0.6">']
    for n, lon in nodes.items():
        parts.append(f'<node id="{n}" lat="53.0" lon="{lon}">{barrier_tags if n == 4 else ""}</node>')
    parts.append('<node id="8" lat="53.001" lon="-2.0035"/>')
    parts.append('<way id="10">' + "".join(f'<nd ref="{n}"/>' for n in nodes) +
                 f'<tag k="highway" v="residential"/>{oneway}</way>')
    parts.append('<way id="11"><nd ref="2"/><nd ref="8"/><nd ref="5"/><tag k="highway" v="residential"/></way>')
    return BarrierClip(("".join(parts) + "</osm>").encode())


CASE = {"node": 4, "stratum": ["closed", "bollard"], "tags": {"barrier": "bollard"}, "ways": [10]}


class Groups(unittest.TestCase):
    def test_groups(self):
        self.assertEqual(barrier_class({"barrier": "bollard"}), "closed")
        self.assertEqual(barrier_class({"barrier": "bollard", "motor_vehicle": "yes"}), "open")
        self.assertEqual(barrier_class({"barrier": "gate"}), "untagged_gate")
        self.assertEqual(barrier_class({"barrier": "gate", "access": "private"}), "restricted")
        self.assertEqual(barrier_class({"barrier": "gate", "motorcar": "no", "access": "yes"}), "closed")
        self.assertEqual(barrier_class({"barrier": "kerb"}), "passable")
        self.assertEqual(barrier_class({"barrier": "gate", "access:conditional": "no @ (22:00-06:00)"}), "conditional")


class Geometry(unittest.TestCase):
    def test_points_either_side_not_touching_the_barrier(self):
        g = case_geometry(CASE, clip())
        self.assertEqual(g["status"], "TESTABLE")
        self.assertEqual(g["origin_segment"], ["2", "3"])
        self.assertEqual(g["destination_segment"], ["5", "6"])
        self.assertEqual(g["direct_path"], ["2", "3", "4", "5", "6"])

    def test_one_way_line_is_tested_in_its_own_direction(self):
        g = case_geometry(CASE, clip(oneway='<tag k="oneway" v="-1"/>'))
        self.assertEqual(g["origin_segment"], ["6", "5"])

    def test_control_strips_only_the_barrier_tags(self):
        raw = b'<osm version="0.6"><node id="4" lat="53.0" lon="-2.003"><tag k="barrier" v="bollard"/></node></osm>'
        stripped = without_barrier(raw, "4")
        self.assertNotIn(b"barrier", stripped)
        self.assertIn(b'lat="53.0"', stripped)


class Verdicts(unittest.TestCase):
    def setUp(self):
        self.clip = clip()
        self.geom = case_geometry(CASE, self.clip)

    def test_through_closed_is_fail_and_detour_is_pass(self):
        self.assertEqual(verdict(self.clip, self.geom, ["2", "3", "4", "5", "6"])["verdict"], "FAIL_THROUGH_BARRIER")
        detour = verdict(self.clip, self.geom, ["2", "3", "2", "8", "5", "6"])
        self.assertEqual(detour["verdict"], "PASS")
        self.assertFalse(detour["through_barrier"])

    def test_open_barrier_avoided_is_reported(self):
        geom = {**self.geom, "group": "open"}
        self.assertEqual(verdict(self.clip, geom, ["2", "3", "4", "5", "6"])["verdict"], "PASS")
        self.assertEqual(verdict(self.clip, geom, ["2", "3", "2", "8", "5", "6"])["verdict"], "AVOIDED_OPEN_BARRIER")

    def test_other_closed_barrier_on_route_makes_it_illegal(self):
        c = clip()
        c.barriers["8"] = {"barrier": "block"}
        result = verdict(c, self.geom, ["2", "3", "2", "8", "5", "6"])
        self.assertEqual(result["route_legal"], "ILLEGAL")
        self.assertIn("barrier:8:block", result["violations"])

    def test_off_target_route_is_unresolved(self):
        self.assertEqual(verdict(self.clip, self.geom, ["3", "2", "8", "5", "6"])["verdict"], "UNRESOLVED_SNAP")


if __name__ == "__main__":
    unittest.main()
