"""ROUTE-004 real-map one-way source-rule baseline.

Cases are selected deterministically from raw public OSM before any router runs.
OSM tags are not independent current road-law evidence.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from math import cos, hypot, isfinite, radians
import os
from pathlib import Path
from statistics import median
from time import perf_counter_ns
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request
import xml.etree.ElementTree as ET

from benchmarks.itinero_public_probe import EXPECTED_ARCHIVE_HASH
from benchmarks.real_map_route_baseline import VERSIONS, numeric
from benchmarks.routing_legality_batch import classify_response, wait_reference
from benchmarks.routing_references import OPENER, route_request
from engine import RouteNotFound, shortest_route
from map_data import Provenance, import_osm_xml
from map_data.osm_xml import _haversine

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 6
ROAD_CLASSES = {"motorway", "trunk", "primary", "secondary", "tertiary",
                "unclassified", "residential", "living_street", "motorway_link",
                "trunk_link", "primary_link", "secondary_link", "tertiary_link"}
EXECUTABLE = ("DMN", "OSRM", "Valhalla", "GraphHopper", "openrouteservice", "BRouter")


def _tags(element):
    return {tag.get("k"): tag.get("v") for tag in element.findall("tag")}


def prepare(raw: bytes, archive_sha256: str) -> dict:
    if archive_sha256 != EXPECTED_ARCHIVE_HASH:
        raise ValueError("Pinned source archive mismatch")
    root = ET.fromstring(raw)
    nodes = {node.get("id"): [float(node.get("lat")), float(node.get("lon"))]
             for node in root.findall("node")}
    cases = []
    for way in sorted(root.findall("way"), key=lambda item: int(item.get("id"))):
        tags = _tags(way)
        direction = tags.get("oneway", "").lower()
        implicit = not direction and tags.get("junction") in ("roundabout", "circular")
        if direction not in ("yes", "1", "true", "-1", "reverse") and not implicit:
            continue
        if tags.get("highway") not in ROAD_CLASSES or any("conditional" in key for key in tags):
            continue
        if any(tags.get(key) not in (None, "yes", "designated", "permissive")
               for key in ("access", "vehicle", "motor_vehicle", "motorcar")):
            continue
        refs = [nd.get("ref") for nd in way.findall("nd")]
        segments = list(enumerate(zip(refs, refs[1:])))
        if direction in ("-1", "reverse"):
            segments = [(index, (b, a)) for index, (a, b) in segments]
        selected = next(((index, a, b) for index, (a, b) in segments
                         if a in nodes and b in nodes and 20 <= _haversine(nodes[a], nodes[b]) <= 300), None)
        if selected is None:
            continue
        index, source, target = selected
        cases.append({"id": f"ROUTE-004-{len(cases)+1:03d}", "way_id": way.get("id"),
                      "segment": index, "road_class": tags.get("highway"), "name": tags.get("name"),
                      "oneway_tag": tags.get("oneway"), "junction": tags.get("junction"),
                      "allowed_start": nodes[source], "allowed_end": nodes[target]})
        if len(cases) == LIMIT:
            break
    return {"test_id": "ROUTE-004", "classification": "real public OSM one-way source-rule; synthetic exact-node endpoints",
            "archive_sha256": archive_sha256, "map_xml_sha256": sha256(raw).hexdigest(),
            "selection": "first six eligible ways numerically; first 20m..300m complete segment; before engine execution",
            "required_cases": LIMIT, "selection_complete": len(cases) == LIMIT,
            "independent_current_road_law": "UNRESOLVED", "cases": cases}


def _xy(point, origin):
    return ((point[1] - origin[1]) * 111195 * cos(radians(origin[0])),
            (point[0] - origin[0]) * 111195)


def forbidden_direct_traversal(points, allowed_start, allowed_end):
    """Detect a returned segment travelling directly along the mapped reverse edge."""
    a = _xy(allowed_start, allowed_start); b = _xy(allowed_end, allowed_start)
    dx, dy = b[0] - a[0], b[1] - a[1]; length2 = dx * dx + dy * dy
    if length2 <= 0:
        raise ValueError("Degenerate frozen segment")
    def projection(point):
        x, y = _xy(point, allowed_start)
        t = ((x-a[0])*dx + (y-a[1])*dy) / length2
        nearest = (a[0] + max(0, min(1, t))*dx, a[1] + max(0, min(1, t))*dy)
        return t, hypot(x-nearest[0], y-nearest[1])
    for first, second in zip(points, points[1:]):
        t1, d1 = projection(first); t2, d2 = projection(second)
        midpoint = [(first[0]+second[0])/2, (first[1]+second[1])/2]
        _, dm = projection(midpoint)
        if d1 <= 8 and d2 <= 8 and dm <= 8 and t1 >= .8 and t2 <= .2:
            return True
    return False


def judge(case, direction, result, calculation_ms):
    row = {"case_id": case["id"] + "-" + direction, "calculation_ms": calculation_ms}
    if result.get("status") == "NO_ROUTE":
        if direction == "reverse":
            return {**row, "outcome": "PASS", "checks": {"safe_no_route": True,
                    "forbidden_direction_absent": True}, "distance_m": None, "duration_s": None}
        return {**row, "outcome": "FAIL", "reason": "Required allowed-direction route unavailable"}
    if result.get("status") != "ROUTE":
        return {**row, "outcome": "UNRESOLVED", "reason": result.get("reason", "No complete output")}
    points = result.get("points")
    if not isinstance(points, list) or not 2 <= len(points) <= 20000:
        return {**row, "outcome": "FAIL", "reason": "Malformed geometry"}
    expected_start, expected_end = ((case["allowed_start"], case["allowed_end"])
                                    if direction == "allowed" else
                                    (case["allowed_end"], case["allowed_start"]))
    reverse_used = direction == "reverse" and forbidden_direct_traversal(
        points, case["allowed_start"], case["allowed_end"])
    distance = numeric(result.get("distance_m"))
    duration = numeric(result.get("duration_s"))
    checks = {"start_within_8m": _haversine(expected_start, points[0]) <= 8,
              "end_within_8m": _haversine(expected_end, points[-1]) <= 8,
              "positive_distance": distance is not None and distance > 0,
              "positive_duration": duration is not None and duration > 0,
              "forbidden_direction_absent": not reverse_used}
    return {**row, "outcome": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
            "failures": [key for key, value in checks.items() if not value],
            "distance_m": distance, "duration_s": duration, "returned_vertices": len(points),
            "independent_current_road_law": "UNRESOLVED"}


def _http_metrics(system, data):
    if system == "OSRM": route=data["routes"][0]; return route.get("distance"),route.get("duration")
    if system == "Valhalla": s=data["trip"]["summary"]; return s.get("length",0)*1000,s.get("time")
    if system == "GraphHopper": p=data["paths"][0]; return p.get("distance"),numeric(p.get("time"))/1000
    if system == "openrouteservice": s=data["features"][0]["properties"]["summary"]; return s.get("distance"),s.get("duration")
    if system == "BRouter": p=data["features"][0].get("properties",{}); return p.get("track-length"),p.get("total-time")
    raise ValueError("Unknown external engine")


def execute(system, manifest, map_path=None):
    imported = None
    if system == "DMN":
        raw=map_path.read_bytes()
        if sha256(raw).hexdigest()!=manifest["map_xml_sha256"]: raise ValueError("Map changed after freeze")
        imported=import_osm_xml(raw,provenance=Provenance("public Manchester legality bbox","Geofabrik260901","pinned public OSM","OpenStreetMap contributors; ODbL"))
        by_point={tuple(value):key for key,value in imported.coordinates.items()}
    else: wait_reference(system)
    rows=[]
    for case in manifest["cases"]:
        for direction in ("allowed","reverse"):
            start,end=((case["allowed_start"],case["allowed_end"]) if direction=="allowed" else
                       (case["allowed_end"],case["allowed_start"]))
            begin=perf_counter_ns()
            if system=="DMN":
                try:
                    route=shortest_route(imported.graph,by_point[tuple(start)],by_point[tuple(end)])
                    points=[start]+[imported.coordinates[imported.graph.edges[e].target] for e in route.edge_ids]
                    result={"status":"ROUTE","points":points,"distance_m":route.length_m,"duration_s":route.estimated_seconds}
                except RouteNotFound: result={"status":"NO_ROUTE"}
            else:
                if system=="BRouter":
                    q=urlencode({"lonlats":f"{start[1]},{start[0]}|{end[1]},{end[0]}","profile":"car-vario","alternativeidx":0,"format":"geojson"})
                    request=Request("http://127.0.0.1:17777/brouter?"+q)
                else: request=route_request(system,start,end)
                try:
                    with OPENER.open(request,timeout=30) as response: status,raw=response.status,response.read(2_000_001)
                except HTTPError as exc: status,raw=exc.code,exc.read(2_000_001)
                data=json.loads(raw); result=classify_response(system,status,raw)
                if result.get("status")=="ROUTE": result["distance_m"],result["duration_s"]=_http_metrics(system,data)
            rows.append(judge(case,direction,result,(perf_counter_ns()-begin)/1e6))
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument("--prepare",action="store_true");p.add_argument("--engine",choices=EXECUTABLE)
    p.add_argument("--map",type=Path,required=True);p.add_argument("--archive-hash");p.add_argument("--manifest",type=Path,required=True);p.add_argument("--output",type=Path)
    a=p.parse_args();raw=a.map.read_bytes()
    if a.prepare:
        result=prepare(raw,a.archive_hash);a.manifest.write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps(result,indent=2));
        if not result["selection_complete"]:raise SystemExit("Incomplete frozen one-way inventory")
        return
    manifest=json.loads(a.manifest.read_text())
    if manifest!=prepare(raw,manifest["archive_sha256"]):raise ValueError("Frozen manifest changed")
    rows=execute(a.engine,manifest,a.map)
    timings=[r["calculation_ms"] for r in rows]
    result={"test_id":"ROUTE-004","system":a.engine,"version":VERSIONS[a.engine],"run_sha":os.environ.get("GITHUB_HEAD_SHA"),
            "map_xml_sha256":manifest["map_xml_sha256"],"manifest_sha256":sha256(a.manifest.read_bytes()).hexdigest(),
            "cases":rows,"passed":sum(r["outcome"]=="PASS" for r in rows),"failed":sum(r["outcome"]=="FAIL" for r in rows),
            "unresolved":sum(r["outcome"]=="UNRESOLVED" for r in rows),"total":len(rows),
            "median_calculation_ms":round(median(timings),6),"independent_current_road_law":"UNRESOLVED"}
    a.output.write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result,indent=2))

if __name__=="__main__":main()
