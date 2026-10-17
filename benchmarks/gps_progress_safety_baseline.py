"""GPS-004 frozen analytical baseline for adjacent-fragment progress safety.

The cases are invented controls. They test software invariants, not UK road,
GNSS, lane or legal truth. Both DMN variants run independently; the default
remains authoritative and the experimental matcher remains research-only.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from engine import RoadEdge, RoadGraph
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/"benchmarks/fixtures/synthetic-gps-004.json"
COORDS={"a":(0.0,0.0),"b":(0.0,.0002),"c":(.000015,.00047),
        "d":(.00030,.00047),"p":(.00005,.00018),"q":(.00005,.00047),
        "x":(0.0,0.0),"y":(0.0,.0010)}

def _edge(eid,a,b,length=30.0):
    return RoadEdge(eid,a,b,length,30.0,"allowed")

def _point(a,b,f):
    return (a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f)

def _scenario(name):
    forward=[_edge("w:1:0:f","a","b",22.24),_edge("w:1:1:f","b","c",30.1)]
    start=GPSFix(1000,*_point(COORDS["a"],COORDS["b"],.30),3,10,90)
    if name=="forward_adjacent":
        return forward,(),[start,GPSFix(4000,*_point(COORDS["b"],COORDS["c"],.20),3,10,87)]
    if name=="remain":
        return forward,(),[start,GPSFix(4000,*_point(COORDS["a"],COORDS["b"],.85),3,10,90)]
    if name=="reverse_same_edge":
        edges=[_edge("w:9:0:f","x","y",111.2)]
        return edges,(),[GPSFix(1000,*_point(COORDS["x"],COORDS["y"],.70),3,10,90),
                          GPSFix(8000,*_point(COORDS["x"],COORDS["y"],.20),3,10,90)]
    if name=="prohibited":
        return forward,(("w:1:0:f","w:1:1:f"),),[start,GPSFix(4000,*_point(COORDS["b"],COORDS["c"],.20),3,10,87)]
    if name=="parallel":
        edges=forward+[_edge("w:2:0:f","p","q",32.0)]
        return edges,(),[start,GPSFix(4000,*_point(COORDS["b"],COORDS["c"],.20),5,10,87)]
    if name=="stationary":
        return forward,(),[start,GPSFix(4000,*_point(COORDS["b"],COORDS["c"],.05),3,0,None)]
    if name=="heading_missing":
        return forward,(),[start,GPSFix(4000,*_point(COORDS["b"],COORDS["c"],.20),3,10,None)]
    if name=="weak_accuracy":
        return forward,(),[start,GPSFix(4000,*_point(COORDS["b"],COORDS["c"],.20),40,10,87)]
    if name=="reverse_directed":
        edges=[_edge("w:1:1:r","c","b",30.1),_edge("w:1:0:r","b","a",22.24)]
        return edges,(),[GPSFix(1000,*_point(COORDS["c"],COORDS["b"],.30),3,10,267),
                          GPSFix(4000,*_point(COORDS["b"],COORDS["a"],.30),3,10,270)]
    if name=="sharp_bend":
        edges=[_edge("w:3:0:f","a","b",22.24),_edge("w:3:1:f","b","d",33.4)]
        return edges,(),[start,GPSFix(4000,*COORDS["b"],3,10,45)]
    raise ValueError("Unknown scenario")

def _run(edges,turns,fixes,opt_in):
    graph=RoadGraph(COORDS,edges,turns)
    matcher=TemporalRoadMatcher(DirectedRoadMatcher(
        graph,COORDS,experimental_adjacent_fragment_equivalence=opt_in))
    events=[]
    for fix in fixes:
        result=matcher.update(fix)
        events.append({"status":result.status,"edge_id":result.edge_id,
                       "reason":result.reason,"candidate_count":result.candidate_count})
    return events

def _judge(case,default,experimental):
    exp=case["expected"]
    checks=[]
    if "default" in exp: checks.append([x["status"] for x in default]==exp["default"])
    if "experimental" in exp: checks.append([x["status"] for x in experimental]==exp["experimental"])
    if "experimental_edge" in exp: checks.append(experimental[-1]["edge_id"]==exp["experimental_edge"])
    if "forbidden_edge" in exp:
        checks.extend(default[-1]["edge_id"]!=exp["forbidden_edge"] for _ in [0])
        checks.extend(experimental[-1]["edge_id"]!=exp["forbidden_edge"] for _ in [0])
    if "final_status" in exp:
        checks.extend([default[-1]["status"]==exp["final_status"],experimental[-1]["status"]==exp["final_status"]])
    if "final_edge" in exp:
        checks.extend([default[-1]["edge_id"]==exp["final_edge"],experimental[-1]["edge_id"]==exp["final_edge"]])
    if "experimental_final_status" in exp:
        checks.append(experimental[-1]["status"]==exp["experimental_final_status"])
    return bool(checks) and all(checks)

def execute():
    raw=FIXTURE.read_bytes(); fixture=json.loads(raw)
    cases=[]
    for case in fixture["cases"]:
        edges,turns,fixes=_scenario(case["scenario"])
        default=_run(edges,turns,fixes,False)
        experimental=_run(edges,turns,fixes,True)
        passed=_judge(case,default,experimental)
        cases.append({"case_id":case["id"],"outcome":"PASS" if passed else "FAIL",
                      "expected":case["expected"],"default":default,
                      "experimental":experimental})
    passed=sum(x["outcome"]=="PASS" for x in cases)
    return {"trial":"GPS-004","classification":fixture["classification"],
            "oracle_sha256":sha256(raw).hexdigest(),"engine_family":"DMN",
            "variants":{"default":"authoritative unchanged matcher",
                        "experimental":"isolated research-only adjacent-fragment matcher"},
            "external_engines_executed":0,
            "external_reason":"Available batch snapping/routing APIs do not expose equivalent stateful fix history and authoritative/shadow outputs",
            "passed":passed,"total":len(cases),"score_out_of_10":10*passed/len(cases),
            "cases":cases,"independent_real_world_truth":False}

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    report=execute();a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("trial","passed","total","score_out_of_10")},indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
