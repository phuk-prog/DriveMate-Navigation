"""MAP-001: fresh, local OSRM/GraphHopper isolated-way binary access references.

Route-API evidence is NOT native graph inspection or independent UK road law.
Only four frozen binary ways are compatible with these adapters. In particular,
neither API supports the per-way private/destination assertions in MAP-001.
Never equate a missing snapped segment or invalid response with legal denial.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
from time import perf_counter_ns
from urllib.error import HTTPError, URLError
from urllib.request import Request

from benchmarks.map001_graph_fact_audit import ROOT, digest
from benchmarks.map001_profile_trial import BINARY_WAYS, DIR, profiles
from benchmarks.osrm_live_reference import OPENER as OSRM_OPENER, local_route_url
from benchmarks.graphhopper_live_reference import _OPENER as GH_OPENER, route_url

VERSIONS = {"OSRM": "5.27.1", "GraphHopper": "11.1"}
OUTPUT = ROOT / "map001-additional-profiles"
MAX_REPLY = 200_000


def endpoint_ok(shape, start, end):
    """Require nonzero route shape and endpoints matching source-way vertices."""
    if not isinstance(shape, list) or len(shape) < 2:
        return False
    if any(not isinstance(q, (list, tuple)) or len(q) != 2 for q in shape):
        return False
    try:
        first, last = shape[0], shape[-1]
        if any(type(p) not in (int, float) for q in (first, last) for p in q):
            return False
        return (first != last and
                all(abs(p - q) <= 0.00003 for p, q in zip(first, (start[1], start[0]))) and
                all(abs(p - q) <= 0.00003 for p, q in zip(last, (end[1], end[0]))))
    except (TypeError, ValueError):
        return False


def classify(engine, status, response, start, end):
    """No-route is distinct from bad snapping, HTTP failure and malformed data."""
    if not isinstance(response, dict):
        return "NOT_JUDGED_SCHEMA"
    if engine == "OSRM":
        code = response.get("code")
        if code == "NoRoute":
            return "NO_ROUTE" if status == 200 else "NOT_JUDGED_HTTP"
        if code == "NoSegment":
            return "NOT_JUDGED_SNAPPING"
        if status != 200 or code != "Ok":
            return "NOT_JUDGED_HTTP_OR_SCHEMA"
        routes = response.get("routes")
        if not isinstance(routes, list) or len(routes) != 1:
            return "NOT_JUDGED_SCHEMA"
        path = routes[0]
        shape = path.get("geometry", {}) if isinstance(path, dict) else {}
        geometry = shape.get("coordinates") if isinstance(shape, dict) and shape.get("type") == "LineString" else None
        if not isinstance(path, dict) or not isinstance(path.get("distance"), (float, int)) or path["distance"] <= 0:
            return "NOT_JUDGED_SCHEMA"
        return "ROUTE" if endpoint_ok(geometry, start, end) else "NOT_JUDGED_ENDPOINT_CORRELATION"
    if engine == "GraphHopper":
        if status != 200:
            message = response.get("message", "")
            return "NO_ROUTE" if status == 400 and message == "Connection not found" else "NOT_JUDGED_HTTP_OR_SNAPPING"
        paths = response.get("paths")
        if not isinstance(paths, list) or len(paths) != 1:
            return "NOT_JUDGED_SCHEMA"
        path = paths[0]
        coords = path.get("points", {}) if isinstance(path, dict) else {}
        geometry = coords.get("coordinates") if isinstance(coords, dict) and coords.get("type") == "LineString" else None
        if not isinstance(path, dict) or not isinstance(path.get("distance"), (float, int)) or path["distance"] <= 0:
            return "NOT_JUDGED_SCHEMA"
        return "ROUTE" if endpoint_ok(geometry, start, end) else "NOT_JUDGED_ENDPOINT_CORRELATION"
    raise ValueError("Unsupported reference engine")


def request_reference(engine, start, end):
    if engine == "OSRM":
        url = local_route_url(start, end).replace("overview=false", "overview=full&geometries=geojson")
        opener = OSRM_OPENER
    elif engine == "GraphHopper":
        url = route_url(start, end).replace("calc_points=false", "calc_points=true")
        opener = GH_OPENER
    else:
        raise ValueError("Unsupported reference engine")
    # Local fixed-loopback request only, with public source-graph vertices.
    if not url.startswith("http://127.0.0.1:"):
        raise ValueError("Reference endpoint must be loopback")
    started = perf_counter_ns()
    try:
        with opener.open(Request(url), timeout=12) as r:
            status = r.status
            raw = r.read(MAX_REPLY + 1)
    except HTTPError as e:
        status = e.code
        raw = e.read(MAX_REPLY + 1)
    except (OSError, URLError) as e:
        raise RuntimeError("Reference engine failed to respond") from e
    elapsed = (perf_counter_ns() - started) / 1e6
    if len(raw) > MAX_REPLY:
        raise ValueError("Reference response too large")
    try:
        response = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError("Reference returned invalid JSON") from e
    return {"outcome": classify(engine, status, response, start, end),
            "http_status": status, "http_request_ms": round(elapsed, 5),
            "response_sha256": digest(raw)}


def probe(engine, way):
    if engine not in VERSIONS or way not in BINARY_WAYS:
        raise ValueError("Unapproved engine or frozen source way")
    manifest = json.loads((DIR / "manifest.json").read_text())
    spec = next(x for x in manifest["cases"] if x["way"] == way)
    raw = (DIR / (way + ".osm")).read_bytes()
    if digest(raw) != spec["input_sha256"]:
        raise ValueError("Frozen isolated-way bytes changed")
    # Endpoint positions must be taken from the exact same source used by DMN
    # and Valhalla (never from user GPS).
    import xml.etree.ElementTree as ET
    source = ET.fromstring(raw)
    nodes = {x.get("id"): (float(x.get("lat")), float(x.get("lon"))) for x in source.findall("node")}
    forward = (nodes[spec["from_node"].split(":")[1]], nodes[spec["to_node"].split(":")[1]])
    observations = {}
    cases = []
    for name, direction_forward, expected, equivalent in profiles(way, spec["source_access"]):
        if not equivalent or not name.startswith("ORDINARY_"):
            raise ValueError("Contextual profile mapped to binary route API")
        direction = "forward" if direction_forward else "reverse"
        a, b = forward if direction_forward else forward[::-1]
        observation = request_reference(engine, a, b)
        actual = observation["outcome"]
        verdict = ("NOT_JUDGED" if actual not in ("ROUTE", "NO_ROUTE") else
                   "PASS" if (actual == "ROUTE") == (expected == "allowed") else "FAIL")
        cases.append({"source_way": way, "profile": name, "direction": direction,
                      "expected_access": expected, "observed": actual, "verdict": verdict,
                      "reason": "SOURCE_PROFILE_AND_LOCAL_ROUTE_API_NOT_INDEPENDENT_ROAD_LAW",
                      "http_request_ms": observation["http_request_ms"],
                      "response_sha256": observation["response_sha256"],
                      "http_status": observation["http_status"]})
        observations[direction] = observation
    if len(cases) != 2:
        raise ValueError("Binary profile coverage incomplete")
    OUTPUT.mkdir(exist_ok=True, parents=True)
    record = {"trial": "MAP-001-PROFILE-EXTERNAL-1", "engine": engine,
              "version": VERSIONS[engine], "source_sha256": manifest["source_sha256"],
              "input_sha256": spec["input_sha256"], "source_way": way,
              "pbf_conversion": "OSMIUM_SORT_OF_UNCHANGED_ISOLATED_XML",
              "graph_facts_inspected": False, "engine_binary_or_config_modified": False,
              "road_legality": "NOT_INDEPENDENTLY_JUDGED",
              "cases": cases}
    (OUTPUT / (engine.lower() + "-" + way + ".json")).write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"engine": engine, "way": way, "verdicts": dict(Counter(c["verdict"] for c in cases))}), flush=True)


def score():
    manifest = json.loads((DIR / "manifest.json").read_text())
    valhalla = {}
    for way in BINARY_WAYS:
        spec = next(x for x in manifest["cases"] if x["way"] == way)
        record = json.loads((DIR / (way + ".json")).read_text())
        if record["source_sha256"] != manifest["source_sha256"] or record["same_engine_input_xml_sha256"] != spec["input_sha256"]:
            raise ValueError("Stale DMN/Valhalla profile evidence")
        valhalla[way] = {x["profile"]: x for x in record["cases"]}
    by_engine = {}
    for engine in VERSIONS:
        by_engine[engine] = {}
        for way in BINARY_WAYS:
            spec = next(x for x in manifest["cases"] if x["way"] == way)
            record = json.loads((OUTPUT / (engine.lower() + "-" + way + ".json")).read_text())
            if (record["engine"] != engine or record["version"] != VERSIONS[engine] or
                    record["source_way"] != way or record["source_sha256"] != manifest["source_sha256"] or
                    record["input_sha256"] != spec["input_sha256"]):
                raise ValueError("Mixed engine, version or frozen source")
            by_engine[engine][way] = {x["profile"]: x for x in record["cases"]}
            if set(by_engine[engine][way]) != {"ORDINARY_FORWARD", "ORDINARY_REVERSE"}:
                raise ValueError("Incomplete or duplicated external profile")
    rows = []
    for way in BINARY_WAYS:
        for name in ("ORDINARY_FORWARD", "ORDINARY_REVERSE"):
            v = valhalla[way][name]
            scores = {"DMN ★": v["dmn_policy_verdict"], "Valhalla 3.9.1": v["valhalla_verdict"]}
            for engine in VERSIONS:
                scores[engine + " " + VERSIONS[engine]] = by_engine[engine][way][name]["verdict"]
            rows.append({"source_way": way, "profile": name, "scores": scores,
                         "independent_road_law": False})
    engines = list(rows[0]["scores"])
    fully_common = [r for r in rows if all(v in ("PASS", "FAIL") for v in r["scores"].values())]
    rank = sorted([{"engine": e, "pass": sum(r["scores"][e] == "PASS" for r in fully_common),
                    "fail": sum(r["scores"][e] == "FAIL" for r in fully_common),
                    "total": len(fully_common)} for e in engines],
                  key=lambda x: (-x["pass"], x["fail"], x["engine"])) if fully_common else []
    report = {"trial": "MAP-001-PROFILE-EXTERNAL-1", "source_sha256": manifest["source_sha256"],
              "cases_total": len(rows), "binary_way_total": len(BINARY_WAYS),
              "engines_executed": engines, "common_complete_case_count": len(fully_common),
              "full_category_1_ranking": None, "provisional_binary_profile_partial_ranking": rank,
              "unjudged_or_failed_cases": [r for r in rows if any(v != "PASS" for v in r["scores"].values())],
              "cases": rows, "truth": "PROVISIONAL_OSM_SOURCE_NOT_UK_ROAD_LAW",
              "different_timing_boundaries_not_speed_comparable": True,
              "private_destination_context_profiles": "UNSUPPORTED_FOR_OSRM_AND_GRAPHHOPPER",
              "native_turn_legality": "NOT_INSPECTED_BY_THESE_ROUTE_API_ADAPTERS"}
    (OUTPUT / "scorecard.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("cases", "unjudged_or_failed_cases")}, indent=2), flush=True)
    if len(rows) != 8:
        raise ValueError("Frozen binary cohort incomplete")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("operation", choices=("probe", "score"))
    p.add_argument("--engine", choices=tuple(VERSIONS))
    p.add_argument("--way", choices=BINARY_WAYS)
    args = p.parse_args()
    if args.operation == "probe":
        if not args.engine or not args.way:
            p.error("probe requires --engine and --way")
        probe(args.engine, args.way)
    else:
        score()


if __name__ == "__main__":
    main()
