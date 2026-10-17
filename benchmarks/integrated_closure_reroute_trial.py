"""INTEGRATED-005 closure-evidence gating and legal route search."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from time import perf_counter_ns

from benchmarks.integrated_journey_trial import scorecard
from benchmarks.rerouting_lifecycle_trial import MAP
from engine import RouteNotFound, shortest_route
from engine.traffic_evidence import traffic_decision
from map_data import Provenance, import_osm_xml

ROOT=Path(__file__).resolve().parents[1]
ORACLE=ROOT/"benchmarks/fixtures/synthetic-integrated-005.json"


def run_dmn():
    raw=ORACLE.read_bytes();contract=json.loads(raw)
    data=import_osm_xml(MAP.read_bytes(),provenance=Provenance(
        "synthetic INTEGRATED-005","synthetic-v1","analytical closure fixture",
        "Synthetic OSM format; no OpenStreetMap contributor road data used"))
    rows=[]
    for case in contract["cases"]:
        started=perf_counter_ns()
        decision=traffic_decision(age_seconds=case["age_seconds"],speed_factor=1,
            closure_state=case["closure_state"],verified_closure=case["verified_closure"],
            legal_detour_available=case["legal_detour_available"])
        route_status="NOT_REQUESTED";route_edges=None
        if decision["propose_reroute"] or case.get("expected_route")=="NO_ROUTE":
            try:
                route=shortest_route(data.graph,"osm:4","osm:3",blocked_edges=case["blocked_edges"])
                route_status="ROUTE";route_edges=list(route.edge_ids)
            except RouteNotFound:route_status="NO_ROUTE"
        checks={"status":decision["status"]==case["expected_status"],
                "proposal":decision["propose_reroute"]==case["expected_propose_reroute"]}
        if "expected_route_edges" in case:checks["route"]=route_edges==case["expected_route_edges"]
        if "expected_route" in case:checks["route"]=route_status==case["expected_route"]
        if not case["expected_propose_reroute"] and "expected_route" not in case:
            checks["no_untrusted_route_search"]=route_status=="NOT_REQUESTED"
        actual={"traffic_decision":decision,"route_status":route_status,"route_edges":route_edges}
        rows.append({"case_id":case["id"],"outcome":"PASS" if all(checks.values()) else "FAIL",
                     "checks":checks,"failures":[key for key,value in checks.items() if not value],
                     "actual":actual,"calculation_ms":(perf_counter_ns()-started)/1e6})
    return {"test_id":contract["test_id"],"system":"DMN","classification":contract["classification"],
            "run_sha":os.getenv("GITHUB_SHA"),"oracle_sha256":sha256(raw).hexdigest(),
            "map_sha256":sha256(MAP.read_bytes()).hexdigest(),
            "passed":sum(row["outcome"]=="PASS" for row in rows),
            "failed":sum(row["outcome"]=="FAIL" for row in rows),"total":len(rows),"cases":rows}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--scorecard",type=Path);args=parser.parse_args();result=run_dmn()
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    if args.scorecard:args.scorecard.write_text(json.dumps(scorecard(result),indent=2)+"\n")
    print(json.dumps(result,indent=2));return 1 if result["failed"] else 0


if __name__=="__main__":raise SystemExit(main())
