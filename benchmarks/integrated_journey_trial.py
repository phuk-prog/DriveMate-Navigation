"""INTEGRATED-001 synthetic engine journey; no Android or real-road claim."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from time import perf_counter_ns

from benchmarks.route_adherence import check_route_line
from engine import RoadEdge, RoadGraph, shortest_route
from engine.arrival_controller import ArrivalController
from engine.instruction_cues import instruction_phase
from engine.rerouting_controller import ReroutingController
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "benchmarks/fixtures/synthetic-integrated-001.json"


def graph_data(prohibited=()):
    coordinates={"a":(53,-2),"b":(53,-1.9998),"c":(53,-1.9996),
                 "d":(53,-1.9994),"e":(53.0002,-1.9998),"f":(53.0002,-1.9996)}
    edges=[RoadEdge("w:1:0:f","a","b",14,30,"allowed"),
           RoadEdge("w:1:1:f","b","c",14,30,"allowed"),
           RoadEdge("w:1:2:f","c","d",14,30,"allowed"),
           RoadEdge("w:2:0:f","b","e",23,25,"allowed"),
           RoadEdge("w:2:1:f","e","f",14,25,"allowed"),
           RoadEdge("w:2:2:f","f","d",27,25,"allowed")]
    return RoadGraph(coordinates,edges,prohibited),coordinates


def graph_sha256():
    graph,coordinates=graph_data()
    value={"coordinates":coordinates,"edges":[vars(edge) for edge in graph.edges.values()]}
    return sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def _clean(case):
    graph,coords=graph_data(); route=shortest_route(graph,"a","d")
    path=[coords[x] for x in ("a","b","c","d")]
    adherence=check_route_line(graph,coords,route.edge_ids,path)["status"]
    match=DirectedRoadMatcher(graph,coords).match(GPSFix(1000,53,-1.9999,2,9,90)).status
    phase=instruction_phase(distance_m=60,speed_mps=14,reliable_fix=True,
        on_correct_route=True,maneuver_verified=True,observation_age_ms=150)
    arrival=ArrivalController(); token=arrival.begin(coords["d"],route_length_m=route.length_m,now_ms=0)
    states=[arrival.observe(context_revision=token,timestamp_ms=10000,now_ms=10000,
        position=coords["d"],accuracy_m=3,reliable=True,on_route=True,remaining_m=0),
        arrival.observe(context_revision=token,timestamp_ms=12000,now_ms=12000,
        position=coords["d"],accuracy_m=3,reliable=True,on_route=True,remaining_m=0)]
    actual={"route_edges":list(route.edge_ids),"route_line":adherence,
            "match_status":match,"instruction_phase":phase,"arrival_states":states}
    checks={"route":actual["route_edges"]==case["expected_route_edges"],
            "route_line":adherence=="PASS","match":match==case["expected_match_status"],
            "instruction":phase==case["expected_instruction_phase"],
            "arrival":states==case["expected_arrival_states"]}
    return actual,checks


def _reroute(case):
    graph,_=graph_data(); controller=ReroutingController()
    controller.begin(shortest_route(graph,"a","d"),now_ms=0)
    first=controller.observe(timestamp_ms=1000,now_ms=1000,reliable=True,on_route=False)
    second=controller.observe(timestamp_ms=3000,now_ms=3000,reliable=True,on_route=False)
    replacement=shortest_route(graph,"e","d")
    installed=controller.complete(second,replacement,now_ms=4000) if second else False
    actual={"first_request":first is not None,"second_request":second is not None,
            "replacement_edges":list(replacement.edge_ids),"replacement_installed":installed,
            "installed_edges":list(controller.installed_route.edge_ids)}
    checks={"first_request":actual["first_request"]==case["expected_first_request"],
            "second_request":actual["second_request"]==case["expected_second_request"],
            "replacement":actual["replacement_edges"]==case["expected_replacement_edges"],
            "installed":installed==case["expected_replacement_installed"],
            "installed_route":actual["installed_edges"]==case["expected_replacement_edges"]}
    return actual,checks


def _restriction(case):
    graph,_=graph_data([tuple(case["prohibited_turn"])])
    route=shortest_route(graph,"a","d")
    actual={"route_edges":list(route.edge_ids)}
    return actual,{"restricted_detour":actual["route_edges"]==case["expected_route_edges"]}


def run_dmn() -> dict:
    raw=ORACLE.read_bytes(); contract=json.loads(raw); rows=[]
    runners={"INTEGRATED-001-clean-arrival":_clean,
             "INTEGRATED-001-corroborated-reroute":_reroute,
             "INTEGRATED-001-turn-restriction-detour":_restriction}
    for case in contract["cases"]:
        started=perf_counter_ns(); actual,checks=runners[case["id"]](case)
        rows.append({"case_id":case["id"],"outcome":"PASS" if all(checks.values()) else "FAIL",
                     "checks":checks,"failures":[key for key,value in checks.items() if not value],
                     "actual":actual,"calculation_ms":(perf_counter_ns()-started)/1e6})
    return {"test_id":contract["test_id"],"system":"DMN",
            "classification":contract["classification"],"run_sha":os.getenv("GITHUB_SHA"),
            "oracle_sha256":sha256(raw).hexdigest(),"graph_definition_sha256":graph_sha256(),
            "passed":sum(row["outcome"]=="PASS" for row in rows),
            "failed":sum(row["outcome"]=="FAIL" for row in rows),"total":len(rows),"cases":rows}


def scorecard(dmn):
    roster=["DMN"]+[item["name"] for item in json.loads(
        (ROOT/"config/dmn-engine-first-programme.json").read_text())["reference_families"]]
    rows=[]
    for name in roster:
        if name=="DMN":
            complete=dmn["passed"]+dmn["failed"]==dmn["total"]
            rows.append({"system":name,"rank":1 if complete and not dmn["failed"] else None,
                         "score_out_of_ten":10*dmn["passed"]/dmn["total"] if complete else None,
                         "passed":dmn["passed"],"failed":dmn["failed"],"cases":dmn["cases"]})
            continue
        status="UNSUPPORTED" if name in {"OSRM","Valhalla","GraphHopper","openrouteservice","BRouter"} else "NOT_RUN"
        reason=("Current integrated static endpoint cannot express matcher, reroute-controller and arrival state"
                if status=="UNSUPPORTED" else "No permitted equivalent full lifecycle harness")
        rows.append({"system":name,"rank":None,"score_out_of_ten":None,"passed":0,"failed":0,
                     "cases":[{"case_id":case["case_id"],"outcome":status,"reason":reason}
                              for case in dmn["cases"]]})
    return {"test_id":"INTEGRATED-001","classification":"DMN-only synthetic lifecycle conformance; no competitive ranking",
            "formula":"10 * passed / 3 only for a complete judged cohort", "rows":rows}


def main() -> int:
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--scorecard",type=Path);args=parser.parse_args()
    result=run_dmn();args.output.write_text(json.dumps(result,indent=2)+"\n")
    if args.scorecard:args.scorecard.write_text(json.dumps(scorecard(result),indent=2)+"\n")
    print(json.dumps(result,indent=2));return 1 if result["failed"] else 0


if __name__=="__main__":raise SystemExit(main())
