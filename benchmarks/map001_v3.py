"""MAP-001 v3: preserve 120 v2 way IDs, close public OSM restriction members,
and audit *both* missing and unexpected prohibited turn pairs.

No DMN production changes. All verdicts remain PROVISIONAL OSM-source agreement.
Newly fetched API objects are NOT a simultaneous/atomic OSM snapshot. Raw bounded
v3 inputs must be preserved with their checksums for identical-input retests.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from benchmarks.map001_graph_fact_audit import ROOT, AREAS, digest, source, tags
from benchmarks.map001_v2 import (audit as audit_v2, context, related,
                                  restriction_expectation)
from map_data import Provenance, OSMImportError, import_osm_xml

# Exact v2 selection by OSM way ID, not a newly cherry-picked easier selection.
FROZEN_V2_IDS = {
"manchester": "4816177 4816180 4816237 4857542 553071025 553071026 553071028 4721486 8777654 27255314 35277147 115559329 154986397 155729945 170158004 170162581 246124643 353938183 548694371 550963219",
"birmingham": "4823751 10059527 10059528 10063222 17504696 17504705 25087889 28291003 55231374 9933276 10479594 228842276 245134692 461175483 481181225 1046773618 1432227441 1432227442 1534025320 1534025328",
"carlisle": "4260309 4260310 4785012 23467606 1134518514 1134519028 1134519029 37801101 70576436 27585152 32790413 34954986 37801478 39034917 70576300 171260645 223351639 229878702 1101726808 1134344461",
"cardiff": "26434425 26434464 26435284 26435286 179051246 809372377 975305336 95026911 95026913 43217606 179051244 319307696 778981940 813498947 818617073 1424373244 35590850 43211138 115185781 116979076",
"glasgow": "4397805 4483892 4483893 4494909 77663259 23706734 23706735 4627827 143769308 4497320 4627829 4787502 4787503 45074531 114324471 745391452 827453788 1307008896 4542288 4764294",
"belfast": "17364284 133261496 133261846 133261851 109730356 117071355 8301321 144822061 133261491 133261493 133261847 182163873 1258575701 1469447056 148210368 148210371 148651261 148651263 267256593 267256594",
}
FROZEN_V2_IDS = {area: value.split() for area, value in FROZEN_V2_IDS.items()}
assert set(FROZEN_V2_IDS) == set(AREAS)
assert all(len(x) == len(set(x)) == 20 for x in FROZEN_V2_IDS.values())


def turn_differences(expected, observed):
    """Exact, symmetric check: an extra prohibition can itself block a legal turn."""
    return sorted(expected - observed), sorted(observed - expected)


def audit_v3(area, case, ways, nodes, relations):
    row = audit_v2(area, case, ways, nodes, relations)
    if row["verdict"] != "PASS":
        return row
    xml, issue = context(case["way"], ways, nodes, relations)
    if issue:
        return {**row, "verdict": "NOT_JUDGED", "type": "TEST_DATA", "reason": issue}
    subset = {way.get("id"): way for way in ET.fromstring(xml).findall("way")}
    expected, issue = restriction_expectation(related(case["way"], relations), subset, nodes)
    if issue:
        return {**row, "verdict": "NOT_JUDGED", "type": "TEST_OR_SOURCE", "reason": issue}
    try:
        imported = import_osm_xml(xml, provenance=Provenance(
            area, "MAP-001-v3-frozen-input", "OSM-source-closure",
            "OpenStreetMap contributors; ODbL"))
    except OSMImportError as exc:
        return {**row, "verdict": "NOT_JUDGED", "type": "DMN_OR_TEST",
                "reason": "import_rejected_on_recheck", "detail": str(exc)[:160]}
    missing, extra = turn_differences(expected, imported.graph.prohibited_turns)
    if missing or extra:
        return {**row, "verdict": "FAIL", "type": "DMN",
                "reason": ",".join(k for k, values in
                     (("missing_prohibited_turn", missing), ("extra_prohibited_turn", extra))
                     if values),
                "missing_turn_pairs": missing[:10], "extra_turn_pairs": extra[:10],
                "missing_count": len(missing), "extra_count": len(extra)}
    return {**row, "checked_both_turn_directions": True}


def relation_missing_ways(root, case_ids):
    ways = {w.get("id"): w for w in root.findall("way")}
    relations = root.findall("relation")
    required = set()
    for case_id in case_ids:
        if case_id not in ways:
            continue
        for relation in related(case_id, relations):
            required.update(m.get("ref") for m in relation.findall("member")
                            if m.get("type") == "way" and m.get("ref"))
    return sorted(required - ways.keys(), key=int)


def merge_way_full(root, requested_id, xml):
    """Accept only the requested full OSM way and its referenced nodes."""
    extra = ET.fromstring(xml)
    if extra.tag != "osm":
        raise ValueError("Unexpected OSM API reply")
    fetched = {w.get("id"): w for w in extra.findall("way")}
    if requested_id not in fetched:
        raise ValueError("Missing requested OSM way in full reply")
    present_nodes = {n.get("id") for n in root.findall("node")}
    present_ways = {w.get("id") for w in root.findall("way")}
    new_way = fetched[requested_id]
    needed = {n.get("ref") for n in new_way.findall("nd")}
    extra_nodes = {n.get("id"): n for n in extra.findall("node")}
    if not needed.issubset(present_nodes | extra_nodes.keys()):
        raise ValueError("Referenced node absent from OSM way/full reply")
    for node_id in sorted(needed - present_nodes, key=int):
        root.append(deepcopy(extra_nodes[node_id]))
    if requested_id not in present_ways:
        root.append(deepcopy(new_way))


def close_area(area, *, fetch, maximum_extras=40):
    path = ROOT / ("map001-" + area + ".osm")
    raw = path.read_bytes()
    if len(raw) > 6_000_000:
        raise ValueError("OSM source exceeds prototype limit")
    root = ET.fromstring(raw)
    original_sha = digest(raw)
    attempts = []
    for way_id in relation_missing_ways(root, FROZEN_V2_IDS[area]):
        if len(attempts) >= maximum_extras:
            raise ValueError("Exceeded permitted missing-member closure budget")
        try:
            xml = fetch(way_id)
            if len(xml) > 2_000_000:
                raise ValueError("OSM way/full response exceeds 2 MB")
            merge_way_full(root, way_id, xml)
            attempts.append({"way": way_id, "status": "RESOLVED",
                             "reply_sha256": digest(xml)})
        except (OSError, ValueError, ET.ParseError) as exc:
            attempts.append({"way": way_id, "status": "UNRESOLVED",
                             "reason": str(exc)[:140]})
    completed = ET.tostring(root, encoding="utf-8")
    if len(completed) > 6_000_000:
        raise ValueError("Closed area exceeds DMN 6 MB source limit")
    path.write_bytes(completed)
    return {"area": area, "base_sha256": original_sha, "closed_sha256": digest(completed),
            "closure": attempts, "snapshot_atomic": False}


def public_way_full(way_id):
    if not way_id.isdigit():
        raise ValueError("Invalid OSM way id")
    url = "https://api.openstreetmap.org/api/0.6/way/" + way_id + "/full"
    with urlopen(Request(url, headers={"User-Agent": "DMN-MAP001-research/3.0"}),
                 timeout=18) as response:
        return response.read(2_000_001)


def case_kind(way):
    if way is None:
        return "missing_source_way"
    t = tags(way)
    if any(k.endswith(":conditional") for k in t):
        return "conditional"
    if t.get("oneway") in ("yes", "1", "true", "-1", "reverse"):
        return "oneway"
    if t.get("junction") in ("roundabout", "circular"):
        return "roundabout"
    if "motorcar" in t or "access" in t:
        return "access"
    if t.get("highway", "").endswith("_link"):
        return "link"
    if t.get("highway") in ("service", "track"):
        return "service"
    return "ordinary"


def freeze():
    manifest = {"trial": "MAP-001-V3", "evidence_level": "PROVISIONAL_OSM_SOURCE",
                "snapshot_atomic": False, "selected_v2_way_ids_retained": True,
                "upstream_v2_snapshots_retrieved": False, "areas": []}
    for area in AREAS:
        raw, nodes, ways, linked = source(ROOT / ("map001-" + area + ".osm"))
        manifest["areas"].append({
            "area": area, "source_sha256": digest(raw),
            "cases": [{"way": wid, "kind": case_kind(ways.get(wid))}
                      for wid in FROZEN_V2_IDS[area]]
        })
    (ROOT / "map001-v3-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def score():
    manifest = json.loads((ROOT / "map001-v3-manifest.json").read_text())
    if [x["area"] for x in manifest["areas"]] != list(AREAS):
        raise ValueError("Area list mismatch")
    rows = []
    for part in manifest["areas"]:
        area = part["area"]
        raw, nodes, ways, linked = source(ROOT / ("map001-" + area + ".osm"))
        if digest(raw) != part["source_sha256"]:
            raise ValueError("Frozen v3 source bytes changed")
        if [x["way"] for x in part["cases"]] != FROZEN_V2_IDS[area]:
            raise ValueError("Frozen v2 selection changed")
        rels = ET.fromstring(raw).findall("relation")
        for case in part["cases"]:
            if case["way"] not in ways:
                rows.append({"case_id": area + "-" + case["way"], "verdict": "NOT_JUDGED",
                             "type": "TEST_DATA", "reason": "selected_way_absent_in_v3_snapshot"})
                continue
            rows.append(audit_v3(area, case, ways, nodes, rels))
    tally = Counter(x["verdict"] for x in rows)
    report = {"trial": "MAP-001-V3", "source_truth": "PROVISIONAL_OSM_NOT_ROAD_LAW",
              "same_source_bytes_as_v2": False, "cases": rows,
              "counts": dict(tally), "case_total": len(rows), "competitor_full_graph_rank": None,
              "issues": [x for x in rows if x["verdict"] != "PASS"],
              "dmn_navigation_code_changed": False}
    (ROOT / "map001-v3-scorecard.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"trial": report["trial"], "counts": report["counts"],
                      "case_total": report["case_total"], "issue_count": len(report["issues"])},
                     indent=2), flush=True)
    if tally["FAIL"]:
        raise SystemExit("MAP-001 v3 confirmed source mismatch; see artifact")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("close", "freeze", "score"))
    args = parser.parse_args()
    if args.operation == "close":
        rows = [close_area(area, fetch=public_way_full) for area in AREAS]
        (ROOT / "map001-v3-closure.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(json.dumps({"closed": len(rows), "unresolved": sum(
            x["status"] != "RESOLVED" for row in rows for x in row["closure"])}))
    elif args.operation == "freeze":
        print(json.dumps({"frozen_area_count": len(freeze()["areas"])}))
    else:
        score()


if __name__ == "__main__":
    main()
