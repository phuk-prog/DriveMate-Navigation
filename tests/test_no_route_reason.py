"""Explaining a missing route (owner-approved, 17 Oct 2026). Synthetic graphs; not run yet."""
import unittest

from engine import RoadEdge, RoadGraph
from engine.no_route_reason import explain_no_route

V = ("a", "b", "c")


class NoRouteReasonTests(unittest.TestCase):
    def test_only_through_a_closed_road(self):
        g = RoadGraph(V, [RoadEdge("ab", "a", "b", 100, 30, "allowed"), RoadEdge("bc", "b", "c", 100, 30, "prohibited")])
        self.assertEqual(explain_no_route(g, "a", "c"), {"reason": "ONLY_VIA_CLOSED_ROAD", "blocking": ["bc"]})

    def test_only_through_an_uncertain_road_in_the_middle(self):
        g = RoadGraph(("a", "b", "c", "d"), [RoadEdge("ab", "a", "b", 100, 30, "allowed"),
                                             RoadEdge("bc", "b", "c", 100, 30, "unknown"),
                                             RoadEdge("cd", "c", "d", 100, 30, "allowed")])
        self.assertEqual(explain_no_route(g, "a", "d")["reason"], "ONLY_VIA_UNCERTAIN_ACCESS")

    def test_only_by_a_banned_turn(self):
        g = RoadGraph(V, [RoadEdge("ab", "a", "b", 100, 30, "allowed"), RoadEdge("bc", "b", "c", 100, 30, "allowed")],
                      [("ab", "bc")])
        r = explain_no_route(g, "a", "c", incoming_edge_id=None, destination_edge_id="bc")
        self.assertEqual(r["reason"], "ONLY_VIA_BANNED_TURN")

    def test_not_connected(self):
        g = RoadGraph(V, [RoadEdge("ab", "a", "b", 100, 30, "allowed")])
        self.assertEqual(explain_no_route(g, "a", "c")["reason"], "NOT_CONNECTED")


if __name__ == "__main__":
    unittest.main()
