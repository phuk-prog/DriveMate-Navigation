"""JOURNEY-001 harness: turn classes, geometry, exit counting and verdicts. Invented fixtures."""
import unittest

from benchmarks.access001_route import AccessClip
from benchmarks.journey001 import (case_geometry, instruction_at, judge_instruction, line_adherence,
                                   makes_movement, ring_exits, turn_class)

#            4
#            |
#  1 - 2 --- 3 --- 5 - 6      crossroads at 3 (roads 200 m long each side)
#            |
#            7
CROSS = {1: (53.0, -2.006), 2: (53.0, -2.003), 3: (53.0, -2.0), 5: (53.0, -1.997), 6: (53.0, -1.994),
         4: (53.0027, -2.0), 7: (52.9973, -2.0)}


def cross_clip():
    parts = ['<osm version="0.6">'] + [f'<node id="{n}" lat="{a}" lon="{b}"/>' for n, (a, b) in CROSS.items()]
    for w, refs in {10: (1, 2, 3), 11: (3, 5, 6), 12: (3, 4), 13: (3, 7)}.items():
        parts.append(f'<way id="{w}">' + "".join(f'<nd ref="{r}"/>' for r in refs) +
                     '<tag k="highway" v="residential"/></way>')
    return AccessClip(("".join(parts) + "</osm>").encode())


def turn_case(to_way, to_node, cls):
    return {"stratum": ["turn", cls], "node": 3, "from_way": 10, "from_node": 2, "to_way": to_way, "to_node": to_node}


#  ring 100: 20 -> 21 -> 22 -> 23 -> 20 (one-way in way order), spokes at every ring node
RING = {20: (53.0, -2.0005), 21: (52.99965, -2.0), 22: (53.0, -1.9995), 23: (53.00035, -2.0)}
SPOKES = {30: (53.0, -2.004), 31: (52.997, -2.0), 32: (53.0, -1.996), 33: (53.003, -2.0)}


def ring_clip():
    parts = ['<osm version="0.6">'] + [f'<node id="{n}" lat="{a}" lon="{b}"/>'
                                       for n, (a, b) in {**RING, **SPOKES}.items()]
    parts.append('<way id="100"><nd ref="20"/><nd ref="21"/><nd ref="22"/><nd ref="23"/><nd ref="20"/>'
                 '<tag k="highway" v="primary"/><tag k="junction" v="roundabout"/></way>')
    for w, (a, b) in {40: (30, 20), 41: (21, 31), 42: (22, 32), 43: (23, 33)}.items():
        parts.append(f'<way id="{w}"><nd ref="{a}"/><nd ref="{b}"/><tag k="highway" v="primary"/></way>')
    return AccessClip(("".join(parts) + "</osm>").encode())


class TurnClasses(unittest.TestCase):
    def test_classes(self):
        self.assertEqual(turn_class(10), "straight")
        self.assertEqual(turn_class(-90), "left")
        self.assertEqual(turn_class(95), "right")
        self.assertIsNone(turn_class(40))
        self.assertIsNone(turn_class(170))


class Geometry(unittest.TestCase):
    def test_crossroads_movements(self):
        clip = cross_clip()
        left = case_geometry(turn_case(12, 4, "left"), clip)  # heading east, north is a left turn
        self.assertEqual(left["status"], "TESTABLE")
        self.assertEqual(left["direct_path"], ["2", "3", "4"])  # 200 m pieces: one segment covers 20 m
        self.assertEqual(case_geometry(turn_case(13, 7, "right"), clip)["expected"], "right")
        self.assertEqual(case_geometry(turn_case(11, 5, "straight"), clip)["direct_path"], ["2", "3", "5"])
        self.assertEqual(case_geometry(turn_case(13, 7, "left"), clip)["status"], "CLASS_CHANGED_IN_CLIP")

    def test_roundabout_exits_are_counted_in_travel_order(self):
        clip = ring_clip()
        path, exits = ring_exits(clip, "100", "20")
        self.assertEqual(path, ["20", "21", "22", "23", "20"])
        self.assertEqual([e[0] for e in exits if e[0] != "20"], ["21", "22", "23"])
        g = case_geometry({"stratum": ["roundabout", "exit2"], "ring_way": 100, "entry_node": 20, "exit_number": 2},
                          clip)
        self.assertEqual(g["status"], "TESTABLE")
        self.assertEqual(g["exit_node"], "22")
        self.assertEqual(g["direct_path"], ["30", "20", "21", "22", "32"])
        last = {"stratum": ["roundabout", "exit3"], "ring_way": 100, "entry_node": 20, "exit_number": 3}
        self.assertEqual(case_geometry(last, clip)["status"], "TOO_FEW_EXITS")


class Verdicts(unittest.TestCase):
    def setUp(self):
        self.left = {**case_geometry(turn_case(12, 4, "left"), cross_clip()), "junction_at": CROSS[3]}
        self.straight = {**case_geometry(turn_case(11, 5, "straight"), cross_clip()), "junction_at": CROSS[3]}

    def test_turn_instructions(self):
        at = CROSS[3]
        self.assertEqual(instruction_at(self.left, [{"at": at, "kind": "left"}])["verdict"], "CORRECT")
        self.assertEqual(instruction_at(self.left, [{"at": at, "kind": "right"}])["verdict"], "WRONG")
        self.assertEqual(instruction_at(self.left, [{"at": CROSS[1], "kind": "left"}])["verdict"], "MISSING")
        self.assertEqual(instruction_at(self.left, [{"at": at, "kind": "left", "slight": True}])["verdict"], "CORRECT")

    def test_straight_on_may_be_silent_or_slight(self):
        self.assertEqual(instruction_at(self.straight, [])["verdict"], "CORRECT")
        self.assertEqual(instruction_at(self.straight, [{"at": CROSS[3], "kind": "right", "slight": True}])["verdict"],
                         "CORRECT")
        self.assertEqual(instruction_at(self.straight, [{"at": CROSS[3], "kind": "right"}])["verdict"], "WRONG")

    def test_roundabout_exit_number(self):
        g = case_geometry({"stratum": ["roundabout", "exit2"], "ring_way": 100, "entry_node": 20, "exit_number": 2},
                          ring_clip())
        self.assertEqual(judge_instruction(g, {"kind": "roundabout", "exit": 2})["verdict"], "CORRECT")
        self.assertEqual(judge_instruction(g, {"kind": "roundabout", "exit": 3})["verdict"], "WRONG")
        self.assertEqual(judge_instruction(g, {"kind": "right"})["verdict"], "WRONG")
        self.assertEqual(judge_instruction(g, None)["verdict"], "MISSING")

    def test_movement_and_line(self):
        self.assertTrue(makes_movement(self.left, ["1", "2", "3", "4"]))
        self.assertFalse(makes_movement(self.left, ["7", "3", "4"]))
        self.assertFalse(makes_movement(self.left, ["1", "2", "3", "5", "6"]))
        clip = cross_clip()
        on = line_adherence(clip, ["2", "3", "4"], [CROSS[2], CROSS[3], CROSS[4]])
        self.assertEqual(on["max_off_road_m"], 0.0)
        off = line_adherence(clip, ["2", "3", "4"], [CROSS[2], (53.0001, -2.0015), CROSS[4]])
        self.assertGreater(off["max_off_road_m"], 10)


if __name__ == "__main__":
    unittest.main()
