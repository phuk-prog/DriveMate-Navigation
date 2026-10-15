"""Find discriminating, map-derived route-preference scenarios on public UK roads.

No personal journeys or GPS input; only a bounded selection of directed
graph-connected public map vertices. Failure to find different routes is
COVERAGE INSUFFICIENT, never evidence that route preferences are equal.
"""
from __future__ import annotations

from collections import deque
from itertools import islice

from engine.routing import RoadGraph, RouteNotFound
from engine.route_alternatives import generate_route_candidates


def _road_pairs(graph: RoadGraph, *, maximum_pairs: int):
    if type(maximum_pairs) is not int or not 1 <= maximum_pairs <= 240:
        raise ValueError("Maximum map-derived scenario count must be 1..240")
    origins = sorted({e.source for e in graph.edges.values() if e.access == "allowed"})
    if not origins:
        return
    stride = max(1, len(origins) // 48)
    sent = set()
    for origin in origins[::stride]:
        frontier = deque([(origin, None, 0)])
        seen_states = {(origin, None)}
        traversed = 0
        while frontier and traversed < 250:
            node, incoming, depth = frontier.popleft()
            traversed += 1
            if 4 <= depth <= 20 and (depth == 4 or depth % 3 == 0):
                item = (origin, node)
                if item not in sent and origin != node:
                    sent.add(item)
                    yield item
                    if len(sent) >= maximum_pairs:
                        return
            if depth >= 20:
                continue
            for edge in graph.adjacency[node]:
                if edge.access != "allowed" or (
                        incoming is not None and
                        (incoming, edge.edge_id) in graph.prohibited_turns):
                    continue
                state = (edge.target, edge.edge_id)
                if state not in seen_states:
                    seen_states.add(state)
                    frontier.append((edge.target, edge.edge_id, depth+1))


def probe_preference_diversity(graph: RoadGraph, *,
                               snapshot_id: str, maximum_pairs: int = 96
                               ) -> dict[str, object]:
    """Only aggregate map-source path diversity, not route legality or quality."""
    considered = 0
    multiple = 0
    different_shortest_fastest = 0
    with_distinct_balanced = 0
    no_route = 0
    for source, dest in _road_pairs(graph, maximum_pairs=maximum_pairs):
        considered += 1
        try:
            routes = generate_route_candidates(graph, source, dest,
                      snapshot_id=snapshot_id, max_candidates=4,
                      max_detour_searches=4)
        except RouteNotFound:
            no_route += 1
            continue
        multiple += int(len(routes) > 1)
        f = next(x for x in routes if "fastest" in x.generated_by)
        s = next(x for x in routes if "shortest" in x.generated_by)
        b = next(x for x in routes if "balanced" in x.generated_by)
        different_shortest_fastest += int(f.route.edge_ids != s.route.edge_ids)
        with_distinct_balanced += int(
            b.route.edge_ids != f.route.edge_ids and
            b.route.edge_ids != s.route.edge_ids)
    return {
        "map_derived_preference_pairs_checked": considered,
        "map_derived_pairs_unroutable": no_route,
        "map_derived_pairs_with_multiple_routes": multiple,
        "fastest_and_shortest_different_path_pairs": different_shortest_fastest,
        "balanced_distinct_from_both_pairs": with_distinct_balanced,
        "route_preference_discriminating_coverage": (
            "MAP_DIVERGENCE_OBSERVED" if different_shortest_fastest > 0
            else "INSUFFICIENT"),
        "independently_verified_traffic_legality_or_lane_truth": False,
        "consumer_navigation_apps_compared": 0,
    }
