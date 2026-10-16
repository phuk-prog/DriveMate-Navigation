"""Turn-aware A* candidate; Dijkstra remains the independent correctness oracle.

The geographic heuristic is used ONLY if every node has a finite position and
every directed edge's measured length is at least its great-circle distance.
Otherwise the heuristic is identically zero (turn-aware Dijkstra). The lower
bound uses the maximum graph speed; nonnegative turn/edge penalties cannot
invalidate its admissibility. This is a small Python prototype, not production.
"""
from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from math import asin, cos, isfinite, radians, sin, sqrt
from types import MappingProxyType
from typing import Iterable, Mapping

from .routing import RoadGraph, Route, RouteNotFound

EARTH_DIAMETER_M = 12_742_000.0


def metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(radians, a)
    lat2, lon2 = map(radians, b)
    dx = lat2 - lat1
    dy = lon2 - lon1
    h = sin(dx / 2)**2 + cos(lat1)*cos(lat2)*sin(dy/2)**2
    return EARTH_DIAMETER_M * asin(min(1.0, sqrt(max(0.0, h))))


@dataclass(frozen=True)
class AStarResult:
    route: Route
    expanded_states: int
    geographic_heuristic_used: bool


@dataclass(frozen=True)
class PreparedAStar:
    """One-time geometry and speed validation for repeated route calculations.

    Prepared state is strictly tied to one immutable RoadGraph instance, and
    contains an immutable COPY of coordinates. Never reuse across map updates.
    """
    graph: RoadGraph
    coordinates: Mapping[str, tuple[float, float]]
    geographic_heuristic_valid: bool
    maximum_mps: float


def prepare_astar(graph: RoadGraph, coordinates: Mapping[str, tuple[float, float]]) -> PreparedAStar:
    """Validate a graph snapshot once; thereafter A* can reroute without O(E) scans."""
    positions = MappingProxyType({key: tuple(value) for key, value in coordinates.items()})
    valid = _safe_geometry(graph, positions)
    maximum_mps = max((edge.estimated_kph for edge in graph.edges.values()), default=1.0) / 3.6
    return PreparedAStar(graph, positions, valid, maximum_mps)


def _safe_geometry(graph: RoadGraph, points: Mapping[str, tuple[float, float]]) -> bool:
    if any(v not in points for v in graph.vertices):
        return False
    for p in points.values():
        if len(p) != 2 or any(not isfinite(x) for x in p):
            return False
        if not (-90 <= p[0] <= 90 and -180 <= p[1] <= 180):
            return False
    # Prevent a geometry/weight mismatch creating an inadmissible heuristic.
    return all(
        edge.length_m + 0.01 >= metres(points[edge.source], points[edge.target])
        for edge in graph.edges.values()
    )


def astar_route(
    graph: RoadGraph,
    source: str,
    destination: str,
    *,
    coordinates: Mapping[str, tuple[float, float]] | None = None,
    prepared: PreparedAStar | None = None,
    incoming_edge_id: str | None = None,
    blocked_edges: Iterable[str] = (),
    time_penalties_s: Mapping[str, float] | None = None,
) -> AStarResult:
    """Find minimum estimated-time path subject to edge/turn legality.

    With no fully validated geometry, reverts automatically to a zero heuristic.
    The caller is responsible for separately verifying road-data completeness.
    """
    if source not in graph.vertices or destination not in graph.vertices:
        raise ValueError("Unknown source or destination")
    if incoming_edge_id is not None:
        incoming = graph.edges.get(incoming_edge_id)
        if incoming is None or incoming.target != source:
            raise ValueError("Incoming edge must end at route start")
    blocked = frozenset(blocked_edges)
    if not blocked <= graph.edges.keys():
        raise ValueError("Unknown blocked edge")
    penalties = dict(time_penalties_s or {})
    for name, delay in penalties.items():
        if name not in graph.edges or not isfinite(delay) or delay < 0:
            raise ValueError("Invalid penalty")
    if prepared is not None:
        if coordinates is not None:
            raise ValueError("Supply prepared state OR raw coordinates, not both")
        if prepared.graph is not graph:
            raise ValueError("Prepared geometry belongs to a different map graph")
        coordinates = prepared.coordinates
        can_heuristic = prepared.geographic_heuristic_valid
        maximum_mps = prepared.maximum_mps
    else:
        can_heuristic = coordinates is not None and _safe_geometry(graph, coordinates)
        maximum_mps = max((e.estimated_kph for e in graph.edges.values()), default=1.0) / 3.6
    if source == destination:
        return AStarResult(Route((), 0.0, 0.0), 0, bool(can_heuristic))
    # Incoming-edge search states share one destination-dependent value per
    # vertex. Keep this cache local to the request, never in prepared map state.
    heuristic_values: dict[str, float] = {}
    def heuristic(vertex: str) -> float:
        if not can_heuristic:
            return 0.0
        assert coordinates is not None
        # Subtract tolerance: avoid slight rounding making h larger than truth.
        if vertex not in heuristic_values:
            heuristic_values[vertex] = max(0.0, metres(coordinates[vertex], coordinates[destination]) - 0.02) / maximum_mps
        return heuristic_values[vertex]

    start = (source, incoming_edge_id)
    distances = {start: 0.0}
    predecessor: dict[tuple[str, str | None], tuple[tuple[str, str | None], str]] = {}
    sequence = count()
    heap = [(heuristic(source), next(sequence), 0.0, start)]
    goal = None
    expanded = 0
    while heap:
        _, _, cost, state = heappop(heap)
        if cost > distances[state]:
            continue
        expanded += 1
        vertex, previous = state
        if vertex == destination:
            goal = state
            break
        for edge in graph.adjacency[vertex]:
            if edge.access != "allowed" or edge.edge_id in blocked:
                continue
            if previous is not None and (previous, edge.edge_id) in graph.prohibited_turns:
                continue
            next_state = (edge.target, edge.edge_id)
            new_cost = cost + edge.estimated_seconds + penalties.get(edge.edge_id, 0)
            if new_cost < distances.get(next_state, float("inf")):
                distances[next_state] = new_cost
                predecessor[next_state] = (state, edge.edge_id)
                heappush(heap, (new_cost + heuristic(edge.target), next(sequence), new_cost, next_state))
    if goal is None:
        raise RouteNotFound("No legal route under current graph")
    ids = []
    state = goal
    while state != start:
        state, edge_id = predecessor[state]
        ids.append(edge_id)
    ids.reverse()
    result = Route(tuple(ids), sum(graph.edges[k].length_m for k in ids), distances[goal])
    return AStarResult(result, expanded, bool(can_heuristic))
