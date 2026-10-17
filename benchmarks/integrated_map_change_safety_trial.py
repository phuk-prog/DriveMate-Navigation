"""INTEGRATED-004 active-route behavior when the map package changes."""
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
from engine.rerouting_controller import ReroutingController
from map_data.offline import OfflineMapStore, PackageValidationError

ROOT=Path(__file__).resolve().parents[1]
ORACLE=ROOT/"benchmarks/fixtures/synthetic-integrated-004.json"


def _run(case):
    _,maps,variants=inputs();store=OfflineMapStore();store.activate(*deepcopy(variants["A"]))
    offline_route=store.route("osm:1","osm:3")
    controller=ReroutingController();controller.begin(offline_route.route,now_ms=0)
    update_status="ACTIVE"
    try:store.activate(*deepcopy(variants[case["update_variant"]]))
    except PackageValidationError:update_status="REJECTED"
    if case["explicit_stop_after_update"]:controller.stop(now_ms=1)
    actual={"update_status":update_status,"controller_active":controller.active,
            "installed_route":controller.installed_route is not None,
            "route_package_sha256":offline_route.package_sha256,
            "active_package_sha256":store.info.sha256,
            "package_context_changed":offline_route.package_sha256!=store.info.sha256}
    checks={"controller_active":actual["controller_active"]==case["expected_controller_active"],
            "installed_route":actual["installed_route"]==case["expected_installed_route"]}
    if "expected_update_status" in case:
        checks["update_status"]=update_status==case["expected_update_status"]
    return actual,checks,{name:sha256(raw).hexdigest() for name,raw in maps.items()}


def run_dmn():
    raw=ORACLE.read_bytes();contract=json.loads(raw);rows=[];map_hashes=None
    for case in contract["cases"]:
        started=perf_counter_ns();actual,checks,map_hashes=_run(case)
        rows.append({"case_id":case["id"],"outcome":"PASS" if all(checks.values()) else "FAIL",
                     "checks":checks,"failures":[key for key,value in checks.items() if not value],
                     "actual":actual,"calculation_ms":(perf_counter_ns()-started)/1e6})
    return {"test_id":contract["test_id"],"system":"DMN","classification":contract["classification"],
            "run_sha":os.getenv("GITHUB_SHA"),"oracle_sha256":sha256(raw).hexdigest(),
            "map_sha256":map_hashes,"passed":sum(row["outcome"]=="PASS" for row in rows),
            "failed":sum(row["outcome"]=="FAIL" for row in rows),"total":len(rows),"cases":rows}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--scorecard",type=Path);args=parser.parse_args();result=run_dmn()
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    if args.scorecard:args.scorecard.write_text(json.dumps(scorecard(result),indent=2)+"\n")
    print(json.dumps(result,indent=2));return 1 if result["failed"] else 0


if __name__=="__main__":raise SystemExit(main())
