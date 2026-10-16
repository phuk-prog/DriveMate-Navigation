"""Combine six *fresh* native Valhalla graph inspections on frozen UK inputs.

No competitor inference from HTTP-only route results. Each region has its
own native graph and source SHA; unsupported/conditional ways are excluded
from the common scored denominator, never silently passed or failed.
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path

from benchmarks.map001_graph_fact_audit import ROOT, AREAS, digest
from benchmarks.map001_v3 import FROZEN_V2_IDS


def rank_rows(cases):
    common = [row for row in cases
              if row.get("equivalent_scored_cohort") is True
              and row.get("dmn_verdict") in ("PASS", "FAIL")
              and row.get("valhalla_verdict") in ("PASS", "FAIL")]
    ranks = [{"engine": engine, "pass": sum(r[key] == "PASS" for r in common),
              "fail": sum(r[key] == "FAIL" for r in common), "total": len(common)}
             for engine, key in (("DMN ★", "dmn_verdict"), ("Valhalla 3.9.1", "valhalla_verdict"))]
    return common, sorted(ranks, key=lambda x: (-x["pass"], x["fail"], x["engine"]))


def summarize():
    manifest=json.loads((ROOT/"map001-v3-manifest.json").read_text())
    if [x["area"] for x in manifest["areas"]] != list(AREAS):
        raise ValueError("The frozen six-region manifest has changed")
    allcases = []
    by_region = []
    for spec in manifest["areas"]:
        area = spec["area"]
        path = ROOT/("map001-native-comparison.json" if area == "manchester" else
                    "map001-native-"+area+"-comparison.json")
        if not path.is_file():
            raise ValueError("Missing fresh native engine report: " + area)
        row = json.loads(path.read_text())
        if row.get("area", "manchester") != area or row["source_sha256"] != spec["source_sha256"]:
            raise ValueError("Mixed region or source hash: " + area)
        if row["engine_versions"]["Valhalla"] != "3.9.1":
            raise ValueError("Wrong native reference version: " + area)
        if not isinstance(row.get("native_output_sha256"), str) or len(row["native_output_sha256"]) != 64:
            raise ValueError("No real native graph evidence digest")
        if len(row["cases"]) != 20 or len(FROZEN_V2_IDS[area]) != 20:
            raise ValueError("Incomplete frozen regional native selection")
        if [x["source_way"] for x in row["cases"]] != FROZEN_V2_IDS[area]:
            raise ValueError("Missing/reordered source way IDs: " + area)
        if row["common_binary_way_cohort"] != sum(x["equivalent_scored_cohort"] for x in row["cases"]):
            raise ValueError("Incorrect regional denominator")
        common, partial = rank_rows(row["cases"])
        by_region.append({"area": area, "source_sha256": spec["source_sha256"],
                          "native_output_sha256": row["native_output_sha256"],
                          "native_edges": row["native_enumeration"].get("directed_edges"),
                          "selected_ways": len(row["cases"]),
                          "comparable_ways": len(common),
                          "source_segments_compared": sum(x.get("expected_checks", 0) for x in common),
                          "partial_ranking": partial,
                          "valhalla_verdicts": dict(Counter(x["valhalla_verdict"] for x in row["cases"]))})
        allcases.extend({**x,"area":area} for x in row["cases"])
    common, rank = rank_rows(allcases)
    if len(allcases) != 120:
        raise ValueError("Not all 120 original UK ways inspected")
    report = {"trial": "MAP-001-NATIVE-SIX-REGION-1",
              "contract": "FROZEN_SOURCE_DIRECTED_CAR_ACCESS_ONLY",
              "evidence": "PROVISIONAL_OSM_SOURCE_NOT_INDEPENDENT_UK_LEGALITY",
              "full_category_1_multi_engine_ranking": None,
              "native_graph_engines_compared": ["DMN ★", "Valhalla 3.9.1"],
              "route_only_engines_not_native_graph_scored": ["OSRM 5.27.1", "GraphHopper 11.1"],
              "total_original_source_ways": len(allcases),
              "partial_common_native_ways": len(common),
              "partial_native_access_ranking": rank,
              "regional_results": by_region,
              "total_comparable_segment_checks": sum(x.get("expected_checks", 0) for x in common),
              "not_judged_native_cases": [{ "area": r["area"], "source_way": r["source_way"],
                                           "reason": r.get("reason", r.get("valhalla_verdict"))}
                                          for r in allcases if r not in common],
              "failed_common_native_cases": [{
                  "area": r["area"], "source_way": r["source_way"],
                  "dmn": r["dmn_verdict"], "valhalla": r["valhalla_verdict"],
                  "wrong_access": r.get("wrong_access", []),
                  "extra_car_allowed_directions": r.get("extra_car_allowed_directions", [])}
                  for r in common if r["dmn_verdict"] == "FAIL" or r["valhalla_verdict"] == "FAIL"],
              "speed_ranking": None, "independent_road_law": False,
              "source_snapshot_atomic": False,
              "native_turn_legality": "UNSUPPORTED_AUTOCOST_CONTEXT_NOT_EVALUATED"}
    (ROOT/"map001-native-six-region-summary.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in (
       "trial","total_original_source_ways","partial_common_native_ways",
       "total_comparable_segment_checks","partial_native_access_ranking",
       "regional_results")},indent=2),flush=True)
    if report["failed_common_native_cases"]:
        raise SystemExit("Comparable native source-access fault: inspect artifact")


if __name__=="__main__":
    summarize()
