"""MAP-001 Category 1 frozen six-region closure: directional access + source relations.

An independently written source-tag oracle, NOT a second call to the DMN
importer's access helper. Agreement proves only archived OSM representation;
unknown access and legal permissions never become UK road-law PASS verdicts.
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from benchmarks.map001_graph_fact_audit import ROOT, AREAS, digest, isolated, source, tags
from benchmarks.map001_v3 import FROZEN_V2_IDS
from benchmarks.map001_v2 import related
from map_data import Provenance, OSMImportError, import_osm_xml

DRIVING = set("motorway trunk primary secondary tertiary unclassified residential living_street motorway_link trunk_link primary_link secondary_link tertiary_link service track".split())
UNCERTAIN = {"service", "track"}
ALLOW = {"yes", "designated", "permissive"}
DENY = {"no"}
CONTEXT = {"private", "agricultural", "forestry", "delivery", "destination", "customers", "permit"}
MODES = ("motorcar", "motor_vehicle", "vehicle", "access")
BLOCKED = {"bollard", "block", "cycle_barrier", "bus_trap"}
SOURCE_SHA_MANCHESTER = "34438baa7a28c55958cd5ba7ac3909a551c51197911963364d27a26eefe8973a"


def conditional(t):
    return any(k.endswith(":conditional") for k in t)


def mode_access(t, orientation):
    """Independent directional precedence (most specific vehicle mode first)."""
    direction = "forward" if orientation == "f" else "backward"
    for mode in MODES:
        for key in (mode + ":" + direction, mode):
            if key in t:
                value = t[key]
                return ("allowed" if value in ALLOW else
                        "prohibited" if value in DENY else "unknown")
    return "unknown" if t.get("highway") in UNCERTAIN else "allowed"


def barrier_access(t):
    kind = t.get("barrier")
    if not kind:
        return "allowed"
    for mode in MODES:
        if mode in t:
            value = t[mode]
            if value in DENY:
                return "prohibited"
            if value in ALLOW and kind not in BLOCKED:
                return "allowed"
            return "unknown"
    return "prohibited" if kind in BLOCKED else "unknown"


def combined(*states):
    return ("prohibited" if "prohibited" in states else
            "unknown" if "unknown" in states else "allowed")


def expected_way(way, nodes):
    """Return exact source segments without inspecting importer output."""
    tag = tags(way)
    ident = way.get("id")
    if tag.get("highway") not in DRIVING:
        return None, "not_driving_highway"
    refs = [n.get("ref") for n in way.findall("nd")]
    if len(refs) < 2 or any(r not in nodes for r in refs):
        return None, "incomplete_way_or_nodes"
    if conditional(tag) or any(conditional(tags(nodes[n])) for n in refs):
        return None, "conditional_source_requires_vehicle_time_policy"
    oneway = tag.get("oneway", "").lower()
    if not oneway and tag.get("junction") in {"roundabout", "circular"}:
        oneway = "yes"
    if oneway not in {"", "no", "0", "false", "yes", "1", "true", "-1", "reverse"}:
        return None, "unrecognized_oneway_value"
    dirs = ("r",) if oneway in {"-1", "reverse"} else (
        ("f",) if oneway in {"yes", "1", "true"} else ("f", "r"))
    rows = {}
    for i, (first, last) in enumerate(zip(refs, refs[1:])):
        if first == last:
            return None, "degenerate_way"
        physical = combined(barrier_access(tags(nodes[first])),
                            barrier_access(tags(nodes[last])))
        for d in dirs:
            start, end = ((first, last) if d == "f" else (last, first))
            rows[f"w:{ident}:{i}:{d}"] = (
                "osm:" + start, "osm:" + end,
                combined(mode_access(tag, d), physical))
    return rows, None


def compare_rows(expected, observed):
    """Symmetric comparison catches extra wrong-way edges AND lost car routes."""
    missing = sorted(set(expected) - set(observed))
    extra = sorted(set(observed) - set(expected))
    wrong = sorted(key for key in (set(expected) & set(observed))
                   if expected[key] != observed[key])
    return {"missing": missing, "extra": extra, "wrong": wrong,
            "verdict": "FAIL" if missing or extra or wrong else "MATCH"}


def relation_facts(rel, ways, nodes):
    """Evidence about applicability; not a legal restriction or route verdict."""
    t = tags(rel)
    mem = rel.findall("member")
    row = {"relation_id": rel.get("id"), "rule": t.get("restriction"),
           "verdict": "UNKNOWN"}
    if conditional(t):
        return {**row, "verdict": "WITHHELD_CONDITIONAL_RESTRICTION"}
    exceptions = {s.strip().lower() for s in t.get("except", "").replace(",", ";").split(";")}
    if "motorcar" in exceptions or "motor_vehicle" in exceptions:
        return {**row, "verdict": "EXCEPTED_MOTORCAR"}
    fr = [m.get("ref") for m in mem if m.get("type") == "way" and m.get("role") == "from"]
    to = [m.get("ref") for m in mem if m.get("type") == "way" and m.get("role") == "to"]
    via = [m.get("ref") for m in mem if m.get("type") == "node" and m.get("role") == "via"]
    if len(fr) != 1 or len(to) != 1 or len(via) != 1 or len(mem) != 3:
        return {**row, "verdict": "UNSUPPORTED_RELATION_SHAPE"}
    if fr[0] not in ways or to[0] not in ways or via[0] not in nodes:
        return {**row, "verdict": "INCOMPLETE_SOURCE_RELATION"}
    rule = t.get("restriction:motorcar", t.get("restriction:motor_vehicle", t.get("restriction", "")))
    if not (rule.startswith("no_") or rule.startswith("only_")):
        return {**row, "verdict": "UNKNOWN_RESTRICTION_RULE"}
    first, why_a = expected_way(ways[fr[0]], nodes)
    second, why_b = expected_way(ways[to[0]], nodes)
    if why_a or why_b:
        return {**row, "verdict": "WITHHELD_UNSUPPORTED_SOURCE_ACCESS",
                "source_reason": [why_a, why_b]}
    node = "osm:" + via[0]
    arrivals = [state for start, end, state in first.values() if end == node]
    departures = [state for start, end, state in second.values() if start == node]
    if "unknown" in arrivals + departures:
        verdict = "WITHHELD_UNQUALIFIED_MOTORCAR_ACCESS"
    elif not arrivals or not departures or "allowed" not in arrivals or "allowed" not in departures:
        verdict = "NO_MOTORCAR_SOURCE_MOVEMENT"
    else:
        verdict = "REPRESENTABLE_SOURCE_MOVEMENT"
    return {**row, "verdict": verdict, "arrival_states": dict(Counter(arrivals)),
            "departure_states": dict(Counter(departures)),
            "motorcar_road_law_verified": False}


def audit_way(area, wayid, ways, nodes, relations):
    result = {"case_id": area + "-" + wayid, "source_way": wayid,
              "legal_truth": "NOT_INDEPENDENTLY_VERIFIED"}
    if wayid not in ways:
        return {**result, "verdict": "NOT_JUDGED", "reason": "source_way_missing"}
    target = ways[wayid]
    expected, issue = expected_way(target, nodes)
    relations_used = related(wayid, relations)
    result["related_relations"] = [relation_facts(r, ways, nodes) for r in relations_used]
    if issue:
        verdict = "SAFE_WITHHELD" if "conditional" in issue else "NOT_JUDGED"
        return {**result, "verdict": verdict, "reason": issue}
    raw = isolated(target, nodes)
    try:
        loaded = import_osm_xml(raw, provenance=Provenance(
            area, "frozen v3 public OSM", "MAP-001 isolated source facts",
            "OpenStreetMap contributors; ODbL"))
    except OSMImportError as exc:
        return {**result, "verdict": "NOT_JUDGED",
                "reason": "isolated_import_rejected", "detail": str(exc)[:180]}
    observed = {k: (e.source, e.target, e.access) for k, e in loaded.graph.edges.items()}
    check = compare_rows(expected, observed)
    statuses = Counter(row[2] for row in expected.values())
    verdict = ("FAIL" if check["verdict"] == "FAIL" else
               "SAFE_WITHHELD" if statuses["unknown"] else "PASS")
    return {**result, "verdict": verdict,
            "source_edges_compared": len(expected), "source_access": dict(statuses),
            "source_encoding_matches": check["verdict"] == "MATCH",
            "reason": ("source_graph_mismatch" if verdict == "FAIL" else
                       "unknown_access_not_road_law" if verdict == "SAFE_WITHHELD"
                       else "frozen_osm_source_agreement"),
            "differences": {key: check[key][:12] for key in ("missing", "extra", "wrong")},
            "related_relation_count": len(relations_used)}


def execute():
    manifest = json.loads((ROOT / "map001-v3-manifest.json").read_text())
    areas = manifest.get("areas", [])
    if [part.get("area") for part in areas] != list(AREAS):
        raise ValueError("Frozen six-region manifest differs from approved cohort")
    if len(areas) != 6 or len(FROZEN_V2_IDS) != 6:
        raise ValueError("Incomplete UK cohort")
    report = {"trial": "MAP-001-CATEGORY-1-CLOSURE", "basis": "ARCHIVED_PUBLIC_OSM_NOT_INDEPENDENT_ROAD_LAW",
              "snapshot_atomic": False, "navigation_behavior_changed": False,
              "full_category_engine_ranking": None, "source_versions": [],
              "source_access_cases": [], "road_law_evidence": {
                  "independently_verified_way_count": 0,
                  "status": "NO_CASE_LEVEL_DATE_VALID_LEGAL_AND_GEOGRAPHIC_PROOF",
                  "official_location_level_reference": {
                      "authority": "Manchester City Council",
                      "location": "King Street westbound from Essex Street to Cross Street",
                      "restriction": "bus gate; ordinary cars excluded at all times",
                      "url": "https://www.manchester.gov.uk/parking/tickets-and-fines/bus-gates/the-king-street-bus-gate",
                      "source_way_correlation": "NOT_ESTABLISHED",
                      "road_law_case_verdict": "NOT_JUDGED"},
                  "uk_dtro": "https://www.gov.uk/guidance/digital-traffic-regulation-orders-d-tro-service"}}
    for area in areas:
        name = area["area"]
        raw, nodes, ways, _ = source(ROOT / ("map001-" + name + ".osm"))
        if digest(raw) != area["source_sha256"]:
            raise ValueError("Frozen source digest mismatch: " + name)
        if name == "manchester" and digest(raw) != SOURCE_SHA_MANCHESTER:
            raise ValueError("Known Manchester source contract changed")
        if [case["way"] for case in area["cases"]] != FROZEN_V2_IDS[name]:
            raise ValueError("Original v2 case order/IDs not preserved")
        report["source_versions"].append({"area": name, "sha256": digest(raw),
                                          "cases": len(area["cases"])})
        rels = ET.fromstring(raw).findall("relation")
        for wid in FROZEN_V2_IDS[name]:
            report["source_access_cases"].append(audit_way(name, wid, ways, nodes, rels))
    if len(report["source_access_cases"]) != 120:
        raise ValueError("Cohort not complete")
    verdicts = Counter(r["verdict"] for r in report["source_access_cases"])
    report["counts"] = dict(verdicts)
    report["related_relation_verdicts"] = dict(Counter(
        rel["verdict"] for row in report["source_access_cases"]
        for rel in row.get("related_relations", [])))
    report["source_segment_comparisons"] = sum(
        r.get("source_edges_compared", 0) for r in report["source_access_cases"])
    report["issues"] = [r for r in report["source_access_cases"] if r["verdict"] != "PASS"]
    report["all_120_cases_accounted_for"] = True
    report["independent_legality_pass"] = 0
    report["notes"] = ("Source-fact access cases are isolated from attached relations. "
        "Related source-relation applicability is diagnostic only, not a graded "
        "turn or complete graph legality check. Unknown access cannot be reclassified as a legal prohibition.")
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "map001-category1-closure.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"trial": report["trial"], "case_total": 120,
                      "counts": report["counts"], "segments": report["source_segment_comparisons"],
                      "relation_diagnostics": report["related_relation_verdicts"],
                      "legal_way_verdicts": 0}, indent=2), flush=True)
    if verdicts["FAIL"]:
        raise SystemExit("Frozen OSM source mismatch; inspect case-level evidence")


if __name__ == "__main__":
    execute()
