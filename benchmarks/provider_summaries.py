"""Parse only aggregate route metrics from local, authorised reference output.

NO HTTP clients, GPS ingestion, coordinates, route geometry, turn instructions
or source responses are retained. This is an offline compatibility adapter,
not a claim that external engines were run or are equally configured.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping, Any


@dataclass(frozen=True)
class RouteSummary:
    provider: str
    distance_m: float
    estimated_seconds: float

    def __post_init__(self):
        if not self.provider or any(not isfinite(x) or x < 0
                                    for x in (self.distance_m, self.estimated_seconds)):
            raise ValueError("Invalid aggregate route result")


def _positive_float(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"Invalid {label}")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Missing/invalid {label}") from exc
    if not isfinite(number) or number < 0:
        raise ValueError(f"Invalid {label}")
    return number


def _mapping(value: Any) -> Mapping:
    if not isinstance(value, Mapping):
        raise ValueError("Expected a JSON object")
    return value


def summarise(provider: str, response: Mapping[str, Any]) -> RouteSummary:
    """Only route distance and estimated duration; no identity, coordinates or itinerary."""
    response = _mapping(response)
    try:
        if provider == "OSRM":
            route = _mapping(response["routes"][0])
            metres = _positive_float(route["distance"], "distance (metres)")
            seconds = _positive_float(route["duration"], "duration (seconds)")
        elif provider == "Valhalla":
            trip = _mapping(response["trip"])
            summary = _mapping(trip["summary"])
            unit = trip.get("units", "kilometers")
            if unit not in ("kilometers", "miles"):
                raise ValueError("Unknown Valhalla units")
            factor = 1000.0 if unit == "kilometers" else 1609.344
            metres = _positive_float(summary["length"], "distance") * factor
            seconds = _positive_float(summary["time"], "duration (seconds)")
        elif provider == "GraphHopper":
            path = _mapping(response["paths"][0])
            metres = _positive_float(path["distance"], "distance (metres)")
            seconds = _positive_float(path["time"], "duration (milliseconds)") / 1000.0
        else:
            raise ValueError("Unsupported reference provider")
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Missing required aggregate response fields") from exc
    return RouteSummary(provider, metres, seconds)
