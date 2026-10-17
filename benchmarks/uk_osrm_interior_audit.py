"""Check OSRM's ephemeral annotated OSM-node path against DMN's mapped rules.

OSRM /route annotations=nodes reports source OSM vertices along a computed
path, not full lane/turn/vehicle-arrival truth. This module never returns raw
node IDs or coordinates; any mismatch is evidence for further map-rule
investigation, NOT authoritative UK legal truth.
"""
from __future__ import annotations

from collections import Counter

from engine.routing import RoadGraph

MAX_NODES = 4000
STATUSES = frozenset((
    "INTERIOR_MAPPED_COMPATIBLE_UNVERIFIED",
    "INTERIOR_MAPPED_TURN_CONFLICT_UNVERIFIED",
    "INTERIOR_ACCESS_OR_COVERAGE_MISMATCH_UNVERIFIED",
    "ANNOTATIONS_UNAVAILABLE",
))


def audit_osrm_interior_nodes(graph: RoadGraph, nodes: object) -> dict:
    """Analyze interior directed node-to-node movements and mapped turn bans.

    Multiple parallel DMN edges are kept as possible states. Do not count
    shared OSM node IDs as matching road direction, source/arrival approach,
    independent signage or roundabout lanes.
    """
    if not isinstance(graph, RoadGraph):
        raise TypeError("Strictly imported DMN RoadGraph required")
    if (not isinstance(nodes, list) or not 2 <= len(nodes) <= MAX_NODES or
            any(type(x) is not int or x <= 0 or x >= 2**64 for x in nodes)):
        return {
            "audit_status": "ANNOTATIONS_UNAVAILABLE",
            "annotated_nodes_count": 0,
            "independent_uk_legality_verified": False,
        }

    by_pair: dict[tuple[str, str], list] = {}
    for edge in graph.edges.values():
        by_pair.setdefault((edge.source, edge.target), []).append(edge)
    allowed = unknown = prohibited = absent = 0
    candidates: list[tuple[str, ...]] = []
    for first, second in zip(nodes, nodes[1:]):
        edges = by_pair.get((f"osm:{first}", f"osm:{second}"), ())
        usable = tuple(edge.edge_id for edge in edges if edge.access == "allowed")
        candidates.append(usable)
        if usable:
            allowed += 1
        elif any(edge.access == "unknown" for edge in edges):
            unknown += 1
        elif edges:
            prohibited += 1
        else:
            absent += 1

    segments = len(nodes) - 1
    compatible = None
    turn_conflict = False
    if allowed == segments:
        reachable = set(candidates[0])
        for successors in candidates[1:]:
            reachable = {
                departing for departing in successors
                if any((arriving, departing) not in graph.prohibited_turns
                       for arriving in reachable)
            }
            if not reachable:
                turn_conflict = True
                break
        compatible = bool(reachable)
    if compatible is True:
        status = "INTERIOR_MAPPED_COMPATIBLE_UNVERIFIED"
    elif turn_conflict:
        status = "INTERIOR_MAPPED_TURN_CONFLICT_UNVERIFIED"
    else:
        status = "INTERIOR_ACCESS_OR_COVERAGE_MISMATCH_UNVERIFIED"
    return {
        "audit_status": status,
        "annotated_nodes_count": len(nodes),
        "interior_node_pairs_checked": segments,
        "interior_mapped_allowed_pairs": allowed,
        "interior_mapped_unknown_access_pairs": unknown,
        "interior_mapped_prohibited_access_pairs": prohibited,
        "interior_unmapped_directional_pairs": absent,
        "mapped_interior_compatible_with_dmn": compatible,
        "origin_or_destination_approach_verified": False,
        "independent_uk_legality_verified": False,
    }


def summarized_interior_audits(rows: list[dict]) -> dict:
    audited = [row["route_node_audit"] for row in rows
               if isinstance(row.get("route_node_audit"), dict)]
    for audit in audited:
        if (audit.get("audit_status") not in STATUSES or
                audit.get("independent_uk_legality_verified") is not False):
            raise AssertionError("Invalid interior route audit or false UK legality")
        if audit["audit_status"] != "ANNOTATIONS_UNAVAILABLE":
            pairs = audit.get("interior_node_pairs_checked")
            counters = (
                audit.get("interior_mapped_allowed_pairs"),
                audit.get("interior_mapped_unknown_access_pairs"),
                audit.get("interior_mapped_prohibited_access_pairs"),
                audit.get("interior_unmapped_directional_pairs"),
            )
            if (type(pairs) is not int or pairs < 1 or
                    any(type(n) is not int or n < 0 for n in counters) or
                    sum(counters) != pairs or
                    audit.get("annotated_nodes_count") != pairs + 1 or
                    audit.get("origin_or_destination_approach_verified") is not False):
                raise AssertionError("Invalid anonymized OSRM node-pair counters")
    counts = Counter(x["audit_status"] for x in audited)
    return {
        "annotated_comparison_cases": len(audited),
        "interior_audit_status_counts": dict(sorted(counts.items())),
        "independent_uk_legality_verified": False,
        "full_dmn_osrm_route_equivalence_verified": False,
    }
