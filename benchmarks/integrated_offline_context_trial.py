"""INTEGRATED-003 offline package and active-route identity integration."""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
from time import perf_counter_ns

from benchmarks.integrated_journey_trial import scorecard
from benchmarks.offline_integrity_trial import inputs
from map_data.offline import OfflineMapStore, PackageValidationError

ROOT=Path(__file__).resolve().parents[1]
ORACLE=ROOT/"benchmarks/fixtures/synthetic-integrated-003.json"


def _label(info,maps):
    hashes={name:sha256(raw).hexdigest() for name,raw in maps.items()}
    return next(name for name,digest in hashes.items() if digest==info.sha256)


def _run(case, maps, variants):
    store=OfflineMapStore(); first=store.activate(*deepcopy(variants[case["activation_sequence"][0]]))
    old_route=store.route("osm:1","osm:3")
    second_status="ACTIVE"
    try:store.activate(*deepcopy(variants[case["activation_sequence"][1]]))
    except PackageValidationError:second_status="REJECTED"
    old_matches=old_route.package_sha256==store.info.sha256
    actual={"first_package_sha256":first.sha256,"active_package_sha256":store.info.sha256,
            "active_map":_label(store.info,maps),"second_activation":second_status,
            "old_route_matches_active":old_matches}
    checks={"active_map":actual["active_map"]==case["expected_active_map"],
            "old_route_context":old_matches==case.get("expected_old_route_matches_active",old_matches)}
    if "expected_second_activation" in case:
        checks["second_activation"]=second_status==case["expected_second_activation"]
    if "expected_new_route_matches_active" in case:
        new_route=store.route(case["source"],case["target"])
        new_matches=new_route.package_sha256==store.info.sha256
        actual.update(new_route_matches_active=new_matches,new_route_edges=list(new_route.route.edge_ids))
        checks["new_route_context"]=new_matches==case["expected_new_route_matches_active"]
    return actual,checks


def run_dmn():
    raw=ORACLE.read_bytes();contract=json.loads(raw);_,maps,variants=inputs();rows=[]
    for case in contract["cases"]:
        started=perf_counter_ns();actual,checks=_run(case,maps,variants)
        rows.append({"case_id":case["id"],"outcome":"PASS" if all(checks.values()) else "FAIL",
                     "checks":checks,"failures":[key for key,value in checks.items() if not value],
                     "actual":actual,"calculation_ms":(perf_counter_ns()-started)/1e6})
    return {"test_id":contract["test_id"],"system":"DMN","classification":contract["classification"],
            "run_sha":os.getenv("GITHUB_SHA"),"oracle_sha256":sha256(raw).hexdigest(),
            "map_sha256":{name:sha256(value).hexdigest() for name,value in maps.items()},
            "passed":sum(row["outcome"]=="PASS" for row in rows),
            "failed":sum(row["outcome"]=="FAIL" for row in rows),"total":len(rows),"cases":rows}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--scorecard",type=Path);args=parser.parse_args();result=run_dmn()
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    if args.scorecard:args.scorecard.write_text(json.dumps(scorecard(result),indent=2)+"\n")
    print(json.dumps(result,indent=2));return 1 if result["failed"] else 0


if __name__=="__main__":raise SystemExit(main())
