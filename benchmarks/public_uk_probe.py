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
from statistics import median
from time import perf_counter_ns

from engine import RouteNotFound, shortest_route
from engine.astar import astar_route, prepare_astar
from map_data import Provenance, import_osm_xml
from map_data.osm_xml import MAX_INPUT_BYTES

ROOT = Path(__file__).resolve().parents[1]
IGNORED = ROOT / "results"


def _public_file(path: Path) -> Path:
    target = path.resolve()
    if not target.is_relative_to(IGNORED.resolve()) or target.suffix != ".osm":
        raise ValueError("Public experiment accepts XML only inside ignored results/")
    if not target.is_file() or target.stat().st_size > MAX_INPUT_BYTES:
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
        tested += 1
        heuristic_count += int(candidate.geographic_heuristic_used)
    if tested < min(3, samples):
        raise AssertionError("Not enough independently generated routable public-road scenarios")
    return {
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
