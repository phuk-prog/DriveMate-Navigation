import unittest

from engine import RoadEdge, RoadGraph, RouteNotFound, shortest_route
from benchmarks.fixture import load_fixture


class RoutingSafetyTests(unittest.TestCase):
    def setUp(self):
        self.graph, self.origin, self.end, self.expected = load_fixture()

    def test_deterministic_legal_route_avoids_prohibited_turn(self):
        for _ in range(10):
            route = shortest_route(self.graph, self.origin, self.end)
            self.assertEqual(route.edge_ids, self.expected)
            self.assertAlmostEqual(route.estimated_seconds, 27.0)
            self.assertAlmostEqual(route.length_m, 270.0)
            self.assertNotIn(("approach","direct"),tuple(zip(route.edge_ids,route.edge_ids[1:])))

    def test_unknown_access_service_road_is_routable_and_flagged(self):
        route = shortest_route(self.graph, "B", "E")
        self.assertIn("unknown-service", route.edge_ids)
        self.assertEqual(route.unverified_access_edges,("unknown-service",))

    def test_incoming_turn_is_preserved_when_rerouting(self):
        route = shortest_route(self.graph, "B", "E", incoming_edge_id="approach")
        self.assertEqual(route.edge_ids, ("unknown-service", "shortcut", "finish"))
        without_context = shortest_route(self.graph, "B", "E")
        self.assertEqual(without_context.edge_ids, ("unknown-service", "shortcut", "finish"))

    def test_blockage_causes_legal_alternative(self):
        route = shortest_route(self.graph, "A", "E", blocked_edges=("legal","unknown-service"))
        self.assertEqual(route.edge_ids, ("alternate", "finish"))

    def test_nonnegative_penalty_does_not_override_illegal_turn(self):
        route = shortest_route(self.graph, "A", "E", time_penalties_s={"legal": 500,"unknown-service":500})
        self.assertEqual(route.edge_ids, ("alternate", "finish"))
        self.assertNotEqual(route.edge_ids, ("approach", "direct", "finish"))

    def test_one_way_is_not_assumed_bidirectional(self):
        with self.assertRaises(RouteNotFound):
            shortest_route(self.graph, "E", "A")

    def test_unreachable_has_explicit_failure(self):
        isolated = RoadGraph(["A", "B"], [])
        with self.assertRaises(RouteNotFound):
            shortest_route(isolated, "A", "B")

    def test_stay_put(self):
        self.assertEqual(shortest_route(self.graph, "A", "A").edge_ids, ())

    def test_bad_turn_reference_rejected(self):
        with self.assertRaises(ValueError):
            RoadGraph(["A", "B"], [RoadEdge("AB","A","B",50,30,"allowed")],
                      prohibited_turns=[("AB","absent")])

    def test_bad_speed_and_negative_penalty_rejected(self):
        with self.assertRaises(ValueError):
            RoadEdge("x","A","B",1,0,"allowed")
        with self.assertRaises(ValueError):
            shortest_route(self.graph, "A", "E", time_penalties_s={"direct": -1})

    def test_invalid_incoming_edge_context_rejected(self):
        with self.assertRaises(ValueError):
            shortest_route(self.graph, "A", "E", incoming_edge_id="direct")

    def test_unknown_edge_is_rejected_as_closure(self):
        with self.assertRaises(ValueError):
            shortest_route(self.graph, "A", "E", blocked_edges=("no-such-edge",))


if __name__ == "__main__":
    unittest.main()
