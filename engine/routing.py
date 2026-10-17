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

    def __post_init__(self) -> None:
        if not self.edge_id or not self.source or not self.target:
            raise ValueError("Edges require IDs and both endpoints")
        if self.source == self.target:
            raise ValueError("Self-loop edges are not supported by this prototype")
        if not isfinite(self.length_m) or self.length_m <= 0:
            raise ValueError("Edge length must be finite and positive")
        if not isfinite(self.estimated_kph) or self.estimated_kph <= 0:
            raise ValueError("Estimated speed must be finite and positive")
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


class RouteNotFound(ValueError):
    """No route under current access evidence and mapped turn restrictions."""


class RoadGraph:
    def __init__(
        self,
        vertices: Iterable[str],
        edges: Iterable[RoadEdge],
        prohibited_turns: Iterable[tuple[str, str]] = (),
        *, journey_destination: str | None = None,
        prohibited_sequences: Iterable[tuple[str, ...]] = (),
    ) -> None:
        self.vertices = frozenset(vertices)
        if not self.vertices or any(not v for v in self.vertices):
            raise ValueError("At least one valid vertex is required")
        if journey_destination is not None and journey_destination not in self.vertices:
            raise ValueError("Journey destination must be in the graph")
        self.journey_destination = journey_destination
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
        # Via-way restrictions: a prohibited *sequence* of three or more
        # consecutive edges (from, via..., to). Pairs stay in prohibited_turns.
        self.prohibited_sequences = frozenset(tuple(q) for q in prohibited_sequences)
        for sequence in self.prohibited_sequences:
            if len(sequence) < 3 or any(e not in self.edges for e in sequence):
                raise ValueError("Prohibited sequence needs three or more known edges")
            if any(self.edges[a].target != self.edges[b].source for a, b in zip(sequence, sequence[1:])):
                raise ValueError("Prohibited sequence is not a connected path")
        self._sequence_prefixes = frozenset(q[:k] for q in self.prohibited_sequences for k in range(1, len(q)))

    def transition(self, history: tuple[str, ...], edge_id: str) -> tuple[str, ...] | None:
        """Turn-legality step shared by every router.

        `history` is the minimal remembered tail of the path (its last edge, or
        a longer tail while a via-way restriction could still complete). Returns
        the new tail, or None when the move completes a prohibited turn/sequence.
        """
        if history and (history[-1], edge_id) in self.prohibited_turns:
            return None
        if not self.prohibited_sequences:
            return (edge_id,)
        path = history + (edge_id,)
        for k in range(len(path) - 2):
            if path[k:] in self.prohibited_sequences:
                return None
        for k in range(len(path)):
            if path[k:] in self._sequence_prefixes:
                return path[k:]
        return (edge_id,)


def shortest_route(
    graph: RoadGraph,
    source: str,
    destination: str,
    *,
    incoming_edge_id: str | None = None,
    blocked_edges: Iterable[str] = (),
    time_penalties_s: Mapping[str, float] | None = None,
    destination_edge_id: str | None = None,
) -> Route:
    """Dijkstra over (vertex, incoming-edge) states, respecting turn restrictions.

    Only edges explicitly tagged 'allowed' can be traversed; 'unknown' is not
    assumed legal. Penalties must be nonnegative; they never override access.
    Rerouting can pass the incoming edge so a prohibited turn stays prohibited.
    `destination_edge_id` makes the route finish by travelling that edge (a
    destination lies on a road, not at a junction), so the turn onto it is
    checked like any other; `destination` must then be that edge's end vertex.
    """
    if graph.journey_destination is not None and destination != graph.journey_destination:
        raise ValueError("Journey-scoped access cannot be reused for another destination")
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
    if destination_edge_id is not None:
        final = graph.edges.get(destination_edge_id)
        if final is None or final.target != destination:
            raise ValueError("Destination edge must end at the routing destination")
    elif source == destination:
        return Route((), 0.0, 0.0)

    begin: tuple[str, tuple[str, ...]] = (source, (incoming_edge_id,) if incoming_edge_id else ())
    best = {begin: 0.0}
    previous: dict[tuple[str, tuple[str, ...]], tuple[tuple[str, tuple[str, ...]], str]] = {}
    order = count()
    pending = [(0.0, next(order), begin)]
    goal: tuple[str, tuple[str, ...]] | None = None

    while pending:
        elapsed, _, state = heappop(pending)
        if elapsed > best[state]:
            continue
        vertex, history = state
        if vertex == destination and (destination_edge_id is None or (history and history[-1] == destination_edge_id)):
            goal = state
            break
        for edge in graph.adjacency[vertex]:
            if edge.access != "allowed" or edge.edge_id in blocked:
                continue
            tail = graph.transition(history, edge.edge_id)
            if tail is None:
                continue
            later = (edge.target, tail)
            candidate = elapsed + edge.estimated_seconds + penalties.get(edge.edge_id, 0.0)
            if candidate < best.get(later, float("inf")):
                best[later] = candidate
                previous[later] = (state, edge.edge_id)
                heappush(pending, (candidate, next(order), later))

    if goal is None:
        raise RouteNotFound("No route using allowed edges and mapped turn restrictions")
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
    )
