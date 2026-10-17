"""Read-only parallel GPS matching experiment for DMN navigation-engine tests.

Each fix goes to two independently owned temporal matchers. The conservative
default is the ONLY authoritative return. Experimental evidence never mutates
the baseline matcher, changes routing, or enables guidance.

This is a research helper: neither branch is verified by surveyed GNSS truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from engine.routing import RoadGraph
from .fix_quality import GPSFix
from .matcher import DirectedRoadMatcher, MatchResult
from .temporal_matcher import TemporalRoadMatcher


@dataclass(frozen=True)
class ShadowGPSObservation:
    baseline: MatchResult
    experimental: MatchResult | None
    experiment_error: str | None

    @property
    def baseline_authoritative(self) -> bool:
        return True

    @property
    def disagrees(self) -> bool:
        return self.experimental is not None and (
            self.baseline.status != self.experimental.status
            or self.baseline.edge_id != self.experimental.edge_id
        )


class GPSShadowComparison:
    """Feed identical observations to separate baseline and research matchers.

    The default is never promoted automatically, even if the shadow matches
    more generated-road labels. Shadow failures are reported, not concealed.
    """

    def __init__(self, graph: RoadGraph,
                 coordinates: Mapping[str, tuple[float, float]]) -> None:
        self._baseline = TemporalRoadMatcher(
            DirectedRoadMatcher(graph, coordinates))
        self._experimental = TemporalRoadMatcher(
            DirectedRoadMatcher(
                graph, coordinates,
                experimental_adjacent_fragment_equivalence=True))

    def reset(self) -> None:
        self._baseline.reset()
        self._experimental.reset()

    def update(self, fix: GPSFix, *, now_ms: int | None = None) -> ShadowGPSObservation:
        # Baseline result is computed first and is always the authoritative output.
        baseline = self._baseline.update(fix, now_ms=now_ms)
        try:
            experimental = self._experimental.update(fix, now_ms=now_ms)
        except Exception as exc:
            # Research-only failure must not suppress or change the baseline.
            return ShadowGPSObservation(
                baseline=baseline,
                experimental=None,
                experiment_error=type(exc).__name__ + ": " + str(exc)[:300])
        return ShadowGPSObservation(
            baseline=baseline, experimental=experimental,
            experiment_error=None)
