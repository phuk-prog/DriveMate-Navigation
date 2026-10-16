"""Compare two DMN matcher variants on exactly the original frozen map cases.

Research only: no production navigation behaviour, no new GPS truth oracle,
and no external engines. Fail closed if default differs or new wrong-road
claims appear. Historical result files are NEVER overwritten.
"""
from hashlib import sha256
import argparse
import json
from pathlib import Path
from benchmarks.itinero_public_probe import EXPECTED_XML_HASH,EXPECTED_ARCHIVE_HASH
from benchmarks.real_map_gps_recovery import freeze,judge
from benchmarks.public_temporal_gps import _point,_bearing
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher
from map_data import Provenance,import_osm_xml

ROOT=Path(__file__).resolve().parents[1]
ORACLE="612f2469facbc4e02fd8233a78d3cb2aa9f1bb40a892efb88e9bf91d116b80b0"

def uk_pairs(graph):
    pool=[]
    for incoming in sorted(graph.edges.values(),key=lambda e:e.edge_id):
        if incoming.access!="allowed" or incoming.length_m<20:continue
        for outgoing in graph.adjacency[incoming.target]:
            if (outgoing.access=="allowed" and outgoing.length_m>=15 and
                (incoming.edge_id,outgoing.edge_id) not in graph.prohibited_turns):
                pool.append((incoming,outgoing))
    return pool[::max(1,len(pool)//40)][:40]

def evaluate(graph,coords,frozen,opt_in):
    base=DirectedRoadMatcher(graph,coords,
        experimental_adjacent_fragment_equivalence=opt_in)
    cases=[]
    counts=dict(correct=0,confident_wrong=0,withheld=0,rejected=0)
    for case in frozen["cases"]:
        temporal=TemporalRoadMatcher(base)
        events=[]
        for event in case["events"]:
            before=temporal.previous_valid_fix
            result=temporal.update(GPSFix(*event["fix"]),now_ms=event["now_ms"])
            actual=judge(event["expectation"],result.status,result.edge_id,
                case["expected_edge"],temporal.previous_valid_fix==before)
            if result.status=="MATCHED":
                counts["correct" if result.edge_id==case["expected_edge"] else "confident_wrong"]+=1
            else:counts["withheld"]+=1
            counts["rejected"]+=int(result.status=="REJECTED")
            events.append(dict(status=result.status,actual_edge=result.edge_id,
                reason=result.reason,passed=actual["passed"]))
        cases.append(dict(case_id=case["id"],
            outcome="PASS" if all(x["passed"] for x in events) else "FAIL",
            events=events))
    pool=uk_pairs(graph)
    if len(pool)!=40:raise ValueError("UK40 selection changed")
    uk=[]
    for i,(incoming,outgoing) in enumerate(pool,1):
        a,b=coords[incoming.source],coords[incoming.target]
        c,d=coords[outgoing.source],coords[outgoing.target]
        first=GPSFix(1000,*_point(a,b,.70),3.,10.,_bearing(a,b))
        second=GPSFix(9000,*_point(c,d,.20),3.,10.,_bearing(c,d))
        temporal=TemporalRoadMatcher(base)
        anchor=temporal.update(first)
        result=temporal.update(second)
        status=("CORRECT" if result.status=="MATCHED" and result.edge_id==outgoing.edge_id
                else "CONFIDENT_WRONG" if result.status=="MATCHED" else "WITHHELD")
        uk.append(dict(case_id=f"TGP-{i:03d}",status=status,
            expected_edge=outgoing.edge_id,actual_edge=result.edge_id,
            anchor_status=anchor.status,reason=result.reason))
    return dict(variant="opt_in_research" if opt_in else "unchanged_default",
        gps003=dict(pass_streams=sum(x["outcome"]=="PASS" for x in cases),
            total_streams=len(cases),counts=counts,cases=cases),
        uk40=dict(correct=sum(x["status"]=="CORRECT" for x in uk),
            confident_wrong=sum(x["status"]=="CONFIDENT_WRONG" for x in uk),
            withheld=sum(x["status"]=="WITHHELD" for x in uk),cases=uk))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--map",type=Path,required=True)
    parser.add_argument("--archive-hash",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result_dir=(ROOT/"results").resolve()
    if (not args.map.resolve().is_relative_to(result_dir) or
        not args.output.resolve().is_relative_to(result_dir)):
        raise ValueError("Require ignored results/ input and output")
    if json.loads(args.archive_hash.read_text())["archive_sha256"]!=EXPECTED_ARCHIVE_HASH:
        raise ValueError("Pinned archive hash mismatch")
    raw=args.map.read_bytes()
    if sha256(raw).hexdigest()!=EXPECTED_XML_HASH:
        raise ValueError("Pinned original XML hash mismatch")
    frozen=freeze(raw)
    if sha256((json.dumps(frozen,indent=2)+"\n").encode()).hexdigest()!=ORACLE:
        raise ValueError("Pinned case/oracle hash mismatch")
    old=json.loads((ROOT/"references/gps003-real-map-20261016.json").read_text())["report"]
    ukold=json.loads((ROOT/"references/gps001-uk-topology-20261015.json").read_text())["report"]
    if (old["oracle_sha256"]!=ORACLE or old["passed"]!=8 or old["total"]!=24 or
        (ukold["temporal_correct"],ukold["temporal_confident_wrong"],
         ukold["temporal_withheld"])!=(17,0,23)):
        raise ValueError("Frozen historical baselines differ")
    imported=import_osm_xml(raw,provenance=Provenance(
        "research variant, same pinned public Manchester map","Geofabrik260901",
        "public pinned historical archive","OpenStreetMap contributors; ODbL"))
    unchanged=evaluate(imported.graph,imported.coordinates,frozen,False)
    variant=evaluate(imported.graph,imported.coordinates,frozen,True)
    if ((unchanged["gps003"]["pass_streams"],unchanged["gps003"]["total_streams"],
         unchanged["gps003"]["counts"]["confident_wrong"])!=(8,24,0) or
        (unchanged["uk40"]["correct"],unchanged["uk40"]["confident_wrong"],
         unchanged["uk40"]["withheld"])!=(17,0,23)):
        raise ValueError("Default matcher no longer reproduces frozen evidence")
    new_wrong=(variant["gps003"]["counts"]["confident_wrong"]+
               variant["uk40"]["confident_wrong"])
    report=dict(trial="GPS003-RESEARCH-VARIANT-001",
        classification="same frozen map-derived GPS and UK40; no field road truth",
        map_sha256=EXPECTED_XML_HASH,oracle_sha256=ORACLE,
        historical_default_unmodified=True,default=unchanged,experimental=variant,
        new_confident_wrong=new_wrong,external_engines_executed=0,
        comparison_scope="DMN versions only; no cross-engine GPS rank",
        safety_gate_pass=new_wrong==0)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"trial":report["trial"],
        "default_gps":unchanged["gps003"]["pass_streams"],
        "variant_gps":variant["gps003"]["pass_streams"],
        "default_uk40":unchanged["uk40"]["correct"],
        "variant_uk40":variant["uk40"]["correct"],
        "new_confident_wrong":new_wrong,
        "default_unchanged":True,"output":str(args.output)},indent=2),flush=True)
    if new_wrong:
        raise SystemExit("Safety gate: opt-in variant made confident wrong-road claims")

if __name__=="__main__":
    main()
