"""Map-derived UK route-preference coverage with explicit connectivity diagnostics.

Public road topology only, never personal journeys or independent legal truth.
Prefer genuinely joining road corridors over shallow arbitrary shortest-path
samples. A passing benchmark with no divergent routes remains INSUFFICIENT.
"""
from __future__ import annotations

from collections import deque
from itertools import islice

from engine.routing import RoadGraph, RouteNotFound
from engine.route_alternatives import generate_route_candidates


def inspect_network(graph: RoadGraph) -> dict[str, int]:
    """Measure the usable mapped graph without treating a vertex as a road.

    Physical (undirected) cycles are only a *necessary indication* of route
    choice: one-way directions and turn prohibitions may prevent detours.
    """
    allowed = [edge for edge in graph.edges.values() if edge.access == "allowed"]
    # Distinguish sparse input from fail-closed access treatment. Counts are
    # directed edge instances, never independent legality observations.
    access_counts = {state: sum(e.access == state for e in graph.edges.values())
                     for state in ("allowed", "unknown", "prohibited")}
    active = {node for edge in allowed for node in (edge.source, edge.target)}
    neighbors = {node: set() for node in active}
    undirected = set()
    for edge in allowed:
        neighbors[edge.source].add(edge.target)
        neighbors[edge.target].add(edge.source)
        undirected.add(tuple(sorted((edge.source, edge.target))))
    visited = set()
    components = []
    for start in sorted(active):
        if start in visited:
            continue
        queue = [start]
        visited.add(start)
        count = 0
        while queue:
            current = queue.pop()
            count += 1
            for next_node in neighbors[current]:
                if next_node not in visited:
                    visited.add(next_node)
                    queue.append(next_node)
        components.append(count)
    branching = sum(
        len({edge.target for edge in graph.adjacency[node]
             if edge.access == "allowed"}) >= 2 for node in active)
    return {
        "network_declared_vertices": len(graph.vertices),
        "network_active_drivable_vertices": len(active),
        "network_allowed_directed_edges": len(allowed),
        "network_unknown_directed_edges": access_counts["unknown"],
        "network_prohibited_directed_edges": access_counts["prohibited"],
        "network_weak_components_with_roads": len(components),
        "network_largest_weak_component_vertices": max(components, default=0),
        "network_drivable_branch_vertices": branching,
        "network_undirected_cycle_rank_upper_bound": max(
            0, len(undirected) - len(active) + len(components)),
    }


def _spread(values, limit: int):
    """Deterministic, evenly spaced coverage instead of the first map IDs."""
    items = sorted(values)
    if len(items) <= limit:
        return items
    if limit == 1:
        return [items[len(items) // 2]]
    return [items[(i * (len(items) - 1)) // (limit - 1)]
            for i in range(limit)]


def _join_destinations(graph: RoadGraph, origin: str,
                       *, max_hops: int = 28, max_states: int = 500):
    """Find destinations reached by distinct first outgoing mapped edges.

    This is a topology-only discoverer. Incoming-edge states respect every
    imported turn ban, and returning to the origin cannot fabricate a detour.
    """
    exits = [edge for edge in graph.adjacency[origin]
             if edge.access == "allowed"]
    unique = {}
    for edge in exits:
        unique.setdefault(edge.target, edge)
    if len(unique) < 2:
        return []
    arrivals: dict[str, dict[str, int]] = {}
    for first in list(unique.values())[:6]:
        frontier = deque([(first.target, first.edge_id, 1)])
        visited = {(first.target, first.edge_id)}
        explored = 0
        while frontier and explored < max_states:
            node, entering, depth = frontier.popleft()
            explored += 1
            if node != origin and depth >= 2:
                arrivals.setdefault(node, {}).setdefault(first.edge_id, depth)
            if depth >= max_hops:
                continue
            for edge in graph.adjacency[node]:
                if (edge.access != "allowed" or edge.target == origin or
                        (entering, edge.edge_id) in graph.prohibited_turns):
                    continue
                state = (edge.target, edge.edge_id)
                if state not in visited:
                    visited.add(state)
                    frontier.append((edge.target, edge.edge_id, depth + 1))
    joined = []
    for dest, paths in arrivals.items():
        if len(paths) >= 2:
            depths = sorted(paths.values())
            joined.append((min(depths[:2]), dest))
    # Prefer useful journeys beyond the next intersection; deterministic ties.
    return [dest for _, dest in sorted(joined, key=lambda x: (-x[0], x[1]))]


def _road_pairs(graph: RoadGraph, *, maximum_pairs: int):
    if type(maximum_pairs) is not int or not 1 <= maximum_pairs <= 240:
        raise ValueError("Maximum map-derived scenario count must be 1..240")
    origins = sorted({edge.source for edge in graph.edges.values()
                      if edge.access == "allowed"})
    if not origins:
        return
    branch_origins = [
        origin for origin in origins
        if len({edge.target for edge in graph.adjacency[origin]
                if edge.access == "allowed"}) >= 2]
    sent = set()

    # Hard cases first: route choices that rejoin after different first turns.
    for origin in _spread(branch_origins, min(64, len(branch_origins))):
        for dest in islice(_join_destinations(graph, origin), 2):
            pair = origin, dest
            if pair not in sent:
                sent.add(pair)
                yield pair
                if len(sent) >= maximum_pairs:
                    return

    # Held-out ordinary corridors remain, spread throughout the graph.
    for origin in _spread(origins, min(72, len(origins))):
        frontier = deque([(origin, None, 0)])
        visited = {(origin, None)}
        picked = 0
        while frontier and len(visited) < 750:
            node, incoming, depth = frontier.popleft()
            if depth >= 4 and depth % 4 == 0 and node != origin:
                pair = origin, node
                if pair not in sent:
                    sent.add(pair)
                    yield pair
                    picked += 1
                    if len(sent) >= maximum_pairs:
                        return
                    if picked >= 2:
                        break
            if depth >= 32:
                continue
            for edge in graph.adjacency[node]:
                if (edge.access != "allowed" or
                        (incoming is not None and
                         (incoming, edge.edge_id) in graph.prohibited_turns)):
                    continue
                state = (edge.target, edge.edge_id)
                if state not in visited:
                    visited.add(state)
                    frontier.append((edge.target, edge.edge_id, depth + 1))


def probe_preference_diversity(graph: RoadGraph, *,
                               snapshot_id: str, maximum_pairs: int = 96
                               ) -> dict[str, object]:
    """Only aggregate source-map path diversity, not road legality or quality."""
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
        **inspect_network(graph),
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
