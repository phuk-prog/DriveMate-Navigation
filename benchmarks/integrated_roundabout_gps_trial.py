"""INTEGRATED-002 roundabout and uncertain-GPS component integration."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from time import perf_counter_ns

from benchmarks.integrated_journey_trial import scorecard
from benchmarks.junction_trial import MAP, load_map
from engine import shortest_route
from engine.arrival_controller import ArrivalController
from engine.instruction_cues import instruction_phase
from engine.maneuvers import principal_maneuvers
from gps.fix_quality import GPSFix, assess_fix

ROOT=Path(__file__).resolve().parents[1]
ORACLE=ROOT/"benchmarks/fixtures/synthetic-integrated-002.json"


def _route_context():
    data,ring=load_map();route=shortest_route(data.graph,"osm:10","osm:18")
    return data,ring,route


def _roundabout(case):
    data,ring,route=_route_context()
    maneuvers=principal_maneuvers(data.graph,data.coordinates,route.edge_ids,ring)
    fix=GPSFix(1000,*data.coordinates["osm:10"],3,10,90)
    assessment=assess_fix(fix,now_ms=1000)
    phase=instruction_phase(distance_m=case["instruction_distance_m"],
        speed_mps=case["instruction_speed_mps"],lead_seconds=case["instruction_lead_seconds"],
        reliable_fix=assessment.status=="VALID",on_correct_route=True,
        maneuver_verified=maneuvers==case["expected_maneuvers"],observation_age_ms=0)
    actual={"route_edges":list(route.edge_ids),"maneuvers":maneuvers,
            "fix_status":assessment.status,"instruction_phase":phase}
    checks={"route":actual["route_edges"]==case["expected_route_edges"],
            "maneuvers":maneuvers==case["expected_maneuvers"],
            "fix":assessment.status==case["expected_fix_status"],
            "instruction":phase==case["expected_instruction_phase"]}
    return actual,checks


def _weak(case):
    data,_,route=_route_context();destination=data.coordinates["osm:18"]
    fix=GPSFix(1000,*destination,case["horizontal_accuracy_m"],0,90)
    assessment=assess_fix(fix,now_ms=1000)
    phase=instruction_phase(distance_m=5,speed_mps=0,
        reliable_fix=assessment.status=="VALID",on_correct_route=True,
        maneuver_verified=True,observation_age_ms=0)
    arrival=ArrivalController();token=arrival.begin(destination,route_length_m=route.length_m,now_ms=0)
    state=arrival.observe(context_revision=token,timestamp_ms=1000,now_ms=1000,
        position=destination,accuracy_m=case["horizontal_accuracy_m"],
        reliable=assessment.status=="VALID",on_route=True,remaining_m=0)
    actual={"fix_status":assessment.status,"fix_reason":assessment.reason,
            "instruction_phase":phase,"arrival_state":state}
    checks={"fix":assessment.status==case["expected_fix_status"],
            "instruction":phase==case["expected_instruction_phase"],
            "arrival":state==case["expected_arrival_state"]}
    return actual,checks


def _stale(case):
    data,_,route=_route_context();destination=data.coordinates["osm:18"]
    fix=GPSFix(case["fix_timestamp_ms"],*destination,3,0,90)
    assessment=assess_fix(fix,now_ms=case["receipt_timestamp_ms"])
    age=case["receipt_timestamp_ms"]-case["fix_timestamp_ms"]
    phase=instruction_phase(distance_m=5,speed_mps=0,
        reliable_fix=assessment.status=="VALID",on_correct_route=True,
        maneuver_verified=True,observation_age_ms=age)
    arrival=ArrivalController();token=arrival.begin(destination,route_length_m=route.length_m,now_ms=0)
    state=arrival.observe(context_revision=token,timestamp_ms=case["fix_timestamp_ms"],
        now_ms=case["receipt_timestamp_ms"],position=destination,accuracy_m=3,
        reliable=assessment.status=="VALID",on_route=True,remaining_m=0)
    actual={"fix_status":assessment.status,"fix_reason":assessment.reason,
            "instruction_phase":phase,"arrival_state":state}
    checks={"fix":assessment.status==case["expected_fix_status"],
            "reason":assessment.reason==case["expected_fix_reason"],
            "instruction":phase==case["expected_instruction_phase"],
            "arrival":state==case["expected_arrival_state"]}
    return actual,checks


def run_dmn():
    raw=ORACLE.read_bytes();contract=json.loads(raw);rows=[]
    runners={"INTEGRATED-002-roundabout-exit-three":_roundabout,
             "INTEGRATED-002-weak-gps-withholds":_weak,
             "INTEGRATED-002-stale-gps-rejected":_stale}
    for case in contract["cases"]:
        started=perf_counter_ns();actual,checks=runners[case["id"]](case)
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
