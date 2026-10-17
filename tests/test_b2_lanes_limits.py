"""Run B2 harness: lane and speed-limit truth parsers and verdicts. Invented values."""
import unittest

from benchmarks.b2_lanes_limits import (clean_lanes, expected_limit, judge_lanes, judge_limit, lane_key,
                                        limit_kind, mph_kph)


class Truth(unittest.TestCase):
    def test_speed_limits(self):
        self.assertEqual(mph_kph("30 mph"), 48.28)
        self.assertIsNone(mph_kph("30"))  # no unit: not used as truth
        self.assertEqual(limit_kind({"highway": "residential", "maxspeed": "20 mph"}), "mph20")
        self.assertEqual(limit_kind({"highway": "primary", "maxspeed": "40 mph", "maxspeed:type": "sign"}), "mph40")
        self.assertEqual(limit_kind({"highway": "residential"}), "none_mapped")
        self.assertEqual(limit_kind({"highway": "secondary", "maxspeed:forward": "30 mph",
                                     "maxspeed:backward": "40 mph"}), "directional")
        self.assertIsNone(limit_kind({"highway": "motorway", "maxspeed": "70 mph"}))
        self.assertIsNone(limit_kind({"highway": "primary", "maxspeed": "national"}))
        self.assertEqual(expected_limit({"maxspeed:forward": "30 mph", "maxspeed:backward": "40 mph"}, "backward"),
                         64.37)

    def test_lanes(self):
        self.assertEqual(lane_key({"turn:lanes:forward": "left|through"}, forward=True), "turn:lanes:forward")
        self.assertEqual(lane_key({"oneway": "yes", "turn:lanes": "left|through"}, forward=True), "turn:lanes")
        self.assertIsNone(lane_key({"turn:lanes": "left|through"}, forward=True))  # two-way road: ambiguous
        self.assertEqual(clean_lanes("left|through;right"), [{"left"}, {"through", "right"}])
        self.assertIsNone(clean_lanes("left|none"))
        self.assertIsNone(clean_lanes("slight_left|through"))
        self.assertIsNone(clean_lanes("through"))  # one lane: nothing to choose


class Verdicts(unittest.TestCase):
    def test_limit_verdicts(self):
        geom = {"expected_kph": 48.28}
        self.assertEqual(judge_limit(geom, 48.0, True)["verdict"], "CORRECT")
        self.assertEqual(judge_limit(geom, 64.4, True)["verdict"], "WRONG")
        self.assertEqual(judge_limit(geom, None, True)["verdict"], "NOT_GIVEN")
        self.assertEqual(judge_limit(geom, 48.0, False)["verdict"], "NOT_JUDGED_ROUTE_DIFFERS")
        self.assertEqual(judge_limit({"expected_kph": None}, None, True)["verdict"], "CORRECT")
        self.assertEqual(judge_limit({"expected_kph": None}, 48.0, True)["verdict"], "GUESSED")

    def test_lane_verdicts(self):
        geom = {"expected_lanes": [2, 3]}
        self.assertEqual(judge_lanes(geom, [3, 2], True)["verdict"], "CORRECT")
        self.assertEqual(judge_lanes(geom, [2], True)["verdict"], "WRONG")
        self.assertEqual(judge_lanes(geom, [], True)["verdict"], "NOT_GIVEN")
        self.assertEqual(judge_lanes(geom, [2, 3], False)["verdict"], "NOT_JUDGED_ROUTE_DIFFERS")


if __name__ == "__main__":
    unittest.main()
