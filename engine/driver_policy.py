"""User-configurable route selection and reroute offer policy for DMN research.

This module is an independent, original decision-policy contract, not a live
traffic provider, route search algorithm, road-law oracle, timer, or Android UI.
The caller must supply legal, up-to-date route alternatives and reevaluate
safety before an actual maneuver or automatic switch.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Mapping, Sequence

ROUTE_MODES = ("fastest", "shortest", "balanced")
REROUTE_MODES = ("always_faster", "blocked_only", "intelligent")
THRESHOLD_MODES = ("any_saving", "fixed", "adaptive")
COUNTDOWN_MODES = ("fixed", "adaptive")
MIN_ETA_CONFIDENCE = 0.65  # experimental prediction gate, NOT legal confidence


def _finite(value: float, label: str, *, minimum: float = 0.0,
            maximum: float | None = None) -> float:
    if type(value) not in (int, float) or not isfinite(value) or value < minimum or (
            maximum is not None and value > maximum):
        raise ValueError(f"Invalid {label}")
    return float(value)


@dataclass(frozen=True)
class DriverNavigationSettings:
    """Selectable preferences; road access and driver safety are never optional."""
    route_mode: str = "balanced"
    reroute_mode: str = "intelligent"
    threshold_mode: str = "adaptive"
    fixed_benefit_seconds: float = 180.0
    countdown_mode: str = "adaptive"
    countdown_seconds: int = 5
    auto_switch_if_unanswered: bool = True
    avoid_complex_maneuvers: bool = True

    def __post_init__(self) -> None:
        for value, allowed, name in (
            (self.route_mode, ROUTE_MODES, "route mode"),
            (self.reroute_mode, REROUTE_MODES, "reroute mode"),
            (self.threshold_mode, THRESHOLD_MODES, "threshold mode"),
            (self.countdown_mode, COUNTDOWN_MODES, "countdown mode"),
        ):
            if value not in allowed:
                raise ValueError(f"Unknown {name}")
        _finite(self.fixed_benefit_seconds, "fixed improvement", minimum=1.0,
                maximum=3600.0)
        if type(self.countdown_seconds) is not int or not 3 <= self.countdown_seconds <= 7:
            raise ValueError("Countdown must be an integer from 3 to 7 seconds")
        if type(self.auto_switch_if_unanswered) is not bool or type(
                self.avoid_complex_maneuvers) is not bool:
            raise ValueError("Invalid boolean preference")

    def to_mapping(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "DriverNavigationSettings":
        if not isinstance(data, Mapping):
            raise ValueError("Preferences must be an object")
        expected = frozenset(cls.__dataclass_fields__)
        if set(data) - expected:
            raise ValueError("Unknown driver preferences")
        return cls(**data)


@dataclass(frozen=True)
class RouteOption:
    """An observed/precomputed candidate; not proof of independent UK road truth.

    Callers cannot use this type to *establish* legality or source freshness;
    the booleans are obligations to a separate independent evidence verifier.
    """
    route_id: str
    estimated_seconds: float
    distance_m: float
    eta_confidence: float
    complex_maneuvers: int
    independently_verified_legal: bool = False
    evidence_current: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.route_id, str) or not self.route_id.strip():
            raise ValueError("Missing route ID")
        _finite(self.estimated_seconds, "estimated time")
        _finite(self.distance_m, "distance")
        _finite(self.eta_confidence, "prediction confidence", maximum=1.0)
        if type(self.complex_maneuvers) is not int or self.complex_maneuvers < 0:
            raise ValueError("Invalid verified maneuver count")
        if type(self.independently_verified_legal) is not bool or type(
                self.evidence_current) is not bool:
            raise ValueError("Source verification must be explicit")


def _trusted(route: RouteOption) -> bool:
    return route.independently_verified_legal and route.evidence_current


def _objective(route: RouteOption, settings: DriverNavigationSettings) -> float:
    """Experimental ordering; distance normalized to time-equivalent units.

    Not a safety or independently observed ETA score. Search generation, actual
    traffic and turn count verification remain distinct implementation stages.
    """
    if settings.route_mode == "fastest":
        return route.estimated_seconds
    if settings.route_mode == "shortest":
        return route.distance_m / 13.9  # comparison units, NOT ETA or road speed
    return (route.estimated_seconds + 0.010 * route.distance_m
            + (20.0 * route.complex_maneuvers
               if settings.avoid_complex_maneuvers else 0.0)
            + 120.0 * (1.0 - route.eta_confidence))


def choose_preferred_route(candidates: Sequence[RouteOption],
                           settings: DriverNavigationSettings
                           ) -> RouteOption | None:
    """Choose among independently checked candidate routes, not raw OSM links.

    Unknown / stale / unverified routes cannot outrank verified candidates,
    even when their estimated time or distance looks attractive.
    """
    approved = [option for option in candidates if _trusted(option)]
    if not approved:
        return None
    return min(approved, key=lambda r: (_objective(r, settings), r.route_id))


@dataclass(frozen=True)
class RerouteOffer:
    offered: bool
    reason: str
    proposed_route_id: str | None
    countdown_seconds: int | None
    estimated_time_saving_seconds: float | None
    objective_benefit_units: float | None


def _no_offer(reason: str) -> RerouteOffer:
    return RerouteOffer(False, reason, None, None, None, None)


def _countdown(settings: DriverNavigationSettings,
               lead_seconds: float | None) -> int | None:
    if lead_seconds is not None:
        _finite(lead_seconds, "maneuver lead time")
    if settings.countdown_mode == "fixed" or lead_seconds is None:
        value = settings.countdown_seconds
    elif lead_seconds >= 45.0:
        value = 7
    elif lead_seconds <= 15.0:
        value = 3
    else:
        value = 5
    # Mandatory minimum preparation interval after the countdown.
    if lead_seconds is not None and lead_seconds < value + 5.0:
        return None
    return value


def consider_reroute(current: RouteOption, proposed: RouteOption,
                     settings: DriverNavigationSettings, *,
                     verified_current_route_blocked: bool = False,
                     maneuver_lead_seconds: float | None = None,
                     safe_to_offer: bool = True,
                     rejected_route_id: str | None = None,
                     cooldown_remaining_seconds: float = 0.0) -> RerouteOffer:
    """Determine whether to offer a vetted alternative, never directly drive it.

    Closure overrides preference benefit, not route legality, evidence freshness,
    maneuver lead or safe switching. The caller MUST independently establish a
    closure; no competitor report or map-only assumption is sufficient.
    """
    if type(verified_current_route_blocked) is not bool or type(safe_to_offer) is not bool:
        raise ValueError("Invalid reroute evidence")
    _finite(cooldown_remaining_seconds, "reroute cooldown")
    if current.route_id == proposed.route_id:
        return _no_offer("same_route")
    if not _trusted(proposed):
        return _no_offer("unverified_or_stale_alternative")
    if not safe_to_offer:
        return _no_offer("unsafe_to_propose_change")
    if not verified_current_route_blocked:
        if rejected_route_id == proposed.route_id:
            return _no_offer("driver_previously_rejected")
        if cooldown_remaining_seconds > 0.0:
            return _no_offer("stability_cooldown")
        if settings.reroute_mode == "blocked_only":
            return _no_offer("rerouting_disabled_until_blocked")
        if proposed.eta_confidence < MIN_ETA_CONFIDENCE:
            return _no_offer("unreliable_predicted_improvement")
    time_saved = current.estimated_seconds - proposed.estimated_seconds
    # The "always_faster" reroute control means *faster in time*, even when
    # route generation prefers short distance. Do not mislabel a shorter but
    # slower road as an always-faster reroute.
    benefit = (time_saved if settings.reroute_mode == "always_faster"
               else _objective(current, settings) - _objective(proposed, settings))
    if not verified_current_route_blocked:
        if settings.reroute_mode == "always_faster" and time_saved <= 0.0:
            return _no_offer("no_predicted_time_saving")
        if benefit <= 0.0:
            return _no_offer("no_objective_improvement")
        if settings.reroute_mode == "always_faster" or settings.threshold_mode == "any_saving":
            required = 0.0
        elif settings.threshold_mode == "fixed":
            required = settings.fixed_benefit_seconds
        else:
            # Calibratable research thresholds, not empirically proven optimum.
            required = max(45.0, min(240.0, 0.03 * current.estimated_seconds))
            if settings.avoid_complex_maneuvers:
                required += 15.0 * max(0, proposed.complex_maneuvers
                                       - current.complex_maneuvers)
        if benefit <= required:
            return _no_offer("improvement_below_threshold")
    countdown = _countdown(settings, maneuver_lead_seconds)
    if countdown is None:
        return _no_offer("insufficient_safe_lead_time")
    return RerouteOffer(True, "verified_closure" if verified_current_route_blocked
                        else "worthwhile_alternative", proposed.route_id,
                        countdown, time_saved, benefit)


@dataclass(frozen=True)
class SwitchDecision:
    action: str  # KEEP | WAIT | DEFER | SWITCH
    reason: str


def decide_reroute_switch(offer: RerouteOffer, settings: DriverNavigationSettings, *,
                          elapsed_seconds: float, driver_response: str = "none",
                          safe_to_switch: bool = False,
                          evidence_still_current: bool = False,
                          proposed_route_id: str | None = None) -> SwitchDecision:
    """Model a UI countdown decision; no timer, Android or actual reroute is run.

    Every accepted or automatic switch is revalidated AFTER the offered choice.
    Never switch based only on a previously displayed countdown.
    """
    _finite(elapsed_seconds, "countdown elapsed time")
    if driver_response not in ("none", "accept", "reject"):
        raise ValueError("Unknown driver response")
    if type(safe_to_switch) is not bool or type(evidence_still_current) is not bool:
        raise ValueError("Invalid safe switching evidence")
    if not offer.offered or offer.proposed_route_id is None or offer.countdown_seconds is None:
        return SwitchDecision("KEEP", "no_offer")
    if driver_response == "reject":
        return SwitchDecision("KEEP", "driver_rejected")
    if proposed_route_id != offer.proposed_route_id or not evidence_still_current:
        return SwitchDecision("DEFER", "alternative_changed_or_expired")
    if not safe_to_switch:
        return SwitchDecision("DEFER", "no_safe_verified_maneuver")
    if driver_response == "accept":
        return SwitchDecision("SWITCH", "driver_accepted")
    if not settings.auto_switch_if_unanswered:
        return SwitchDecision("WAIT", "automatic_switch_disabled")
    if elapsed_seconds < offer.countdown_seconds:
        return SwitchDecision("WAIT", "countdown_in_progress")
    return SwitchDecision("SWITCH", "unanswered_countdown_elapsed")
