"""Ephemeral public-road routing experiment, strictly NOT driving guidance.

Loads only the ignored OSM XML subset made from an independently chosen public
UK map bbox. Generates deterministic non-personal test paths *from the graph*;
never reads trip logs, origin/destination input, GPS traces or device IDs.
Displays aggregate correctness/performance results with honest limitations.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections import Counter
from statistics import median
import xml.etree.ElementTree as ET
from time import perf_counter_ns

from engine import RouteNotFound, shortest_route
from engine.route_alternatives import generate_route_candidates
from benchmarks.public_route_preferences import probe_preference_diversity
from engine.astar import astar_route, prepare_astar
from map_data import Provenance, import_osm_xml
from map_data.osm_xml import MAX_INPUT_BYTES

ROOT = Path(__file__).resolve().parents[1]
IGNORED = ROOT / "results"


def _public_file(path: Path) -> Path:
    target = path.resolve()
    if not target.is_relative_to(IGNORED.resolve()) or target.suffix != ".osm":
        raise ValueError("Public experiment accepts XML only inside ignored results/")
    if not target.is_file() or (MAX_INPUT_BYTES is not None and target.stat().st_size > MAX_INPUT_BYTES):
        raise ValueError("Missing, empty or oversized extracted public-road XML")
    return target


def _scenarios(graph, *, limit: int) -> list[tuple[str, str]]:
    """Walk only fixed public-road topology, never user-specified coordinates."""
    scenarios = []
    selected = set()
    for origin in sorted(graph.vertices):
        # Spread experiments through the network, but avoid inferring user routes.
        walk = origin
        entering = None
        visited = {walk}
        for _ in range(9):
            choices = [e for e in graph.adjacency[walk]
                       if e.access == "allowed"
                       and (entering is None or (entering, e.edge_id) not in graph.prohibited_turns)
                       and e.target not in visited]
            if not choices:
                break
            next_edge = choices[0]
            walk, entering = next_edge.target, next_edge.edge_id
            visited.add(walk)
            if len(visited) >= 5 and (origin, walk) not in selected:
                selected.add((origin, walk))
                scenarios.append((origin, walk))
                break
        if len(scenarios) >= limit * 3:
            break
    return scenarios


def _source_access_breakdown(raw: bytes, graph) -> dict[str, dict[str, int]]:
    """Explain routed vs unknown/prohibited edges by actual OSM road class.

    Graph access tags are map-source semantics; no classes certify legal truth.
    """
    root = ET.fromstring(raw)
    roads = {}
    for way in root.findall("way"):
        tags = {tag.get("k"): tag.get("v") for tag in way.findall("tag")}
        if "highway" in tags:
            roads[way.get("id")] = tags["highway"]
    counts = {"allowed": Counter(), "unknown": Counter(), "prohibited": Counter()}
    for edge in graph.edges.values():
        way_id = edge.edge_id.split(":")[1]
        counts[edge.access][roads.get(way_id, "unknown_road_class")] += 1
    return {status: dict(sorted(group.items(), key=lambda pair: (-pair[1], pair[0])))
            for status, group in counts.items()}


def check_public_graph(raw: bytes, *, snapshot: str, region: str, samples: int = 8) -> dict[str, object]:
    if not 1 <= samples <= 100:
        raise ValueError("Sample count must be 1..100")
    imported = import_osm_xml(
        raw,
        provenance=Provenance(region=region, snapshot=snapshot, source="Geofabrik-current-or-pinned",
                              attribution="© OpenStreetMap contributors"),
    )
    graph = imported.graph
    setup_start = perf_counter_ns()
    prepared = prepare_astar(graph, imported.coordinates)
    prepare_ms = (perf_counter_ns() - setup_start) / 1e6
    tested = 0
    d_ms, a_ms, cold_ms = [], [], []
    heuristic_count = 0
    route_profiles_checked = 0
    distinct_candidate_cases = 0
    for source, target in _scenarios(graph, limit=samples):
        if tested >= samples:
            break
        try:
            start = perf_counter_ns()
            baseline = shortest_route(graph, source, target)
            d_ms.append((perf_counter_ns() - start)/1e6)
            start = perf_counter_ns()
            candidate = astar_route(graph, source, target, prepared=prepared)
            a_ms.append((perf_counter_ns() - start)/1e6)
            start = perf_counter_ns()
            cold = astar_route(graph, source, target, coordinates=imported.coordinates)
            cold_ms.append((perf_counter_ns() - start)/1e6)
        except RouteNotFound:
            continue
        if abs(cold.route.estimated_seconds - candidate.route.estimated_seconds) > 1e-7:
            raise AssertionError("Prepared and unprepared A* disagree")
        if abs(baseline.estimated_seconds - candidate.route.estimated_seconds) > 1e-7:
            raise AssertionError("A* and Dijkstra disagreed on shortest-time cost")
        if not candidate.route.edge_ids:
            raise AssertionError("A nontrivial scenario has an empty path")
        previous = None
        for eid in candidate.route.edge_ids:
            edge = graph.edges[eid]
            if edge.access != "allowed" or (previous, eid) in graph.prohibited_turns:
                raise AssertionError("Candidate used a prohibited movement")
            previous = eid
        new_routes = generate_route_candidates(
            graph, source, target, snapshot_id=imported.metadata["source_sha256"],
            max_candidates=4, max_detour_searches=4)
        if not new_routes:
            raise AssertionError("Routable public graph produced no profile candidates")
        expected_seconds = min(r.route.estimated_seconds for r in new_routes)
        if abs(expected_seconds - baseline.estimated_seconds) > 1e-7:
            raise AssertionError("Fastest route generator disagreed with Dijkstra")
        for proposal in new_routes:
            if proposal.as_unverified_option().independently_verified_legal:
                raise AssertionError("Map-only route cannot self-certify legality")
            entering = None
            for edge_id in proposal.route.edge_ids:
                edge = graph.edges[edge_id]
                if edge.access != "allowed" or (entering, edge_id) in graph.prohibited_turns:
                    raise AssertionError("Route preference bypassed mapped access/turn rule")
                entering = edge_id
        route_profiles_checked += 1
        distinct_candidate_cases += int(len(new_routes) > 1)
        tested += 1
        heuristic_count += int(candidate.geographic_heuristic_used)
    if tested < min(3, samples):
        raise AssertionError("Not enough independently generated routable public-road scenarios")
    discovery = probe_preference_diversity(
        graph, snapshot_id=imported.metadata["source_sha256"], maximum_pairs=96)
    return {
        **discovery,
        "source_road_access_by_class": _source_access_breakdown(raw, graph),
        "classification": "public-road-experimental-not-legality-verified",
        "source_sha256": imported.metadata["source_sha256"],
        "source_snapshot": snapshot,
        "road_graph_vertices": len(graph.vertices),
        "road_graph_directed_edges": len(graph.edges),
        "node_via_forbidden_turn_pairs": len(graph.prohibited_turns),
        "scenario_count": tested,
        "astar_matches_dijkstra_estimated_cost": True,
        "astar_geographic_heuristic_used_count": heuristic_count,
        "median_ms_dijkstra": round(median(d_ms), 5),
        "median_ms_astar_prepared": round(median(a_ms), 5),
        "median_ms_astar_unprepared": round(median(cold_ms), 5),
        "one_time_astar_prepare_ms": round(prepare_ms, 5),
        "external_engines_executed": 0,
        "route_preference_profiles_checked": route_profiles_checked,
        "route_preference_distinct_path_scenarios": distinct_candidate_cases,
        "route_preference_graph_rules_consistent": True,
        "driver_route_legality_independently_verified": False,
        "source_road_data_public": True,
        "user_location_information_used": False,
        "verified_safe_for_live_navigation": False,
        "warning": "Partial public map extract; no proof of legal road access, route quality, or Android performance.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--region", default="independently chosen public UK road area")
    parser.add_argument("--samples", type=int, default=8)
    args = parser.parse_args()
    raw = _public_file(args.input).read_bytes()
    if not raw:
        raise ValueError("Input is empty")
    print(json.dumps(check_public_graph(raw, snapshot=args.snapshot,
                                        region=args.region, samples=args.samples), indent=2))


if __name__ == "__main__":
    main()
