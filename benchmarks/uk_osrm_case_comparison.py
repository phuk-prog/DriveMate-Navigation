"""OSRM on the SAME pinned OSM snapshot and regenerated UK research endpoints.

This is a local reference *observation*, never independent legal/traffic truth.
OSRM's car.lua routing weights, road snapping and graph are not DMN's; even a
successful endpoint snap is not a valid numerical navigation-quality ranking.
All route coordinates and HTTP URLs remain ephemeral and are NOT reported.
"""
from __future__ import annotations

from collections import Counter
from math import isfinite
from typing import Callable, Sequence

from benchmarks.osrm_live_reference import local_osrm_request, local_route_url

SNAP_MAX_METRES = 15.0
RESULT_STATUSES = frozenset((
    "ENDPOINTS_NEAR_DIFFERENT_PROFILES",
    "SNAP_MISMATCH_NOT_COMPARABLE",
    "OSRM_NO_ROUTE",
    "OSRM_NO_SEGMENT",
))


def _metres(value: object, label: str) -> float:
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        raise ValueError("Invalid OSRM " + label)
    return float(value)


def compare_osrm_case(case: dict, origin: tuple[float, float],
                      destination: tuple[float, float], *,
                      request: Callable[[str], dict] = local_osrm_request) -> dict:
    """Query local OSRM once using precisely the DMN public-map endpoints.

    Return only a hashed case identifier, numerical distances/durations,
    waypoint snap distances and a conservative non-ranking classification.
    """
    if (case.get("map_only_test_case") is not True or
            case.get("independent_current_uk_road_legality") != "UNKNOWN" or
            case.get("competitor_outcomes") != "NOT_RUN"):
        raise ValueError("Not a pinned, unverified DMN public-map case")
    case_id = case.get("case_id")
    if not isinstance(case_id, str) or not case_id.startswith("dmn-mapcase-"):
        raise ValueError("Invalid deterministic case identifier")
    response = request(local_route_url(origin, destination))
    if not isinstance(response, dict):
        raise ValueError("Invalid local OSRM response")
    code = response.get("code")
    result = {
        "case_id": case_id,
        "reference_engine": "OSRM MLD 5.27.1 pinned car.lua",
        "same_map_snapshot": case["map_snapshot"],
        "dmn_fastest_mapped_distance_m": case["fastest_length_m"],
        "dmn_fastest_mapped_seconds": case["fastest_estimated_seconds"],
        "independent_current_uk_road_legality": "UNKNOWN",
        "driver_navigation_quality_comparable": False,
    }
    if code in ("NoRoute", "NoSegment"):
        result["status"] = "OSRM_NO_ROUTE" if code == "NoRoute" else "OSRM_NO_SEGMENT"
        return result
    if code != "Ok":
        raise ValueError("Unsupported OSRM status")
    waypoints = response.get("waypoints")
    routes = response.get("routes")
    if (not isinstance(waypoints, list) or len(waypoints) != 2 or
            not all(isinstance(w, dict) for w in waypoints) or
            not isinstance(routes, list) or not routes or
            not isinstance(routes[0], dict)):
        raise ValueError("Incomplete OSRM route or waypoint response")
    origin_snap = _metres(waypoints[0].get("distance"), "origin snap")
    destination_snap = _metres(waypoints[1].get("distance"), "destination snap")
    result.update({
        "osrm_distance_m": round(_metres(routes[0].get("distance"), "route distance"), 3),
        "osrm_estimated_seconds": round(_metres(routes[0].get("duration"), "route duration"), 3),
        "origin_snap_m": round(origin_snap, 3),
        "destination_snap_m": round(destination_snap, 3),
        "status": ("ENDPOINTS_NEAR_DIFFERENT_PROFILES"
                   if max(origin_snap, destination_snap) <= SNAP_MAX_METRES
                   else "SNAP_MISMATCH_NOT_COMPARABLE"),
    })
    return result


