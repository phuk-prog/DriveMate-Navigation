import math
import unittest

from engine import RoadEdge, RoadGraph, RouteNotFound, shortest_route
from engine.astar import astar_route
from benchmarks.fixture import load_fixture
from benchmarks.synthetic_grid import grid
from benchmarks.search_comparison import run


class AStarCorrectnessTests(unittest.TestCase):
    def test_a_star_matches_independent_dijkstra_on_many_synthetic_grids(self):
        for size in range(2, 10):
            graph, points, start, finish = grid(size)
            gold = shortest_route(graph, start, finish)
            candidate = astar_route(graph, start, finish, coordinates=points)
            self.assertTrue(candidate.geographic_heuristic_used)
            self.assertTrue(math.isclose(gold.estimated_seconds, candidate.route.estimated_seconds))
            self.assertEqual(gold.length_m, candidate.route.length_m)
            for edge in candidate.route.edge_ids:
                self.assertEqual(graph.edges[edge].access, "allowed")

    def test_blocked_segments_and_learned_delays_do_not_break_optimality(self):
        graph, points, start, finish = grid(8)
        blocked = {"v-0-0>v-1-0", "v-2-1>v-3-1"}
        penalty = {"v-2-2>v-3-2": 100, "v-4-4>v-5-4": 20}
        baseline = shortest_route(graph, start, finish, blocked_edges=blocked, time_penalties_s=penalty)
        candidate = astar_route(graph, start, finish, coordinates=points,
                                blocked_edges=blocked, time_penalties_s=penalty).route
        self.assertAlmostEqual(candidate.estimated_seconds, baseline.estimated_seconds)
        self.assertFalse(blocked.intersection(candidate.edge_ids))

    def test_explicit_turn_prohibition_and_incoming_edge_still_enforced(self):
        graph, begin, end, expected = load_fixture()
        result = astar_route(graph, begin, end)
        self.assertFalse(result.geographic_heuristic_used)
        self.assertEqual(result.route.edge_ids, expected)
        arrived = astar_route(graph, "B", end, incoming_edge_id="approach")
        self.assertEqual(arrived.route.edge_ids, ("legal", "merge", "finish"))

    def test_bad_geometry_falls_back_to_dijkstra_not_unsafe_heuristic(self):
        graph, points, start, finish = grid(4)
        points = dict(points)
        points[start] = (50, 50)
        alternate = astar_route(graph, start, finish, coordinates=points)
        self.assertFalse(alternate.geographic_heuristic_used)
        self.assertAlmostEqual(alternate.route.estimated_seconds,
                               shortest_route(graph, start, finish).estimated_seconds)

    def test_missing_coordinate_falls_back(self):
        graph, points, start, finish = grid(3)
        points = dict(points)
        points.pop(start)
        self.assertFalse(astar_route(graph, start, finish, coordinates=points).geographic_heuristic_used)

    def test_prohibited_access_and_oneway_still_apply(self):
        vertices = ("A", "B", "C")
        edges = [RoadEdge("ab", "A", "B", 112, 30, "allowed"),
                 RoadEdge("bc", "B", "C", 112, 30, "unknown"),
                 RoadEdge("ac", "A", "C", 500, 30, "allowed")]
        graph = RoadGraph(vertices, edges)
        p = {"A": (0., 0.), "B": (0., .001), "C": (0., .002)}
        self.assertEqual(astar_route(graph, "A", "C", coordinates=p).route.edge_ids, ("ac",))
        with self.assertRaises(RouteNotFound):
            astar_route(graph, "C", "A", coordinates=p)

    def test_stay_put_and_bad_penalty(self):
        graph, points, start, finish = grid(3)
        self.assertEqual(astar_route(graph, start, start, coordinates=points).route.edge_ids, ())
        with self.assertRaises(ValueError):
            astar_route(graph, start, finish, coordinates=points,
                        time_penalties_s={next(iter(graph.edges)): -10})

    def test_synthetic_comparison_labels_are_honest(self):
        summary = run(size=4, repeats=2)
        self.assertFalse(summary["valid_for_road_navigation"])
        self.assertEqual(summary["actual_external_engine_runs"], 0)
        self.assertEqual(summary["classification"], "synthetic")
        self.assertEqual(summary["runs_each"], 2)


if __name__ == "__main__":
    unittest.main()
