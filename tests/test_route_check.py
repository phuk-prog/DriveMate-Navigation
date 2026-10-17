"""Checking a received route line against DMN's map rules (owner-approved, 17 Oct 2026). Synthetic."""
import unittest

from engine import RoadEdge, RoadGraph
from engine.route_check import RouteChecker, destination_side

P = {"a": (53.0, -2.002), "b": (53.0, -2.0), "c": (53.0, -1.998), "d": (53.0015, -2.0)}
EDGES = [RoadEdge("ab", "a", "b", 134, 30, "allowed"), RoadEdge("ba", "b", "a", 134, 30, "allowed"),
         RoadEdge("bc", "b", "c", 134, 30, "allowed"),  # one-way b -> c
         RoadEdge("bd", "b", "d", 167, 30, "prohibited"), RoadEdge("db", "d", "b", 167, 30, "prohibited")]


class RouteCheckTests(unittest.TestCase):
    def checker(self, turns=()):
        return RouteChecker(RoadGraph(P, EDGES, turns), P)

    def test_legal_route_is_ok(self):
        r = self.checker().check([P["a"], P["b"], P["c"]], destination=P["c"])
        self.assertEqual(r["verdict"], "OK")

    def test_one_way_driven_backwards_fails(self):
        r = self.checker().check([P["c"], P["b"], P["a"]])
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("WRONG_WAY", {i["kind"] for i in r["issues"]})

    def test_closed_road_fails(self):
        r = self.checker().check([P["a"], P["b"], P["d"]])
        self.assertIn("CLOSED_ROAD", {i["kind"] for i in r["issues"]})
        self.assertEqual(r["verdict"], "FAIL")

    def test_banned_turn_fails(self):
        r = self.checker(turns=[("ab", "bc")]).check([P["a"], P["b"], P["c"]])
        self.assertIn("BANNED_TURN", {i["kind"] for i in r["issues"]})

    def test_route_ending_far_from_the_destination_warns(self):
        r = self.checker().check([P["a"], P["b"]], destination=P["c"])
        self.assertEqual(r["verdict"], "WARN")
        self.assertIn("ENDS_FAR_FROM_DESTINATION", {i["kind"] for i in r["issues"]})

    def test_destination_side(self):
        g = RoadGraph(P, EDGES)
        self.assertEqual(destination_side(P, g.edges["ab"], (53.0001, -2.001)), "left")
        self.assertEqual(destination_side(P, g.edges["ab"], (52.9999, -2.001)), "right")


if __name__ == "__main__":
    unittest.main()
