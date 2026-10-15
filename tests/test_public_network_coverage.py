"""Topology diagnostics and route-pair selection regression tests.

These are invented tiny graphs for algorithm validation, NOT UK road truth.
"""
import unittest

from benchmarks.public_route_preferences import (
    _join_destinations, _road_pairs, inspect_network, probe_preference_diversity)
from engine import RoadEdge, RoadGraph


class PublicNetworkCoverageTests(unittest.TestCase):
    def test_independent_two_corridors_are_selected_before_control_walks(self):
        graph = RoadGraph(["A", "B", "C", "D", "E"], [
            RoadEdge("ab", "A", "B", 40, 10, "allowed"),
            RoadEdge("bd", "B", "D", 40, 10, "allowed"),
            RoadEdge("ac", "A", "C", 110, 80, "allowed"),
            RoadEdge("ce", "C", "E", 80, 80, "allowed"),
            RoadEdge("ed", "E", "D", 80, 80, "allowed"),
        ])
        self.assertEqual(list(_road_pairs(graph, maximum_pairs=1)), [("A", "D")])
        report = probe_preference_diversity(
            graph, snapshot_id="synthetic", maximum_pairs=1)
        self.assertEqual(report["map_derived_pairs_with_multiple_routes"], 1)
        self.assertEqual(report["fastest_and_shortest_different_path_pairs"], 1)
        self.assertEqual(report["network_drivable_branch_vertices"], 1)
        self.assertEqual(report["network_undirected_cycle_rank_upper_bound"], 1)
        self.assertEqual(report["network_largest_weak_component_vertices"], 5)

    def test_turn_restriction_prevents_false_join(self):
        graph = RoadGraph(["A", "B", "C", "D", "E"], [
            RoadEdge("ab", "A", "B", 40, 10, "allowed"),
            RoadEdge("bd", "B", "D", 40, 10, "allowed"),
            RoadEdge("ac", "A", "C", 110, 80, "allowed"),
            RoadEdge("ce", "C", "E", 80, 80, "allowed"),
            RoadEdge("ed", "E", "D", 80, 80, "allowed"),
        ], prohibited_turns={("ab", "bd")})
        self.assertNotIn("D", _join_destinations(graph, "A"))
        self.assertEqual(inspect_network(graph)["network_undirected_cycle_rank_upper_bound"], 1)
        # A physical cycle does not establish a valid directed alternative.
        self.assertEqual(
            probe_preference_diversity(graph, snapshot_id="synthetic")[
                "fastest_and_shortest_different_path_pairs"], 0)

    def test_unconnected_metadata_nodes_not_counted_as_drivable(self):
        graph = RoadGraph(["A", "B", "C", "D", "metadata"], [
            RoadEdge("ab", "A", "B", 40, 10, "allowed"),
            RoadEdge("cd", "C", "D", 40, 10, "allowed"),
        ])
        report = inspect_network(graph)
        self.assertEqual(report["network_declared_vertices"], 5)
        self.assertEqual(report["network_active_drivable_vertices"], 4)
        self.assertEqual(report["network_weak_components_with_roads"], 2)
        self.assertEqual(report["network_largest_weak_component_vertices"], 2)
        self.assertEqual(report["network_edges_by_access"],
                         {"allowed": 2, "unknown": 0, "prohibited": 0})
        self.assertEqual(report["network_undirected_cycle_rank_upper_bound"], 0)

    def test_no_usable_edges_is_coverage_not_a_pass(self):
        graph = RoadGraph(["A", "B"], [
            RoadEdge("ab", "A", "B", 40, 10, "unknown")])
        report = probe_preference_diversity(graph, snapshot_id="synthetic")
        self.assertEqual(report["network_active_drivable_vertices"], 0)
        self.assertEqual(report["network_weak_components_with_roads"], 0)
        self.assertEqual(report["route_preference_discriminating_coverage"],
                         "INSUFFICIENT")


if __name__ == "__main__":
    unittest.main()
