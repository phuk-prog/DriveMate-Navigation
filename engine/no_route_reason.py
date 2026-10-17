"""Why there is no legal route (owner-approved, 17 Oct 2026).

When shortest_route finds nothing, the driver should be told why, e.g. "the only way is
through a bus gate", not just "no route". This relaxes one rule at a time and reports
the first relaxation that would give a route. It never returns that route for driving:
it is an explanation only, and every rule stays in force for real routing.

  ONLY_VIA_UNCERTAIN_ACCESS  only through a private / access-only / unclear road or gate
  ONLY_VIA_CLOSED_ROAD       only through a road or barrier closed to cars (bus gate, busway
                             with car access mapped, "no motor vehicles", closed barrier)
  ONLY_VIA_BANNED_TURN       only by making a mapped banned turn
  NOT_CONNECTED              no way at all in this map (or the map is cut short here)
"""
from __future__ import annotations

from dataclasses import replace

from .routing import RoadGraph, RouteNotFound, shortest_route


def _relaxed(graph: RoadGraph, *, open_unknown: bool, open_prohibited: bool, drop_turns: bool) -> RoadGraph:
    edges = [replace(e, access="allowed") if (e.access == "unknown" and open_unknown)
             or (e.access == "prohibited" and open_prohibited) else e for e in graph.edges.values()]
    return RoadGraph(graph.vertices, edges,
                     () if drop_turns else graph.prohibited_turns,
                     journey_destination=graph.journey_destination,
                     prohibited_sequences=() if drop_turns else graph.prohibited_sequences)


def explain_no_route(graph: RoadGraph, source: str, destination: str, *, incoming_edge_id: str | None = None,
                     destination_edge_id: str | None = None) -> dict:
    steps = (("ONLY_VIA_UNCERTAIN_ACCESS", dict(open_unknown=True, open_prohibited=False, drop_turns=False)),
             ("ONLY_VIA_CLOSED_ROAD", dict(open_unknown=True, open_prohibited=True, drop_turns=False)),
             ("ONLY_VIA_BANNED_TURN", dict(open_unknown=True, open_prohibited=True, drop_turns=True)))
    for reason, relax in steps:
        trial = _relaxed(graph, **relax)
        try:
            route = shortest_route(trial, source, destination, incoming_edge_id=incoming_edge_id,
                                   destination_edge_id=destination_edge_id, endpoint_uncertain_access=True)
        except RouteNotFound:
            continue
        blocking = [e for e in route.edge_ids if graph.edges[e].access != "allowed"]
        if reason == "ONLY_VIA_BANNED_TURN":
            blocking = [f"{a}->{b}" for a, b in zip(route.edge_ids, route.edge_ids[1:])
                        if (a, b) in graph.prohibited_turns] or ["turn sequence"]
        return {"reason": reason, "blocking": blocking[:10]}
    return {"reason": "NOT_CONNECTED", "blocking": []}
