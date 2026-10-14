"""Deterministic shortest-time routing on a small directed, evidence-labelled graph.

Purpose: establish a reference-quality, testable safety contract before optimising
algorithms. This is an original Python prototype, not an Android/mobile engine.
Road lengths and estimated travel speeds must be supplied by a separate importer.
"""
from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from math import isfinite
from types import MappingProxyType
from typing import Iterable, Mapping


@dataclass(frozen=True)
class RoadEdge:
    edge_id: str
    source: str
    target: str
    length_m: float
    estimated_kph: float
    access: str = "unknown"  # allowed | prohibited | unknown
    junction: str = ""
    exit_group: str | None = None
    lane_evidence: object = None

    def __post_init__(self) -> None:
        if not self.edge_id or not self.source or not self.target:
            raise ValueError("Edges require IDs and both endpoints")
        if self.source == self.target:
            raise ValueError("Self-loop edges are not supported by this prototype")
        if not isfinite(self.length_m) or self.length_m <= 0:
            raise ValueError("Edge length must be finite and positive")
        if not isfinite(self.estimated_kph) or self.estimated_kph <= 0:
            raise ValueError("Estimated speed must be finite and positive")
        if not isinstance(self.junction,str):raise ValueError("Junction evidence must be a string")
        if self.exit_group is not None and (not isinstance(self.exit_group,str) or not self.exit_group):raise ValueError("Invalid exit group evidence")
        if self.access not in ("allowed", "prohibited", "unknown"):
            raise ValueError("Unknown road-access status")

    @property
    def estimated_seconds(self) -> float:
        return self.length_m / (self.estimated_kph / 3.6)


@dataclass(frozen=True)
class Route:
    edge_ids: tuple[str, ...]
    length_m: float
    estimated_seconds: float
    unverified_access_edges: tuple[str, ...] = ()


class RouteNotFound(ValueError):
    """No route exists using explicitly accessible links and legal turns."""


class RoadGraph:
    def __init__(
        self,
        vertices: Iterable[str],
        edges: Iterable[RoadEdge],
        prohibited_turns: Iterable[tuple[str, str]] = (),
        *, multi_restrictions=(), validity_window=None, extended_restrictions=(), lane_connections=(),
    ) -> None:
        self.extended_restrictions = tuple(multi_restrictions)+tuple(extended_restrictions)
        self.multi_restrictions = tuple(r for r in self.extended_restrictions if not getattr(r,"condition",None))
        self.validity_window = validity_window
        self.lane_connections = tuple(lane_connections)
        self.vertices = frozenset(vertices)
        if not self.vertices or any(not v for v in self.vertices):
            raise ValueError("At least one valid vertex is required")
        self.edges: dict[str, RoadEdge] = {}
        adjacency: dict[str, list[RoadEdge]] = {vertex: [] for vertex in self.vertices}
        for edge in edges:
            if edge.edge_id in self.edges:
                raise ValueError(f"Duplicate edge: {edge.edge_id}")
            if edge.source not in self.vertices or edge.target not in self.vertices:
                raise ValueError("An edge references an unknown vertex")
            self.edges[edge.edge_id] = edge
            adjacency[edge.source].append(edge)
        self.edges = MappingProxyType(self.edges)
        self.adjacency = MappingProxyType({
            vertex: tuple(sorted(items, key=lambda e: e.edge_id))
            for vertex, items in adjacency.items()
        })
        self.prohibited_turns = frozenset(tuple(t) for t in prohibited_turns)
        for entering, leaving in self.prohibited_turns:
            if entering not in self.edges or leaving not in self.edges:
                raise ValueError("Prohibited turn references unknown edge")
            if self.edges[entering].target != self.edges[leaving].source:
                raise ValueError("Prohibited turn connects unrelated edges")


def shortest_route(
    graph: RoadGraph,
    source: str,
    destination: str,
    *,
    incoming_edge_id: str | None = None,
    blocked_edges: Iterable[str] = (),
    time_penalties_s: Mapping[str, float] | None = None,
) -> Route:
    """Dijkstra over (vertex, incoming-edge) states, respecting turn restrictions.

    Unknown access alone does not exclude a road; it remains marked unverified
    in the result. Confirmed prohibitions remain blocked. Penalties must be
    nonnegative; they never override a prohibition.
    Rerouting can pass the incoming edge so a prohibited turn stays prohibited.
    """
    if graph.extended_restrictions or graph.validity_window:
        raise ValueError("Use reconciled navigation for multi-road or conditional graphs")
    if source not in graph.vertices or destination not in graph.vertices:
        raise ValueError("Unknown origin or destination")
    if incoming_edge_id is not None:
        prior = graph.edges.get(incoming_edge_id)
        if prior is None or prior.target != source:
            raise ValueError("Incoming edge must end at routing origin")
    blocked = frozenset(blocked_edges)
    if not blocked <= graph.edges.keys():
        raise ValueError("Blocked edge not in road graph")
    penalties = dict(time_penalties_s or {})
    for edge_id, seconds in penalties.items():
        if edge_id not in graph.edges or not isfinite(seconds) or seconds < 0:
            raise ValueError("Invalid additional edge-time penalty")
    if source == destination:
        return Route((), 0.0, 0.0)

    begin = (source, incoming_edge_id)
    best = {begin: 0.0}
    previous: dict[tuple[str, str | None], tuple[tuple[str, str | None], str]] = {}
    order = count()
    pending = [(0.0, next(order), begin)]
    goal: tuple[str, str | None] | None = None

    while pending:
        elapsed, _, state = heappop(pending)
        if elapsed > best[state]:
            continue
        vertex, entering = state
        if vertex == destination:
            goal = state
            break
        for edge in graph.adjacency[vertex]:
            if edge.access == "prohibited" or edge.edge_id in blocked:
                continue
            if entering is not None and (entering, edge.edge_id) in graph.prohibited_turns:
                continue
            later = (edge.target, edge.edge_id)
            candidate = elapsed + edge.estimated_seconds + penalties.get(edge.edge_id, 0.0)
            if candidate < best.get(later, float("inf")):
                best[later] = candidate
                previous[later] = (state, edge.edge_id)
                heappush(pending, (candidate, next(order), later))

    if goal is None:
        raise RouteNotFound("No route using available allowed roads and legal turns")
    ids: list[str] = []
    state = goal
    while state != begin:
        state, edge_id = previous[state]
        ids.append(edge_id)
    ids.reverse()
    return Route(
        edge_ids=tuple(ids),
        length_m=sum(graph.edges[edge_id].length_m for edge_id in ids),
        estimated_seconds=best[goal],
        unverified_access_edges=tuple(e for e in ids if graph.edges[e].access == "unknown"),
    )
