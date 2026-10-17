"""ROUTE-003 shared real-map route-output and calculation-time baseline.

The road snapshot and three synthetic endpoint pairs are frozen independently of
all engines.  OpenStreetMap tags are source-map evidence, not current road law.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from math import isfinite
import os
from pathlib import Path
from statistics import median
from time import perf_counter_ns
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request

from benchmarks.itinero_public_probe import EXPECTED_ARCHIVE_HASH, EXPECTED_XML_HASH
from benchmarks.routing_legality_batch import classify_response, wait_reference
from benchmarks.routing_references import OPENER, route_request
from engine import RouteNotFound, shortest_route
from map_data import Provenance, import_osm_xml
from map_data.osm_xml import _haversine

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = {
    "DMN": "repository shortest_route",
    "OSRM": "5.27.1; car.lua; MLD",
    "Valhalla": "3.9.1; auto",
    "GraphHopper": "11.1; car; CH",
    "openrouteservice": "10.1.0; driving-car; fastest",
    "BRouter": "1.7.10; car-vario",
    "Itinero": "source b8a004a; car; uncontracted",
    "Routino": "3.4.1; motorcar; quickest",
}


def load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text())
    if manifest.get("expected_xml_sha256") != EXPECTED_XML_HASH:
        raise ValueError("Wrong frozen map snapshot")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != 3:
        raise ValueError("ROUTE-003 requires all three frozen endpoint pairs")
    if len({c.get("id") for c in cases}) != 3:
        raise ValueError("Duplicate or missing case ID")
    return manifest


def geometry_length(points: list[list[float]]) -> float:
    return sum(_haversine(a, b) for a, b in zip(points, points[1:]))


def numeric(value):
    """Accept finite numeric provider fields, including BRouter JSON strings."""
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if isfinite(result) else None


def judge(case: dict, result: dict, calculation_ms: float) -> dict:
    base = {"case_id": case["id"], "calculation_ms": calculation_ms}
    if result.get("status") != "ROUTE":
        return {**base, "outcome": "UNRESOLVED", "reason": result.get("reason", "No complete route")}
    points = result.get("points")
    if (not isinstance(points, list) or not 2 <= len(points) <= 20000 or
            any(not isinstance(p, (list, tuple)) or len(p) != 2 or
                any(type(v) not in (int, float) or not isfinite(v) for v in p)
                for p in points)):
        return {**base, "outcome": "FAIL", "reason": "Malformed route geometry"}
    start_error = _haversine(case["start"], points[0])
    end_error = _haversine(case["end"], points[-1])
    length_m = numeric(result.get("distance_m", geometry_length(points)))
    duration_s = numeric(result.get("duration_s"))
    checks = {
        "complete_geometry": len(points) >= 2,
        "start_within_5m": start_error <= 5,
        "end_within_5m": end_error <= 5,
        "positive_finite_distance": length_m is not None and length_m > 0,
        "positive_finite_duration": duration_s is not None and duration_s > 0,
    }
    return {
        **base,
        "outcome": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failures": [name for name, passed in checks.items() if not passed],
        "start_error_m": round(start_error, 6),
        "end_error_m": round(end_error, 6),
        "distance_m": round(length_m, 3) if length_m is not None else None,
        "duration_s": round(duration_s, 3) if duration_s is not None else None,
        "returned_vertices": len(points),
        "mapped_legality": "UNRESOLVED",
    }


def _external_metrics(system: str, data: dict) -> tuple[float | None, float | None]:
    if system == "OSRM":
        route = data.get("routes", [{}])[0]
        return route.get("distance"), route.get("duration")
    if system == "Valhalla":
        summary = data.get("trip", {}).get("summary", {})
        return summary.get("length", 0) * 1000, summary.get("time")
    if system == "GraphHopper":
        route = data.get("paths", [{}])[0]
        return route.get("distance"), route.get("time", 0) / 1000
    if system == "openrouteservice":
        summary = data.get("features", [{}])[0].get("properties", {}).get("summary", {})
        return summary.get("distance"), summary.get("duration")
    if system == "BRouter":
        props = data.get("features", [{}])[0].get("properties", {})
        return props.get("track-length"), props.get("total-time")
    raise ValueError("No live HTTP metrics adapter")


def run_dmn(manifest: dict, map_path: Path) -> list[dict]:
    raw = map_path.read_bytes()
    if sha256(raw).hexdigest() != EXPECTED_XML_HASH:
        raise ValueError("Pinned XML mismatch")
    imported = import_osm_xml(raw, provenance=Provenance(
        "public Greater Manchester test bbox", "Geofabrik260901",
        "pinned Geofabrik Greater Manchester extract", "OpenStreetMap contributors; ODbL"))
    by_point = {tuple(value): key for key, value in imported.coordinates.items()}
    rows = []
    for case in manifest["cases"]:
        start = perf_counter_ns()
        try:
            route = shortest_route(imported.graph, by_point[tuple(case["start"])], by_point[tuple(case["end"])])
            points = [case["start"]] + [imported.coordinates[imported.graph.edges[e].target] for e in route.edge_ids]
            result = {"status": "ROUTE", "points": points, "distance_m": route.length_m,
                      "duration_s": route.estimated_seconds}
        except (KeyError, RouteNotFound) as exc:
            result = {"status": "UNRESOLVED", "reason": type(exc).__name__ + ": " + str(exc)}
        rows.append(judge(case, result, (perf_counter_ns() - start) / 1e6))
    return rows


def run_http(system: str, manifest: dict) -> list[dict]:
    wait_reference(system)
    rows = []
    for case in manifest["cases"]:
        if system == "BRouter":
            query = urlencode({"lonlats": "|".join(f"{p[1]},{p[0]}" for p in (case["start"], case["end"])),
                               "profile": "car-vario", "alternativeidx": 0, "format": "geojson"})
            request = Request("http://127.0.0.1:17777/brouter?" + query)
        else:
            request = route_request(system, case["start"], case["end"])
        begin = perf_counter_ns()
        try:
            with OPENER.open(request, timeout=30) as response:
                status, raw = response.status, response.read(2_000_001)
        except HTTPError as exc:
            status, raw = exc.code, exc.read(2_000_001)
        elapsed = (perf_counter_ns() - begin) / 1e6
        if len(raw) > 2_000_000:
            result = {"status": "UNRESOLVED", "reason": "Oversized response"}
        else:
            data = json.loads(raw)
            result = classify_response(system, status, raw)
            if result.get("status") == "ROUTE":
                result["distance_m"], result["duration_s"] = _external_metrics(system, data)
        rows.append(judge(case, result, elapsed))
    return rows


def report(system: str, manifest_path: Path, rows: list[dict]) -> dict:
    judged = [r for r in rows if r["outcome"] in ("PASS", "FAIL")]
    timings = [r["calculation_ms"] for r in rows]
    return {
        "test_id": "ROUTE-003", "system": system, "version": VERSIONS[system],
        "run_sha": os.environ.get("GITHUB_HEAD_SHA"),
        "classification": "real public map; synthetic endpoint pairs; route output and process/request timing",
        "map_xml_sha256": EXPECTED_XML_HASH,
        "manifest_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
        "execution": "actual_local_python" if system == "DMN" else "actual_loopback_engine",
        "cases": rows, "passed": sum(r["outcome"] == "PASS" for r in rows),
        "failed": sum(r["outcome"] == "FAIL" for r in rows),
        "unresolved": sum(r["outcome"] == "UNRESOLVED" for r in rows),
        "judged_cases": len(judged), "total_cases": len(rows),
        "median_calculation_ms": round(median(timings), 6),
        "calculation_scope": "in-process" if system == "DMN" else "warm loopback request including serialization",
        "independent_current_road_legality": "UNRESOLVED",
        "traffic": "NOT_TESTED_IN_ROUTE-003",
    }


def scorecard(reports: list[dict]) -> dict:
    supplied = {r["system"]: r for r in reports}
    if len(supplied) != len(reports):
        raise ValueError("Duplicate engine report")
    first = reports[0]
    for item in reports:
        if item["test_id"] != "ROUTE-003" or item["manifest_sha256"] != first["manifest_sha256"] or item["map_xml_sha256"] != first["map_xml_sha256"]:
            raise ValueError("Reports do not share the frozen cohort")
    rows = []
    for system in VERSIONS:
        item = supplied.get(system)
        complete = bool(item and item["judged_cases"] == item["total_cases"] == 3)
        score = round(10 * item["passed"] / 3, 3) if complete else None
        rows.append({"system": system, "rank": None, "score_out_of_ten": score,
                     "passed": item["passed"] if item else 0, "failed": item["failed"] if item else 0,
                     "unresolved": item["unresolved"] if item else 0, "not_run": 0 if item else 3,
                     "median_calculation_ms": item["median_calculation_ms"] if item else None,
                     "cases": item["cases"] if item else []})
    rows.sort(key=lambda r: (r["score_out_of_ten"] is None, -(r["score_out_of_ten"] or 0), r["system"]))
    previous = None
    for index, row in enumerate((r for r in rows if r["score_out_of_ten"] is not None), 1):
        if row["score_out_of_ten"] != previous:
            rank = index
        row["rank"] = rank
        previous = row["score_out_of_ten"]
    return {"test_id": "ROUTE-003",
            "formula": "10 * passed / 3 frozen route-output cases; incomplete cohorts unranked; time reported separately",
            "timing_warning": "DMN in-process and external warm loopback timings have different boundaries and are not a fair speed rank",
            "legality_warning": "OSM source agreement is not independent current road-law proof",
            "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=["DMN", "OSRM", "Valhalla", "GraphHopper", "openrouteservice", "BRouter"])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--map", type=Path)
    parser.add_argument("--reports", nargs="*", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    if args.engine:
        rows = run_dmn(manifest, args.map) if args.engine == "DMN" else run_http(args.engine, manifest)
        result = report(args.engine, args.manifest, rows)
    else:
        result = scorecard([json.loads(path.read_text()) for path in args.reports or []])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
