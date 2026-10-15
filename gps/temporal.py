"""Conservative temporal GPS matcher, separate from single-fix candidate scoring.

Uses consecutive quality-screened fixes and graph connectivity to select a
road only when *one* plausible connected road sequence remains. No simulated
test can establish real device accuracy, lane location or actual road legality.
"""
from __future__ import annotations

from dataclasses import dataclass
from .fix_quality import GPSFix, assess_fix
from .matcher import DirectedRoadMatcher, MatchResult, _closest_distance_and_bearing, angular_difference

@dataclass(frozen=True)
class TemporalState:
    last_fix: GPSFix | None = None
    possible_edges: frozenset[str] = frozenset()
    consecutive_valid: int = 0

@dataclass(frozen=True)
class TemporalResult:
    match: MatchResult
    state: TemporalState

def advance(matcher: DirectedRoadMatcher, state: TemporalState,
            fix: GPSFix, *, now_ms: int | None = None) -> TemporalResult:
    """Update immutable state; uncertainty remains explicit.

    This is intentionally one-edge adjacency, not a full HMM or continuous
    distance-accurate trajectory solver. If time is insufficient to establish
    a connected path, do not pretend it was established.
    """
    quality=assess_fix(fix,previous=state.last_fix,now_ms=now_ms)
    if quality.status=="REJECTED":
        return TemporalResult(MatchResult("REJECTED",None,quality.reason,None,0),state)
    if quality.status=="UNCERTAIN":
        return TemporalResult(MatchResult("UNKNOWN",None,quality.reason,None,0),
                              TemporalState(fix,frozenset(),0))
    single=matcher.match(fix)
    if single.status in ("REJECTED","UNKNOWN"):
        return TemporalResult(single,TemporalState(fix,frozenset(),0))
    radius=min(matcher.maximum_snap_m,max(8.0,2*fix.horizontal_accuracy_m))
    candidates=set()
    for edge in matcher._allowed:
        p=_closest_distance_and_bearing(fix,matcher.coords[edge.source],matcher.coords[edge.target])
        if p is None or p[0]>radius:
            continue
        if fix.speed_mps is not None and fix.speed_mps>=2 and fix.bearing_deg is not None:
            if angular_difference(fix.bearing_deg,p[1])>75:
                continue
        candidates.add(edge.edge_id)
    if not state.possible_edges:
        chosen=frozenset(candidates)
    else:
        # Only same road or a graph-connected, legal outgoing movement.
        # In particular, physically close but disconnected carriageways
        # cannot be switched between without a mapped connecting road.
        connected=set()
        for eid in candidates:
            edge=matcher.graph.edges[eid]
            for prior_id in state.possible_edges:
                prior=matcher.graph.edges[prior_id]
                if eid==prior_id or (prior.target==edge.source and
                    (prior_id,eid) not in matcher.graph.prohibited_turns):
                    connected.add(eid)
                    break
        chosen=frozenset(connected)
        if not chosen:
            return TemporalResult(
                MatchResult("UNKNOWN",None,"no_verified_connected_transition",None,len(candidates)),
                TemporalState(fix,frozenset(),0))
    if len(chosen)==1 and state.consecutive_valid>=1:
        eid=next(iter(chosen))
        return TemporalResult(
            MatchResult("MATCHED",eid,"unique_connected_temporal_candidate",None,len(candidates)),
            TemporalState(fix,chosen,state.consecutive_valid+1))
    return TemporalResult(
        MatchResult("AMBIGUOUS",None,"temporal_evidence_insufficient",None,len(chosen)),
        TemporalState(fix,chosen,state.consecutive_valid+1))