def distance_discrepancy_triage(rows: Sequence[dict]) -> dict:
    """Prioritize *investigation*, NOT a route winner, from observed distances.

    Unlike fast/shortest rankings this is not proof of a missed illegal turn:
    two driving profiles and geometry estimators may disagree legitimately.
    """
    flagged = []
    secondary = 0
    for row in rows:
        if row["status"] != "ENDPOINTS_NEAR_DIFFERENT_PROFILES":
            continue
        dmn = row["dmn_fastest_mapped_distance_m"]
        osrm = row["osrm_distance_m"]
        absolute_gap = abs(osrm - dmn)
        denominator = max(osrm, dmn)
        gap_pct = 100 * absolute_gap / denominator if denominator else 0
        if absolute_gap >= 50 and gap_pct >= 10:
            flagged.append({
                "case_id": row["case_id"],
                "absolute_distance_gap_m": round(absolute_gap, 3),
                "relative_distance_gap_pct": round(gap_pct, 2),
                "review_classification": "HIGH_GAP_VERIFY_TURN_AND_MAP_TRUTH",
            })
        elif absolute_gap >= 15 and gap_pct >= 2:
            secondary += 1
    flagged.sort(key=lambda r: (-r["absolute_distance_gap_m"], r["case_id"]))
    return {
        "high_gap_case_count": len(flagged),
        "secondary_gap_case_count": secondary,
        "review_cases_in_priority_order": flagged,
        "independently_verified_navigation_failures": 0,
        "ranking_supported": False,
        "review_next": ("Check matching incoming/exit directed road, mapped turn "
                        "prohibitions, access, source data completeness and "
                        "dated official road evidence before changing DMN."),
    }


def validate_osrm_case_results(cases: Sequence[dict], rows: Sequence[dict],
                               *, snapshot: str) -> dict:
    """Require exactly one strictly unverified local reference outcome per case."""
    if not isinstance(snapshot, str) or not snapshot:
        raise ValueError("Missing pinned source snapshot")
    if not isinstance(cases, (tuple, list)) or not isinstance(rows, (tuple, list)):
        raise ValueError("Expected bounded comparison records")
    if not 1 <= len(cases) <= 240 or len(rows) != len(cases):
        raise AssertionError("Missing or excessive same-case OSRM executions")
    expected = [c["case_id"] for c in cases]
    found = [r.get("case_id") for r in rows]
    if found != expected or len(set(found)) != len(found):
        raise AssertionError("OSRM did not execute each pinned map case exactly once")
    for case, row in zip(cases, rows):
        if (case.get("map_snapshot") != snapshot or
                row.get("same_map_snapshot") != snapshot or
                row.get("status") not in RESULT_STATUSES or
                row.get("independent_current_uk_road_legality") != "UNKNOWN" or
                row.get("driver_navigation_quality_comparable") is not False or
                row.get("reference_engine") != "OSRM MLD 5.27.1 pinned car.lua" or
                row.get("dmn_fastest_mapped_distance_m") != case.get("fastest_length_m") or
                row.get("dmn_fastest_mapped_seconds") != case.get("fastest_estimated_seconds")):
            raise AssertionError("Comparator mismatch, unsupported status or false legality claim")
        if row["status"] in ("ENDPOINTS_NEAR_DIFFERENT_PROFILES",
                             "SNAP_MISMATCH_NOT_COMPARABLE"):
            for key in ("osrm_distance_m", "osrm_estimated_seconds",
                        "origin_snap_m", "destination_snap_m"):
                _metres(row.get(key), key)
            near = max(row["origin_snap_m"], row["destination_snap_m"]) <= SNAP_MAX_METRES
            if near != (row["status"] == "ENDPOINTS_NEAR_DIFFERENT_PROFILES"):
                raise AssertionError("False snapped-endpoint classification")
        elif any(k in row for k in ("osrm_distance_m", "osrm_estimated_seconds")):
            raise AssertionError("Unroutable OSRM response cannot assert route metrics")
    statuses = Counter(row["status"] for row in rows)
    return {
        "classification": "same-public-map-endpoint-observations-not-ranked",
        "source_snapshot": snapshot,
        "reference_engine": "OSRM MLD 5.27.1 pinned car.lua",
        "same_source_era": True,
        "case_count": len(cases),
        "case_results": list(rows),
        "status_counts": dict(sorted(statuses.items())),
        "osrm_routes_with_both_endpoint_snaps_within_15m": statuses[
            "ENDPOINTS_NEAR_DIFFERENT_PROFILES"],
        "cases_attempted": len(rows),
        "complete_same_case_execution": True,
        "independent_legality_established": False,
        "travel_time_truth_established": False,
        "route_quality_ranking_valid": False,
        "distance_discrepancy_review": distance_discrepancy_triage(rows),
        "profile_equivalence_established": False,
        "physical_approach_or_departure_edge_equivalence_established": False,
        "note": ("DMN and OSRM used identical OSM snapshot era and actual map-point "
                 "endpoints. Endpoint snap checks do not prove identical directed "
                 "approaches; OSRM uses different motorcar access/cost/turn models. "
                 "No UK legality, live traffic or route quality winner is inferred."),
    }
