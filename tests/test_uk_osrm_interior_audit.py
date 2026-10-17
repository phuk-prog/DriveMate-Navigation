"""OSRM node annotations: mapped interior facts, never certified UK law."""
from __future__ import annotations

import unittest

from engine import RoadEdge, RoadGraph
from benchmarks.uk_osrm_interior_audit import (
    audit_osrm_interior_nodes, summarized_interior_audits)


def graph(*, turns=(), access="allowed"):
    edges = [
        RoadEdge("ab", "osm:1", "osm:2", 100, 40, "allowed"),
        RoadEdge("bc", "osm:2", "osm:3", 100, 40, access),
        RoadEdge("cd", "osm:3", "osm:4", 100, 40, "allowed"),
    ]
    return RoadGraph(["osm:1", "osm:2", "osm:3", "osm:4"],
                     edges, prohibited_turns=turns)


class OSRMInteriorAuditTests(unittest.TestCase):
    def test_matched_directed_nodes_are_not_road_law_proof(self):
        r = audit_osrm_interior_nodes(graph(), [1, 2, 3, 4])
        self.assertEqual(r["audit_status"], "INTERIOR_MAPPED_COMPATIBLE_UNVERIFIED")
        self.assertEqual(r["interior_node_pairs_checked"], 3)
        self.assertEqual(r["interior_mapped_allowed_pairs"], 3)
        self.assertIs(r["mapped_interior_compatible_with_dmn"], True)
        self.assertFalse(r["independent_uk_legality_verified"])
        self.assertFalse(r["origin_or_destination_approach_verified"])
        self.assertNotIn("node_ids", r)

    def test_real_mapped_turn_conflict_keeps_provisional_status(self):
        r = audit_osrm_interior_nodes(graph(turns=(("ab", "bc"),)), [1, 2, 3])
        self.assertEqual(r["audit_status"], "INTERIOR_MAPPED_TURN_CONFLICT_UNVERIFIED")
        self.assertIs(r["mapped_interior_compatible_with_dmn"], False)

    def test_missing_or_reversed_oneway_direction(self):
        r = audit_osrm_interior_nodes(graph(), [1, 3, 2])
        self.assertEqual(r["interior_unmapped_directional_pairs"], 2)
        self.assertEqual(r["audit_status"], "INTERIOR_ACCESS_OR_COVERAGE_MISMATCH_UNVERIFIED")
        self.assertIsNone(r["mapped_interior_compatible_with_dmn"])

    def test_unknown_road_access_is_never_assumed_allowed(self):
        r = audit_osrm_interior_nodes(graph(access="unknown"), [1, 2, 3, 4])
        self.assertEqual(r["interior_mapped_unknown_access_pairs"], 1)
        self.assertIsNone(r["mapped_interior_compatible_with_dmn"])

    def test_prohibited_access_is_not_allowed(self):
        r = audit_osrm_interior_nodes(graph(access="prohibited"), [1, 2, 3])
        self.assertEqual(r["interior_mapped_prohibited_access_pairs"], 1)
        self.assertIsNone(r["mapped_interior_compatible_with_dmn"])

    def test_unavailable_or_untrusted_annotations_do_not_fabricate_match(self):
        for value in ([], None, ["1", 2], [True, 2], [0, 2], [-1, 2]):
            with self.subTest(value=value):
                r = audit_osrm_interior_nodes(graph(), value)
                self.assertEqual(r["audit_status"], "ANNOTATIONS_UNAVAILABLE")
                self.assertFalse(r["independent_uk_legality_verified"])

    def test_parallel_edges_keep_compatible_turn_path(self):
        g = RoadGraph(["osm:1", "osm:2", "osm:3"], [
            RoadEdge("ab", "osm:1", "osm:2", 30, 20, "allowed"),
            RoadEdge("bc_banned", "osm:2", "osm:3", 30, 20, "allowed"),
            RoadEdge("bc_ok", "osm:2", "osm:3", 30, 20, "allowed"),
        ], prohibited_turns={("ab", "bc_banned")})
        r = audit_osrm_interior_nodes(g, [1, 2, 3])
        self.assertEqual(r["audit_status"], "INTERIOR_MAPPED_COMPATIBLE_UNVERIFIED")

    def test_forged_proof_and_bad_counters_are_refused(self):
        r = audit_osrm_interior_nodes(graph(), [1, 2, 3])
        r["independent_uk_legality_verified"] = True
        with self.assertRaises(AssertionError):
            summarized_interior_audits([{"route_node_audit": r}])
        r["independent_uk_legality_verified"] = False
        r["interior_mapped_allowed_pairs"] = 100
        with self.assertRaises(AssertionError):
            summarized_interior_audits([{"route_node_audit": r}])


if __name__ == "__main__":
    unittest.main()
