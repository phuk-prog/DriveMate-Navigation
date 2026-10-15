"""Bounded passenger-car route alternative research on a directed, evidence-labelled graph.

Generates real paths for fastest, shortest, and balanced preferences using
turn-aware Dijkstra; enumerates bounded one-edge detour candidates. Graph
'access=allowed' is map semantics, NOT independently proven UK road legality.
Every result remains UNVERIFIED until dated, independent road/turn evidence
validates the route. No GPS history, live traffic, user data or Android UI.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from heapq import heappop, heappush
from itertools import count
from math import isfinite
from typing import Iterable, Mapping

from .driver_policy import DriverNavigationSettings, RouteOption
from .routing import RoadGraph, Route, RouteNotFound

_MODES = ("fastest", "shortest", "balanced")
_BALANCED_DISTANCE_FACTOR = 0.010
_BALANCED_COMPLEX_TURN_SECONDS = 20.0


@dataclass(frozen=True)
class GeneratedRoute:
    """A graph-based candidate: never a verified-legal route or official ETA."""
    route_id: str
    route: Route
    complex_maneuvers: int
    generated_by: tuple[str, ...]
    snapshot_id: str

    def as_unverified_option(self, *, eta_confidence: float = 0.0) -> RouteOption:
        """Force independent traffic/legality verification before selection."""
        return RouteOption(self.route_id, self.route.estimated_seconds,
                           self.route.length_m, eta_confidence,
                           self.complex_maneuvers,
                           independently_verified_legal=False,
                           evidence_current=False)


def _validate_edges(graph: RoadGraph, edge_ids: Iterable[str],
                    label: str) -> frozenset[str]:
    edges = frozenset(edge_ids)
    if edges - graph.edges.keys():
        raise ValueError(f"Unknown {label}")
    return edges


def _validate_turns(graph: RoadGraph,
                    turns: Iterable[tuple[str, str]]
                    ) -> frozenset[tuple[str, str]]:
    found = frozenset(tuple(pair) for pair in turns)
    for entering, leaving in found:
        a = graph.edges.get(entering)
        b = graph.edges.get(leaving)
        if a is None or b is None or a.target != b.source:
            raise ValueError("Unknown or disconnected maneuver complexity evidence")
    return found


def _validate_penalties(graph: RoadGraph,
                        penalties: Mapping[str, float] | None) -> dict[str, float]:
    values = dict(penalties or {})
    if values.keys() - graph.edges.keys():
        raise ValueError("Unknown delay-penalty edge")
    for value in values.values():
        if type(value) not in (int, float) or not isfinite(value) or value < 0:
            raise ValueError("Delay estimates must be finite and nonnegative")
    return values


def _edge_cost(edge, incoming_id: str | None, mode: str,
               settings: DriverNavigationSettings, penalty_s: float,
               complex_turns: frozenset[tuple[str, str]]) -> float:
    if mode == "shortest":
        return edge.length_m / 13.9  # ranking units, not travel-time estimate
    travel_s = edge.estimated_seconds + penalty_s
    if mode == "fastest":
        return travel_s
    complexity = int((incoming_id, edge.edge_id) in complex_turns)
    return (travel_s + _BALANCED_DISTANCE_FACTOR * edge.length_m
            + (_BALANCED_COMPLEX_TURN_SECONDS * complexity
               if settings.avoid_complex_maneuvers else 0.0))


def _search(graph: RoadGraph, source: str, destination: str,
            *, incoming_edge_id: str | None, blocked: frozenset[str],
            penalties: Mapping[str, float],
            complex_turns: frozenset[tuple[str, str]],
            settings: DriverNavigationSettings, mode: str) -> tuple[Route, int]:
    """Positive-weight shortest path over (vertex, incoming directed edge)."""
    if source == destination:
        return Route((), 0.0, 0.0), 0
    initial = (source, incoming_edge_id)
    best = {initial: 0.0}
    previous: dict[tuple[str, str | None],
                   tuple[tuple[str, str | None], str]] = {}
    counter = count()
    waiting = [(0.0, next(counter), initial)]
    terminal: tuple[str, str | None] | None = None
    while waiting:
        spent, _, state = heappop(waiting)
        if spent > best[state]:
            continue
        node, entering = state
        if node == destination:
            terminal = state
            break
        for edge in graph.adjacency[node]:
            if edge.access != "allowed" or edge.edge_id in blocked:
                continue
            if entering is not None and (entering, edge.edge_id) in graph.prohibited_turns:
                continue
            successor = (edge.target, edge.edge_id)
            total = spent + _edge_cost(edge, entering, mode, settings,
                                       penalties.get(edge.edge_id, 0.0), complex_turns)
            if total < best.get(successor, float("inf")):
                best[successor] = total
                previous[successor] = (state, edge.edge_id)
                heappush(waiting, (total, next(counter), successor))
    if terminal is None:
        raise RouteNotFound("No candidate with allowed mapped access and turns")
    edge_ids: list[str] = []
    state = terminal
    complex_count = 0
    while state != initial:
        past, edge_id = previous[state]
        if (past[1], edge_id) in complex_turns:
            complex_count += 1
        edge_ids.append(edge_id)
        state = past
    edge_ids.reverse()
    return (Route(tuple(edge_ids),
                  sum(graph.edges[x].length_m for x in edge_ids),
                  sum(graph.edges[x].estimated_seconds + penalties.get(x, 0.0)
                      for x in edge_ids)), complex_count)


def generate_route_candidates(
    graph: RoadGraph, source: str, destination: str, *,
    snapshot_id: str,
    settings: DriverNavigationSettings | None = None,
    incoming_edge_id: str | None = None,
    blocked_edges: Iterable[str] = (),
    time_penalties_s: Mapping[str, float] | None = None,
    verified_complex_turns: Iterable[tuple[str, str]] = (),
    max_candidates: int = 6,
    max_detour_searches: int = 12,
) -> tuple[GeneratedRoute, ...]:
    """Generate mode optima and bounded alternatives WITHOUT asserting truth.

    Traffic delays and verified maneuver-complexity facts are supplied by a
    separate trusted caller; invented speed/complexity truth is not inferred
    here. A caller must assess real-world restrictions and evidence freshness.
    Additional alternatives are partial one-edge-exclusion probes, NOT a
    complete k-shortest path enumeration.
    """
    if not isinstance(graph, RoadGraph):
        raise TypeError("Expected RoadGraph")
    policy = settings or DriverNavigationSettings()
    if not isinstance(policy, DriverNavigationSettings):
        raise TypeError("Expected DriverNavigationSettings")
    if not isinstance(snapshot_id, str) or not snapshot_id.strip() or len(snapshot_id) > 128:
        raise ValueError("Provide the public map snapshot identifier")
    if source not in graph.vertices or destination not in graph.vertices:
        raise ValueError("Unknown origin or destination")
    if incoming_edge_id is not None:
        previous = graph.edges.get(incoming_edge_id)
        if previous is None or previous.target != source:
            raise ValueError("Incoming edge must end at route origin")
    if type(max_candidates) is not int or not 3 <= max_candidates <= 12:
        raise ValueError("Allow 3..12 candidate routes")
    if type(max_detour_searches) is not int or not 0 <= max_detour_searches <= 32:
        raise ValueError("Bound detour-search attempts to 0..32")
    blocked = _validate_edges(graph, blocked_edges, "blocked edge")
    penalties = _validate_penalties(graph, time_penalties_s)
    complexity = _validate_turns(graph, verified_complex_turns)
    found: dict[tuple[str, ...], tuple[Route, int, set[str]]] = {}
    for mode in _MODES:
        route, maneuvers = _search(
            graph, source, destination,
            incoming_edge_id=incoming_edge_id,
            blocked=blocked, penalties=penalties, complex_turns=complexity,
            settings=policy, mode=mode)
        key = route.edge_ids
        if key in found:
            found[key][2].add(mode)
        else:
            found[key] = (route, maneuvers, {mode})
    primary = list(found)
    # Each primary optimum must survive the optional detour search.
    if len(found) < max_candidates and max_detour_searches:
        tried: set[str] = set()
        attempts = 0
        for key in primary:
            for edge_id in key:
                if attempts >= max_detour_searches:
                    break
                if edge_id in tried:
                    continue
                tried.add(edge_id)
                attempts += 1
                try:
                    route, maneuvers = _search(
                        graph, source, destination, incoming_edge_id=incoming_edge_id,
                        blocked=blocked | {edge_id}, penalties=penalties,
                        complex_turns=complexity, settings=policy, mode="balanced")
                except RouteNotFound:
                    continue
                if route.edge_ids not in found:
                    found[route.edge_ids] = (route, maneuvers, {"single_edge_detour"})
                if len(found) >= max_candidates:
                    break
            if len(found) >= max_candidates or attempts >= max_detour_searches:
                break
    # Keep all mode optima before detours; never replace a mode's optimum with
    # an arbitrary detour just because it has favorable provisional metrics.
    chosen = primary + [key for key in found if key not in primary][:max_candidates-len(primary)]
    result = []
    for key in chosen:
        route, maneuvers, produced = found[key]
        # Include map snapshot and all endpoints so the candidate ID cannot
        # silently carry over to a different graph version or trip.
        fingerprint = sha256(repr((snapshot_id, source, destination,
                                   incoming_edge_id, key)).encode("utf-8")).hexdigest()[:24]
        result.append(GeneratedRoute(
            "dmn:" + fingerprint, route, maneuvers,
            tuple(sorted(produced)), snapshot_id))
    return tuple(result)
