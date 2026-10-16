"""MAP-001 v3 experimental Valhalla /locate graph metadata adapter.

Valhalla is MIT licensed. This adapter tests only visibility of OSM way IDs in
locally imported graph candidates. It CANNOT verify complete directed topology,
turn prohibitions or lawfulness, and is NEVER given a Category 1 full-graph rank.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from benchmarks.map001_graph_fact_audit import ROOT, tags
from benchmarks.map001_v3 import FROZEN_V2_IDS, digest

LOCATE_URL = "http://127.0.0.1:8002/locate"


def way_midpoint(way, nodes):
    refs = [n.get("ref") for n in way.findall("nd")]
    if len(refs) < 2:
        raise ValueError("Way has fewer than two nodes")
    middle = max(0, (len(refs) - 2) // 2)
    a, b = nodes[refs[middle]], nodes[refs[middle + 1]]
    return {"lat": (float(a.get("lat")) + float(b.get("lat"))) / 2,
            "lon": (float(a.get("lon")) + float(b.get("lon"))) / 2,
            "minimum_reachability": 0, "radius": 45}


def extract_way_ids(result):
    """Never conflate an unavailable field with an incorrect graph."""
    if not isinstance(result, dict) or not isinstance(result.get("edges"), list):
        return None
    ids = set()
    for edge in result["edges"]:
        if not isinstance(edge, dict):
            continue
        info = edge.get("edge_info")
        value = edge.get("way_id")
        if value is None and isinstance(info, dict):
            value = info.get("way_id")
        if value is not None and str(value).isdigit():
            ids.add(str(value))
    return ids


def interpret(ids, result):
    found = extract_way_ids(result)
    if found is None:
        return "SCHEMA_UNAVAILABLE"
    return "WAY_VISIBLE" if str(ids) in found else "UNRESOLVED_CORRELATION"


def probe():
    raw = (ROOT / "map001-manchester.osm").read_bytes()
    manifest = json.loads((ROOT / "map001-v3-manifest.json").read_text())
    manchester = next(x for x in manifest["areas"] if x["area"] == "manchester")
    if digest(raw) != manchester["source_sha256"]:
        raise ValueError("Valhalla input map differs from frozen v3 map")
    root = ET.fromstring(raw)
    ways = {w.get("id"): w for w in root.findall("way")}
    nodes = {n.get("id"): n for n in root.findall("node")}
    eligible = [wid for wid in FROZEN_V2_IDS["manchester"]
                if wid in ways and len(ways[wid].findall("nd")) >= 2]
    locations = [way_midpoint(ways[wid], nodes) for wid in eligible]
    body = json.dumps({"costing": "auto", "verbose": True,
                       "locations": locations}, separators=(",", ":")).encode()
    if len(body) > 10_000:
        raise ValueError("Valhalla request exceeds 10 KB")
    req = Request(LOCATE_URL, data=body, headers={"Content-Type": "application/json"},
                  method="POST")
    with urlopen(req, timeout=30) as response:
        raw_output = response.read(500_001)
    if len(raw_output) > 500_000:
        raise ValueError("Valhalla response exceeds 500KB")
    parsed = json.loads(raw_output)
    if not isinstance(parsed, list) or len(parsed) != len(eligible):
        raise ValueError("Valhalla /locate unexpected response contract")
    cases = [{"case_id": "manchester-" + wid, "verdict": interpret(wid, item),
              "visible_way_count": len(extract_way_ids(item) or ())}
             for wid, item in zip(eligible, parsed)]
    counts = Counter(item["verdict"] for item in cases)
    report = {"engine": "Valhalla 3.9.1", "api": "local /locate verbose",
              "data_license": "OpenStreetMap contributors, ODbL",
              "engine_license": "MIT", "map_sha256": digest(raw),
              "scope": "OSM_WAY_ID_GRAPH_CANDIDATE_VISIBILITY_ONLY",
              "full_category1_rank": None, "complete_turn_graph_inspection": False,
              "cases": cases, "counts": dict(counts)}
    (ROOT / "map001-v3-valhalla-locate.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(json.dumps({"engine": report["engine"], "counts": report["counts"]}))
    if not counts["WAY_VISIBLE"]:
        raise SystemExit("Valhalla OSM-way metadata contract not verified")


if __name__ == "__main__":
    probe()
