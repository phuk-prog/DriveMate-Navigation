"""Input-quality gate for a proposed DMN GPS pipeline, not a map matcher.

Works with public-fixture or simulated GNSS fixes. No assumption of real
device accuracy, road membership, legal speed limit, sensor fusion or driver route.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, isfinite, radians, sin, sqrt


@dataclass(frozen=True)
class GPSFix:
    timestamp_ms: int
    latitude: float
    longitude: float
    horizontal_accuracy_m: float
    speed_mps: float | None = None
    bearing_deg: float | None = None

    def __post_init__(self):
        if type(self.timestamp_ms) is not int or self.timestamp_ms < 0:
            raise ValueError("Invalid nonnegative monotonic-source millisecond timestamp")
        values = (self.latitude, self.longitude, self.horizontal_accuracy_m)
        if any(not isinstance(v, (float, int)) or not isfinite(v) for v in values):
            raise ValueError("GPS coordinates and accuracy must be finite")
        if abs(self.latitude) > 90 or abs(self.longitude) > 180:
            raise ValueError("Invalid geographic coordinates")
        if self.horizontal_accuracy_m < 0:
            raise ValueError("Horizontal accuracy cannot be negative")
        if self.speed_mps is not None and (
                not isfinite(self.speed_mps) or self.speed_mps < 0):
            raise ValueError("GNSS speed must be nonnegative and finite")
        if self.bearing_deg is not None and (
                not isfinite(self.bearing_deg) or not 0 <= self.bearing_deg < 360):
            raise ValueError("Bearing must be in [0,360)")


@dataclass(frozen=True)
class FixAssessment:
    status: str  # VALID | UNCERTAIN | REJECTED
    reason: str
    implied_speed_mps: float | None


def _distance_m(a: GPSFix, b: GPSFix) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (
        a.latitude, a.longitude, b.latitude, b.longitude))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 12_742_000 * asin(min(1.0, sqrt(max(0.0, h))))


def assess_fix(fix: GPSFix, *, previous: GPSFix | None = None,
               now_ms: int | None = None, max_age_ms: int = 10_000,
               max_plausible_speed_mps: float = 90.0,
               uncertainty_threshold_m: float = 35.0) -> FixAssessment:
    """Conservative quality screen; thresholds are test parameters, not UK traffic law.

    Error radii reduce the displacement lower bound, so a poor fix is marked
    UNCERTAIN rather than falsely rejected for noisy position displacement.
    """
    if type(max_age_ms) is not int or max_age_ms < 0:
        raise ValueError("Invalid maximum age")
    if not isfinite(max_plausible_speed_mps) or max_plausible_speed_mps <= 0:
        raise ValueError("Invalid maximum plausible speed")
    if not isfinite(uncertainty_threshold_m) or uncertainty_threshold_m < 0:
        raise ValueError("Invalid confidence threshold")
    if now_ms is not None:
        if type(now_ms) is not int or now_ms < 0:
            raise ValueError("Invalid observation time")
        if fix.timestamp_ms > now_ms:
            return FixAssessment("REJECTED", "future_timestamp", None)
        if now_ms - fix.timestamp_ms > max_age_ms:
            return FixAssessment("REJECTED", "stale_timestamp", None)
    if previous is not None and fix.timestamp_ms <= previous.timestamp_ms:
        return FixAssessment("REJECTED", "duplicate_or_out_of_order", None)
    if fix.speed_mps is not None and fix.speed_mps > max_plausible_speed_mps:
        return FixAssessment("REJECTED", "implausible_reported_speed", None)
    implied = None
    if previous is not None:
        elapsed_s = (fix.timestamp_ms - previous.timestamp_ms) / 1000.0
        # Lower bound on physically traveled distance after both error radii.
        displacement = max(0.0, _distance_m(fix, previous) -
                           fix.horizontal_accuracy_m - previous.horizontal_accuracy_m)
        implied = displacement / elapsed_s
        if implied > max_plausible_speed_mps:
            return FixAssessment("REJECTED", "implausible_position_jump", implied)
    if fix.horizontal_accuracy_m > uncertainty_threshold_m:
        return FixAssessment("UNCERTAIN", "weak_position_accuracy", implied)
    if fix.bearing_deg is None:
        return FixAssessment("UNCERTAIN", "heading_unavailable", implied)
    return FixAssessment("VALID", "basic_quality_accepted", implied)
