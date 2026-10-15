"""Conservative two-plus-fix candidate matcher for DMN research.

Uses a prior *unambiguously anchored* directed link to resolve a later
ambiguous fix only when exactly one locally plausible next link is topologically
reachable without crossing an OSM-prohibited mapped maneuver.

NOT dead reckoning, sensor fusion, lane positioning, a navigation controller,
or independently verified legality. Never assumes map completeness.
"""
from __future__ import annotations

from math import isfinite

from .fix_quality import GPSFix, assess_fix
from .matcher import (DirectedRoadMatcher, MatchResult,
                      _closest_distance_and_bearing, angular_difference)


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
        graph = self.matcher.graph
        if new_id == old_id:
            return True
        old, new = graph.edges[old_id], graph.edges[new_id]
        return old.target == new.source and (old_id, new_id) not in graph.prohibited_turns

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
        connected = {candidate for candidate in plausible
                     if self._connected(old, candidate)}
        moving = (fix.speed_mps is not None and fix.speed_mps >= 2.0
                  and fix.bearing_deg is not None)

        if base.status == "MATCHED":
            # Never trust a disconnected jump just because it happens to be
            # close to the noisy position. Keep the previous anchor briefly.
            if base.edge_id not in connected:
                self.unresolved += 1
                return MatchResult("AMBIGUOUS", None, "disconnected_road_jump",
                                   base.distance_m, len(plausible))
            self._remember(fix, base.edge_id)
            return base

        if base.status == "AMBIGUOUS" and moving and len(connected) == 1:
            chosen = next(iter(connected))
            # Historical topological connection is corroboration, not a
            # license to use a link the current heading/position disallows.
            self._remember(fix, chosen)
            return MatchResult("MATCHED", chosen, "unique_legal_temporal_connection",
                               base.distance_m, len(plausible))

        self.unresolved += 1
        return base
