"""Isolated prototype of conservative, directed-road GPS matching.

Local geometry only. No networking, phone sensors, hidden maps, IMU fusion,
legal lane position, or real-device accuracy claims. Returns UNCERTAIN when
parallel roads, weak GPS, or insufficient evidence prevent identification.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, degrees, hypot, isfinite, radians
from typing import Mapping

from engine.routing import RoadGraph
from .fix_quality import GPSFix, assess_fix

METERS_PER_DEG_LAT = 111195.0

@dataclass(frozen=True)
class MatchResult:
    status: str  # MATCHED | AMBIGUOUS | UNKNOWN | REJECTED
    edge_id: str | None
    reason: str
    distance_m: float | None
    candidate_count: int

@dataclass(frozen=True)
class _Candidate:
    edge_id: str
    distance_m: float
    score: float
    heading: float

def angular_difference(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)

def _local(lat: float, lon: float, ref_lat: float, ref_lon: float) -> tuple[float, float]:
    return ((lon - ref_lon) * METERS_PER_DEG_LAT * cos(radians(ref_lat)),
            (lat - ref_lat) * METERS_PER_DEG_LAT)

def _closest_distance_and_bearing(fix: GPSFix, a: tuple[float, float],
                                  b: tuple[float, float]) -> tuple[float, float] | None:
    ax,ay=_local(a[0],a[1],fix.latitude,fix.longitude)
    bx,by=_local(b[0],b[1],fix.latitude,fix.longitude)
    vx,vy=bx-ax,by-ay
    norm=vx*vx+vy*vy
    if norm < 1e-8:
        return None
    fraction=max(0.0,min(1.0,-(ax*vx+ay*vy)/norm))
    cx,cy=ax+vx*fraction,ay+vy*fraction
    # 0 = north, 90 = east: the one-way travel direction matters.
    heading=(degrees(atan2(vx,vy))+360.0)%360.0
    return hypot(cx,cy),heading

class DirectedRoadMatcher:
    """Screen for plausible allowed directed road edges.

    Does not infer road/turn legality from GPS. Prior matching is accepted
    only as a soft continuity hint and never overrides independent ambiguity
    or contradictory heading. All thresholds are empirical *test parameters*.
    """
    def __init__(self, graph: RoadGraph, coordinates: Mapping[str,tuple[float,float]],
                 *, maximum_snap_m: float=35.0,
                 minimum_score_separation: float=0.85,
                 experimental_adjacent_fragment_equivalence: bool=False):
        if not isinstance(graph,RoadGraph):
            raise TypeError("Requires a directed RoadGraph")
        if not isfinite(maximum_snap_m) or maximum_snap_m<=0 or maximum_snap_m>1000:
            raise ValueError("Invalid snap distance")
        if not isfinite(minimum_score_separation) or minimum_score_separation<=0:
            raise ValueError("Invalid ambiguity separation")
        if type(experimental_adjacent_fragment_equivalence) is not bool:
            raise ValueError('Experimental mode must be boolean')
        # Default mode and previously frozen GPS-003 judgments are unchanged.
        self.experimental_adjacent_fragment_equivalence=experimental_adjacent_fragment_equivalence
        self.graph=graph
        self.maximum_snap_m=maximum_snap_m
        self.minimum_score_separation=minimum_score_separation
        self.coords={}
        for vertex in graph.vertices:
            value=coordinates.get(vertex)
            if value is None or len(value)!=2 or any(not isfinite(z) for z in value):
                raise ValueError("Every road vertex must have a finite coordinate")
            lat,lon=value
            if abs(lat)>90 or abs(lon)>180:
                raise ValueError("Invalid graph coordinates")
            self.coords[vertex]=(float(lat),float(lon))
        self._allowed=tuple(sorted(
            (e for e in graph.edges.values() if e.access=="allowed"),
            key=lambda e:e.edge_id))

    def _straight_same_way(self, first: _Candidate, other: _Candidate) -> bool:
        """Adjacent collinear pieces of one OSM way are not parallel roads.

        Arbitrary labels, different ways, diverging branches and opposing
        directions retain the existing ambiguity rules.
        """
        a, b = first.edge_id.split(':'), other.edge_id.split(':')
        if not (len(a) == len(b) == 4 and a[0] == b[0] == 'w'
                and a[1].isdigit() and a[1] == b[1]
                and a[2].isdigit() and b[2].isdigit()
                and a[3] in ('f', 'r') and b[3] in ('f', 'r')):
            return False
        left, right = self.graph.edges[first.edge_id], self.graph.edges[other.edge_id]
        contiguous = left.target == right.source or right.target == left.source
        return contiguous and angular_difference(first.heading, other.heading) < 1e-6

    def _experimental_same_way_bend(self, first: _Candidate, other: _Candidate,
                                     fix: GPSFix) -> bool:
        """Opt-in research hypothesis, NOT a verified safe driving matcher.

        Require an accurately aligned, moving fix and a clearly worse,
        physically adjacent, same-OSM-way same-direction fragment. Keep
        competing carriageways, different ways, prohibited turns, reverse
        directions, stationary fixes and sharp turns ambiguous.
        """
        if (fix.speed_mps is None or fix.speed_mps < 2.0 or
                fix.bearing_deg is None or fix.horizontal_accuracy_m > 5.0 or
                first.distance_m > fix.horizontal_accuracy_m or
                other.distance_m <= max(2.0*fix.horizontal_accuracy_m,
                                        first.distance_m+4.0) or
                angular_difference(first.heading,other.heading) > 8.0):
            return False
        a,b=first.edge_id.split(':'),other.edge_id.split(':')
        if not (len(a)==len(b)==4 and a[0]==b[0]=='w' and
                a[1].isdigit() and a[1]==b[1] and
                a[2].isdigit() and b[2].isdigit() and
                a[3]==b[3] and a[3] in ('f','r')):
            return False
        left,right=self.graph.edges[first.edge_id],self.graph.edges[other.edge_id]
        if right.target==left.source:
            return (other.edge_id,first.edge_id) not in self.graph.prohibited_turns
        if left.target==right.source:
            return (first.edge_id,other.edge_id) not in self.graph.prohibited_turns
        return False

    def _candidates(self, fix: GPSFix, prior_edge_id: str | None = None) -> list[_Candidate]:
        """One shared candidate policy for stateless and temporal matching."""
        moving=(fix.speed_mps is not None and fix.speed_mps >= 2.0 and
                fix.bearing_deg is not None)
        # A stationary or heading-less fix cannot disambiguate opposing links.
        # With a preceding accepted fix, a continuity hint helps only if the
        # new position independently supports that same road.
        contenders=[]
        max_radius=min(self.maximum_snap_m,max(8.0,fix.horizontal_accuracy_m*2.0))
        for edge in self._allowed:
            projection=_closest_distance_and_bearing(
                fix,self.coords[edge.source],self.coords[edge.target])
            if projection is None:
                continue
            distance,heading=projection
            if distance>max_radius:
                continue
            if moving and angular_difference(fix.bearing_deg,heading)>75.0:
                continue
            # Divide lateral error by a conservative uncertainty floor.
            # Candidate rank is a heuristic, not a posterior probability.
            noise=max(5.0,fix.horizontal_accuracy_m)
            lateral=(distance/noise)**2
            heading_penalty=0.0
            if moving:
                heading_penalty=0.7*(angular_difference(fix.bearing_deg,heading)/45.0)**2
            continuity=0.0
            if prior_edge_id is not None and edge.edge_id==prior_edge_id:
                continuity=-0.20
            elif prior_edge_id is not None and edge.edge_id in self.graph.edges:
                prior=self.graph.edges[prior_edge_id]
                if prior.target==edge.source and (
                        (prior_edge_id,edge.edge_id) not in self.graph.prohibited_turns):
                    continuity=-0.08
            contenders.append(_Candidate(edge.edge_id,distance,
                                          lateral+heading_penalty+continuity,heading))
        if not contenders:
            return []
        contenders.sort(key=lambda c: (c.score, c.distance_m, c.edge_id))
        first = contenders[0]
        return [first] + [c for c in contenders[1:]
                          if not self._straight_same_way(first, c)
                          and not (self.experimental_adjacent_fragment_equivalence
                                   and self._experimental_same_way_bend(first,c,fix))]

    def match(self, fix: GPSFix, *, previous_fix: GPSFix | None = None,
              prior_edge_id: str | None = None, now_ms: int | None = None) -> MatchResult:
        check=assess_fix(fix,previous=previous_fix,now_ms=now_ms)
        if check.status=="REJECTED":
            return MatchResult("REJECTED",None,check.reason,None,0)
        if check.status=="UNCERTAIN" and check.reason=="weak_position_accuracy":
            return MatchResult("UNKNOWN",None,"weak_position_accuracy",None,0)
        if prior_edge_id is not None and prior_edge_id not in self.graph.edges:
            raise ValueError("Unrecognized prior edge")
        contenders = self._candidates(fix, prior_edge_id)
        moving = (fix.speed_mps is not None and fix.speed_mps >= 2.0
                  and fix.bearing_deg is not None)
        if not contenders:
            return MatchResult("UNKNOWN",None,"no_supported_road_near_fix",None,0)
        first=contenders[0]
        # Do not turn a location coordinate into false road-level precision.
        # Heading can disambiguate opposing traffic directions, but NOT two
        # nearby *same-direction* roads that equally fit that heading. For
        # stationary / heading-less fixes, any close competing link is enough.
        if len(contenders)>1 and any(
                c.distance_m <= max(12.0,2.0*fix.horizontal_accuracy_m)
                for c in contenders[1:]):
            return MatchResult("AMBIGUOUS",None,
                               "nearby_parallel_or_overlapping_roads" if moving
                               else "insufficient_motion_to_disambiguate",
                               round(first.distance_m,2),len(contenders))
        if len(contenders)>1 and contenders[1].score-first.score<self.minimum_score_separation:
            return MatchResult("AMBIGUOUS",None,"multiple_plausible_roads",
                               round(first.distance_m,2),len(contenders))
        # No distinction by single-best proximity when heading is unavailable
        # *and* the fix is not precise enough to rule out a parallel road.
        # Existing candidates/score separation already enforce ambiguity.
        return MatchResult("MATCHED",first.edge_id,"directed_road_candidate",
                           round(first.distance_m,2),len(contenders))
