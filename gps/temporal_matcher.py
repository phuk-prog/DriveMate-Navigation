"""Conservative two-plus-fix candidate matcher for DMN research.

Uses a prior *unambiguously anchored* directed link to resolve a later
ambiguous fix only when exactly one locally plausible next link is topologically
reachable without crossing an OSM-prohibited mapped maneuver and its minimum
travel distance through the connecting junction fits the observed time budget.
Same-edge history must also support forward progress within reported uncertainty.

NOT dead reckoning, sensor fusion, lane positioning, a navigation controller,
or independently verified legality. Never assumes map completeness.
"""
from __future__ import annotations

from math import hypot, isfinite
from heapq import heappop, heappush
from itertools import count

from .fix_quality import GPSFix, assess_fix, _distance_m
from .matcher import (DirectedRoadMatcher, MatchResult,
                      _closest_distance_and_bearing, _local, angular_difference)


class TemporalRoadMatcher:
    def __init__(self, matcher: DirectedRoadMatcher, *,
                 max_anchor_age_ms: int = 20_000,
                 max_unresolved_fixes: int = 2,
                 max_anchor_displacement_m: float = 100.0):
        if not isinstance(matcher, DirectedRoadMatcher):
            raise TypeError("Expected a DirectedRoadMatcher")
        if not isinstance(max_anchor_age_ms, int) or max_anchor_age_ms <= 0:
            raise ValueError("Invalid anchor lifetime")
        if not isinstance(max_unresolved_fixes, int) or max_unresolved_fixes < 0:
            raise ValueError("Invalid unresolved-fix count")
        if not isfinite(max_anchor_displacement_m) or max_anchor_displacement_m <= 0:
            raise ValueError("Invalid anchor displacement")
        self.matcher = matcher
        self.max_anchor_age_ms = max_anchor_age_ms
        self.max_unresolved_fixes = max_unresolved_fixes
        self.max_anchor_displacement_m = max_anchor_displacement_m
        self.reset()

    def reset(self) -> None:
        self.anchor_edge_id: str | None = None
        self.anchor_fix: GPSFix | None = None
        self.previous_valid_fix: GPSFix | None = None
        self.unresolved = 0

    def _connected(self, old_id: str, new_id: str) -> bool:
        return self._connection_length(old_id, new_id) is not None

    def _connection_length(self, old_id: str, new_id: str) -> float | None:
        """Bounded turn-aware connector between observed directed segments.

        At most eight intermediate links and 128 expanded states. Exhausting
        this local research bound withholds confidence, never invents a path.
        Distances are measured graph lengths; access and turn rules still apply.
        """
        graph = self.matcher.graph
        if new_id == old_id:
            return 0.0
        old, new = graph.edges[old_id], graph.edges[new_id]
        serial = count()
        pending = [(0.0, next(serial), old.target, old_id, 0)]
        best = {(old.target, old_id, 0): 0.0}
        expanded = 0
        while pending and expanded < 128:
            distance, _, vertex, entering, hops = heappop(pending)
            if distance > best[(vertex, entering, hops)]:
                continue
            expanded += 1
            if vertex == new.source and (entering, new_id) not in graph.prohibited_turns:
                return distance
            if hops == 8:
                continue
            for edge in graph.adjacency[vertex]:
                if edge.access != 'allowed' or (entering, edge.edge_id) in graph.prohibited_turns:
                    continue
                later = (edge.target, edge.edge_id, hops + 1)
                candidate = distance + edge.length_m
                if candidate < best.get(later, float('inf')):
                    best[later] = candidate
                    heappush(pending, (candidate, next(serial), *later))
        return None

    def _transition_fits_time(self, old_id: str, new_id: str, fix: GPSFix,
                              connector_length: float | None = None) -> bool:
        """Bound travel via the shared junction, not just between GPS fixes.

        Great-circle distances to/from that junction are lower bounds even
        when the actual roads curve. Subtract both uncertainty radii and use
        the anchor's time/speed: intervening unresolved fixes cannot shorten
        the required trip or refresh the trusted position. This is a bounded
        one-junction screen, not proof of a vehicle's route or legal movement.
        """
        if old_id == new_id:
            return self._same_edge_direction_fits(old_id, fix)
        assert self.anchor_fix is not None
        if connector_length is None:
            connector_length = self._connection_length(old_id, new_id)
        if connector_length is None:
            return False
        junction = self.matcher.coords[self.matcher.graph.edges[old_id].target]
        vertex_fix = GPSFix(0, junction[0], junction[1], 0.0)
        new_start = self.matcher.coords[self.matcher.graph.edges[new_id].source]
        entry_fix = GPSFix(0, new_start[0], new_start[1], 0.0)
        minimum_distance = max(
            0.0, _distance_m(self.anchor_fix, vertex_fix)
            + connector_length + _distance_m(entry_fix, fix)
            - self.anchor_fix.horizontal_accuracy_m - fix.horizontal_accuracy_m)
        seconds = (fix.timestamp_ms - self.anchor_fix.timestamp_ms) / 1000.0
        # Match the existing displacement screen's generous reported-speed
        # tolerance, capped by assess_fix's generic physical plausibility gate.
        limit = 90.0
        if self.anchor_fix.speed_mps is not None and fix.speed_mps is not None:
            limit = min(limit, max(20.0, 3.0 * max(
                self.anchor_fix.speed_mps, fix.speed_mps)))
        return minimum_distance <= limit * seconds

    def _same_edge_direction_fits(self, edge_id: str, fix: GPSFix) -> bool:
        """Withhold reverse progress beyond both reported uncertainty radii.

        Use one fixed local frame for the road and both observations. This
        checks the prototype's straight directed segment, not a curved-road
        polyline or proof that the vehicle made an illegal manoeuvre.
        """
        assert self.anchor_fix is not None
        edge = self.matcher.graph.edges[edge_id]
        origin = self.matcher.coords[edge.source]
        target = self.matcher.coords[edge.target]
        dx, dy = _local(*target, *origin)
        length = hypot(dx, dy)
        if length < 1e-4:
            return False
        before_x, before_y = _local(
            self.anchor_fix.latitude, self.anchor_fix.longitude, *origin)
        after_x, after_y = _local(fix.latitude, fix.longitude, *origin)
        progress = ((after_x - before_x) * dx + (after_y - before_y) * dy) / length
        uncertainty = self.anchor_fix.horizontal_accuracy_m + fix.horizontal_accuracy_m
        return progress >= -uncertainty

    def _plausible_edges(self, fix: GPSFix) -> set[str]:
        """Mirror stateless candidate gate, excluding prohibited/unknown roads."""
        result = set()
        moving = (fix.speed_mps is not None and fix.speed_mps >= 2.0
                  and fix.bearing_deg is not None)
        radius = min(self.matcher.maximum_snap_m, max(8.0, 2*fix.horizontal_accuracy_m))
        for edge in self.matcher._allowed:
            projection = _closest_distance_and_bearing(
                fix, self.matcher.coords[edge.source],
                self.matcher.coords[edge.target])
            if projection is None:
                continue
            distance, heading = projection
            if distance > radius:
                continue
            if moving and angular_difference(fix.bearing_deg, heading) > 75.0:
                continue
            result.add(edge.edge_id)
        return result

    def _live_anchor(self, fix: GPSFix) -> bool:
        if self.anchor_fix is None or self.anchor_edge_id is None:
            return False
        age = fix.timestamp_ms - self.anchor_fix.timestamp_ms
        if age <= 0 or age > self.max_anchor_age_ms:
            return False
        from .fix_quality import _distance_m
        if _distance_m(fix, self.anchor_fix) > (
                self.max_anchor_displacement_m
                + fix.horizontal_accuracy_m
                + self.anchor_fix.horizontal_accuracy_m):
            return False
        return self.unresolved <= self.max_unresolved_fixes

    def _remember(self, fix: GPSFix, edge_id: str) -> None:
        self.anchor_edge_id = edge_id
        self.anchor_fix = fix
        self.unresolved = 0

    def update(self, fix: GPSFix, *, now_ms: int | None = None) -> MatchResult:
        quality = assess_fix(fix, previous=self.previous_valid_fix, now_ms=now_ms)
        if quality.status == "REJECTED":
            # A rejected input cannot move our anchor or replace the last
            # accepted GNSS fix; two consecutive bad fixes expire confidence.
            self.unresolved += 1
            if self.unresolved > self.max_unresolved_fixes:
                self.anchor_edge_id = None
                self.anchor_fix = None
            return MatchResult("REJECTED", None, quality.reason, None, 0)

        if quality.reason == "weak_position_accuracy":
            self.unresolved += 1
            if self.unresolved > self.max_unresolved_fixes:
                self.anchor_edge_id = None
                self.anchor_fix = None
            self.previous_valid_fix = fix
            return MatchResult("UNKNOWN", None, "weak_position_accuracy", None, 0)

        # A topologically connected road is NOT proof that the vehicle could
        # traverse the displacement in the observed time. Existing fix-quality
        # tests reject >90 m/s; this second, deliberately conservative guard
        # detects large disagreements against the vehicle's OWN reported speed.
        # 20 m/s minimum tolerates urban GPS jitter; speed is never a UK speed
        # limit or independent evidence that the vehicle followed a legal road.
        if (self.previous_valid_fix is not None
                and self.previous_valid_fix.speed_mps is not None
                and fix.speed_mps is not None):
            from .fix_quality import _distance_m
            seconds=(fix.timestamp_ms-self.previous_valid_fix.timestamp_ms)/1000
            minimum_distance=max(
                0.0,_distance_m(self.previous_valid_fix,fix)
                -self.previous_valid_fix.horizontal_accuracy_m
                -fix.horizontal_accuracy_m)
            limit=max(20.0,3.0*max(self.previous_valid_fix.speed_mps,fix.speed_mps))
            if minimum_distance/seconds>limit:
                self.unresolved+=1
                if self.unresolved>self.max_unresolved_fixes:
                    self.anchor_edge_id=None
                    self.anchor_fix=None
                return MatchResult("REJECTED",None,"distance_speed_disagreement",
                                   None,0)
        base = self.matcher.match(fix, previous_fix=self.previous_valid_fix, now_ms=now_ms)
        self.previous_valid_fix = fix

        # Without fresh, trusted history, never invent confidence from one
        # ambiguous point. Preserve legacy behaviour for easy fixes.
        if not self._live_anchor(fix):
            self.anchor_edge_id = None
            self.anchor_fix = None
            if base.status == "MATCHED":
                self._remember(fix, base.edge_id)
            else:
                self.unresolved += 1
            return base

        old = self.anchor_edge_id
        assert old is not None
        plausible = self._plausible_edges(fix)
        connections = {candidate: self._connection_length(old, candidate)
                       for candidate in plausible}
        connected = {candidate for candidate, distance in connections.items()
                     if distance is not None}
        reachable = {candidate for candidate in connected
                     if self._transition_fits_time(old, candidate, fix, connections[candidate])}
        moving = (fix.speed_mps is not None and fix.speed_mps >= 2.0
                  and fix.bearing_deg is not None)

        if base.status == "MATCHED":
            # Never trust a disconnected jump just because it happens to be
            # close to the noisy position. Keep the previous anchor briefly.
            if base.edge_id not in reachable:
                self.unresolved += 1
                if base.edge_id == old:
                    reason = "backward_directed_progress"
                else:
                    reason = ("implausible_road_transition" if base.edge_id in connected
                              else "disconnected_road_jump")
                return MatchResult("AMBIGUOUS", None, reason,
                                   base.distance_m, len(plausible))
            self._remember(fix, base.edge_id)
            return base

        if base.status == "AMBIGUOUS" and moving and len(reachable) == 1:
            chosen = next(iter(reachable))
            # Historical topological connection is corroboration, not a
            # license to use a link the current heading/position disallows.
            self._remember(fix, chosen)
            return MatchResult("MATCHED", chosen, "unique_legal_temporal_connection",
                               base.distance_m, len(plausible))

        self.unresolved += 1
        return base
