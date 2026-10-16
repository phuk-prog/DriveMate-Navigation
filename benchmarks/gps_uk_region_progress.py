"""Three real-UK-OSM regions: directed progress checks, not surveyed GNSS."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from benchmarks.itinero_public_probe import EXPECTED_ARCHIVE_HASH
from benchmarks.public_temporal_gps import _point,_bearing
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher
from map_data import Provenance,import_osm_xml

ROOT=Path(__file__).resolve().parents[1]
AREAS=("salford","stockport","oldham")

def sample_pairs(graph,limit=12):
    pairs=[]
    for e in sorted(graph.edges.values(),key=lambda e:e.edge_id):
        if e.access!="allowed" or e.length_m<20:continue
        for f in graph.adjacency[e.target]:
            if (f.access=="allowed" and f.length_m>=15 and
                    (e.edge_id,f.edge_id) not in graph.prohibited_turns):
                pairs.append((e,f))
    chosen=[]
    used=set()
    for same in (True,False):
        for e,f in pairs:
            a,b=e.edge_id.split(":"),f.edge_id.split(":")
            if not (len(a)==len(b)==4 and a[0]==b[0]=="w"
                    and a[1].isdigit() and b[1].isdigit()):
                continue
            if (a[1]==b[1])!=same or a[1] in used:continue
            if same and a[3]!=b[3]:continue
            chosen.append((e,f))
            used.add(a[1])
            if len(chosen)==limit:return chosen
    return chosen

def run_pair(graph,xy,a,b):
    first=GPSFix(1000,*_point(xy[a.source],xy[a.target],.70),
                 3,10,_bearing(xy[a.source],xy[a.target]))
    second=GPSFix(9000,*_point(xy[b.source],xy[b.target],.20),
                  3,10,_bearing(xy[b.source],xy[b.target]))
    result={}
    for mode in ("default","research"):
        temporal=TemporalRoadMatcher(DirectedRoadMatcher(graph,xy,
            experimental_adjacent_fragment_equivalence=(mode=="research")))
        anchor=temporal.update(first)
        state=temporal.update(second)
        outcome=("CORRECT" if state.status=="MATCHED" and state.edge_id==b.edge_id
                 else "CONFIDENT_WRONG" if state.status=="MATCHED" else "WITHHELD")
        result[mode]={"outcome":outcome,"status":state.status,
                      "edge":state.edge_id,"reason":state.reason,
                      "initial_status":anchor.status}
    return result

def analyse(name,raw):
    data=import_osm_xml(raw,provenance=Provenance(
        "UK GPS real-map regional comparison","Geofabrik260901-"+name,
        "historical public OSM","OpenStreetMap contributors; ODbL"))
    graph,xy=data.graph,data.coordinates
    pairs=sample_pairs(graph)
    if len(pairs)<8:raise ValueError(name+" fewer than 8 distinct public OSM roads")
    rows=[]
    for i,(a,b) in enumerate(pairs,1):
        both=run_pair(graph,xy,a,b)
        rows.append({"id":name.upper()+f"-{i:02d}",
            "incoming":a.edge_id,"expected":b.edge_id,
            "same_way":a.edge_id.split(":")[1]==b.edge_id.split(":")[1],**both})
    totals={mode:dict(Counter(row[mode]["outcome"] for row in rows))
            for mode in ("default","research")}
    # Safety guards use actual OSM directed segments sampled in reverse;
    # only anchored samples count as executed.
    reverse=[]
    seen=set()
    for e in sorted(graph.edges.values(),key=lambda x:x.edge_id):
        bits=e.edge_id.split(":")
        if (e.access!="allowed" or e.length_m<45 or len(bits)!=4
                or bits[0]!="w" or bits[1] in seen):continue
        a,b=xy[e.source],xy[e.target]
        heading=_bearing(a,b)
        f=GPSFix(1000,*_point(a,b,.80),3,10,heading)
        s=GPSFix(9000,*_point(a,b,.20),3,10,heading)
        state={}
        for mode in ("default","research"):
            t=TemporalRoadMatcher(DirectedRoadMatcher(graph,xy,
                experimental_adjacent_fragment_equivalence=(mode=="research")))
            anchored=t.update(f)
            after=t.update(s)
            state[mode]={"anchor":anchored.status,"status":after.status,"edge":after.edge_id}
        if any(state[m]["anchor"]!="MATCHED" for m in state):continue
        reverse.append({"edge":e.edge_id,**state,
            "research_confident_same_edge_reverse":(
                state["research"]["status"]=="MATCHED"
                and state["research"]["edge"]==e.edge_id)})
        seen.add(bits[1])
        if len(reverse)>=6:break
    danger=totals["research"].get("CONFIDENT_WRONG",0)+sum(
        r["research_confident_same_edge_reverse"] for r in reverse)
    return {"region":name,"map_sha256":sha256(raw).hexdigest(),
            "case_count":len(rows),"distinct_incoming_ways":len(rows),
            "cases":rows,"summary":totals,
            "reverse_trajectory_checks":reverse,"safety_failure_count":danger,
            "independent_road_truth":False,"actual_phone_gnss":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive-hash",type=Path,required=True)
    p.add_argument("--maps",nargs=3,type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    root=(ROOT/"results").resolve()
    if any(not f.resolve().is_relative_to(root) for f in a.maps+[a.output]):
        raise ValueError("Use only ignored results paths")
    if json.loads(a.archive_hash.read_text())["archive_sha256"]!=EXPECTED_ARCHIVE_HASH:
        raise ValueError("Historical UK OSM archive differs")
    regions=[analyse(n,p.read_bytes()) for n,p in zip(AREAS,a.maps)]
    report={"test":"UK-REGION-GPS-PROGRESS-001",
            "pinned_archive_sha256":EXPECTED_ARCHIVE_HASH,
            "classification":"real UK OSM source geometry, provisional unsurveyed oracle",
            "regions":regions,"total_cases":sum(x["case_count"] for x in regions),
            "safety_failure_count":sum(x["safety_failure_count"] for x in regions),
            "default_engine_unchanged":True,"external_engines_executed":0}
    a.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"test":report["test"],"count":report["total_cases"],
        "regions":[{"name":x["region"],"cases":x["case_count"],
            "default":x["summary"]["default"],"research":x["summary"]["research"],
            "reverse_checks":len(x["reverse_trajectory_checks"]),
            "safety_failures":x["safety_failure_count"]} for x in regions],
        "independent_road_truth":False},indent=2),flush=True)
    if report["safety_failure_count"]:
        raise SystemExit("Unsafe: confidently wrong source-geometry or reverse-progress edge")

if __name__=="__main__":
    main()
