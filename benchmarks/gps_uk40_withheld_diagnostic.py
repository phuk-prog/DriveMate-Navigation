"""Read-only exact geometry/temporal causes of 18 unresolved UK40 DMN matches.

Use the same pinned OSM snapshot, frozen case generator and BOTH existing GPS
variants. This is a diagnosis, not a real GPS measurement or navigation fix.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from benchmarks.gps003_research_variant import uk_pairs, evaluate, ORACLE
from benchmarks.itinero_public_probe import EXPECTED_ARCHIVE_HASH, EXPECTED_XML_HASH
from benchmarks.real_map_gps_recovery import freeze
from benchmarks.public_temporal_gps import _point, _bearing
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher, angular_difference
from gps.temporal_matcher import TemporalRoadMatcher
from map_data import Provenance, import_osm_xml

ROOT=Path(__file__).resolve().parents[1]
# Historical 18-case group was frozen before the directed-progress experiment.
PREVIOUS_18=frozenset(f'TGP-{n:03d}' for n in
    (1,2,4,5,7,9,10,11,12,13,14,15,16,18,19,21,25,40))

def require(ok,reason):
    if not ok:
        raise ValueError("Frozen UK40 diagnostic mismatch: "+reason)

def classify(anchor,expected,candidate_ids,reachable):
    if anchor is None:return "NO_TRUSTED_INITIAL_ANCHOR"
    if expected not in candidate_ids:return "GENERATING_FRAGMENT_NOT_IN_CANDIDATES"
    if not reachable:return "NO_TIME_REACHABLE_CANDIDATE"
    if expected not in reachable:return "GENERATING_FRAGMENT_NOT_TIME_REACHABLE"
    if len(reachable)>1:return "MULTIPLE_TIME_REACHABLE_CANDIDATES"
    return "UNRESOLVED_DESPITE_UNIQUE_REACHABLE_CANDIDATE"

def inspect(raw):
    frozen=freeze(raw)
    require(sha256((json.dumps(frozen,indent=2)+"\n").encode()).hexdigest()==ORACLE,
            "GPS-003 oracle changed")
    archive=json.loads((ROOT/"references/gps001-uk-topology-20261015.json").read_text())["report"]
    require(archive["source_sha256"]==EXPECTED_XML_HASH and
            (archive["temporal_correct"],archive["temporal_confident_wrong"],
             archive["temporal_withheld"])==(17,0,23),"old UK40 evidence changed")
    data=import_osm_xml(raw,provenance=Provenance("diagnostic-only pinned OSM",
            "Geofabrik260901","pinned extract","OpenStreetMap contributors; ODbL"))
    graph,coords=data.graph,data.coordinates
    pairs=uk_pairs(graph)
    require(len(pairs)==40,"UK40 deterministic selection")
    baseline=evaluate(graph,coords,frozen,False)["uk40"]
    shadow=evaluate(graph,coords,frozen,True)["uk40"]
    require((baseline["correct"],baseline["confident_wrong"],baseline["withheld"])==(17,0,23),
            "original variant verdicts")
    require(shadow["confident_wrong"]==0 and shadow["correct"]>=22
            and shadow["withheld"]<=18,"research variant regressed correctness or safety")
    old={x["case_id"]:x for x in baseline["cases"]}
    new={x["case_id"]:x for x in shadow["cases"]}
    retained=[]
    totals=Counter()
    for n,(incoming,outgoing) in enumerate(pairs,1):
        caseid=f"TGP-{n:03d}"
        if caseid not in PREVIOUS_18:continue
        first=GPSFix(1000,*_point(coords[incoming.source],coords[incoming.target],.70),
                     3.,10.,_bearing(coords[incoming.source],coords[incoming.target]))
        second=GPSFix(9000,*_point(coords[outgoing.source],coords[outgoing.target],.20),
                      3.,10.,_bearing(coords[outgoing.source],coords[outgoing.target]))
        matcher=DirectedRoadMatcher(graph,coords,
                        experimental_adjacent_fragment_equivalence=True)
        temporal=TemporalRoadMatcher(matcher)
        anchor_result=temporal.update(first)
        anchor=temporal.anchor_edge_id
        options=matcher._candidates(second)
        ids={c.edge_id for c in options}
        raw_result=matcher.match(second,previous_fix=temporal.previous_valid_fix,now_ms=9000)
        reachable=set()
        records=[]
        for c in options:
            edge=graph.edges[c.edge_id]
            connector=(temporal._connection_length(anchor,c.edge_id)
                       if anchor is not None else None)
            possible=(connector is not None and
                      temporal._transition_fits_time(anchor,c.edge_id,second,connector))
            if possible:reachable.add(c.edge_id)
            a,b=c.edge_id.split(":"),outgoing.edge_id.split(":")
            records.append({
                "edge":c.edge_id,"source":edge.source,"target":edge.target,
                "distance_m":round(c.distance_m,4),
                "heading_error_degrees":round(angular_difference(c.heading,second.bearing_deg),4),
                "score":round(c.score,6),"connector_m":round(connector,3)
                    if connector is not None else None,
                "time_reachable":possible,
                "same_osm_way":len(a)==len(b)==4 and a[:2]==b[:2],
                "same_direction":len(a)==len(b)==4 and a[3]==b[3]
            })
        result=temporal.update(second)
        expected_status=new[caseid]["status"]
        require((result.status=="MATCHED")==(expected_status=="CORRECT")
                and (result.status!="MATCHED")== (expected_status=="WITHHELD"),
                caseid+" replay status diverged")
        require(result.edge_id==new[caseid]["actual_edge"],caseid+" edge changed")
        cls=("RESOLVED_BY_NEW_RESEARCH_PROGRESS" if new[caseid]["status"]=="CORRECT"
             else classify(anchor,outgoing.edge_id,ids,reachable))
        totals[cls]+=1
        retained.append({
            "case_id":caseid,"generating_source_edge":outgoing.edge_id,
            "prior_default_status":old[caseid]["status"],
            "shadow_status":new[caseid]["status"],
            "anchor_status":anchor_result.status,"anchor_edge":anchor,
            "stateless_status":raw_result.status,"stateless_reason":raw_result.reason,
            "temporal_status":result.status,"temporal_reason":result.reason,
            "cause":cls,"candidates":records,
            "expected_in_candidates":outgoing.edge_id in ids,
            "expected_time_reachable":outgoing.edge_id in reachable,
            "reachable_count":len(reachable)
        })
    require(len(retained)==18,"target count no longer 18")
    lost=[cid for cid in old if old[cid]["status"]=="CORRECT"
          and new[cid]["status"]!="CORRECT"]
    require(not lost,"shadow newly loses prior source-correct cases")
    return {
        "test":"DMN-UK40-WITHHELD-18","classification":"DIAGNOSTIC_ONLY",
        "map_sha256":EXPECTED_XML_HASH,"original_oracle_sha256":ORACLE,
        "default_correct":17,"historical_shadow_correct":22,
        "historical_shadow_withheld":18,
        "shadow_correct":shadow["correct"],"shadow_withheld":shadow["withheld"],
        "historical_18_case_ids":sorted(PREVIOUS_18),
        "confident_wrong":0,"previous_correct_lost":lost,
        "reason_counts":dict(sorted(totals.items())),
        "remaining_case_ids":[r["case_id"] for r in retained
                              if r["shadow_status"]=="WITHHELD"],
        "newly_resolved_case_ids":[r["case_id"] for r in retained
                                  if r["shadow_status"]=="CORRECT"],
        "cases":retained,"external_engine_comparison":False,
        "independent_position_and_road_legality":"UNVERIFIED",
        "default_engine_changed":False
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--map",type=Path,required=True)
    p.add_argument("--archive-hash",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    x=p.parse_args()
    results=(ROOT/"results").resolve()
    require(x.map.resolve().is_relative_to(results) and
            x.output.resolve().is_relative_to(results) and
            x.map.suffix==".osm" and x.output.suffix==".json",
            "must operate only on ignored results")
    require(json.loads(x.archive_hash.read_text())["archive_sha256"]==EXPECTED_ARCHIVE_HASH,
            "historical archive differs")
    raw=x.map.read_bytes()
    require(sha256(raw).hexdigest()==EXPECTED_XML_HASH,"historical XML differs")
    result=inspect(raw)
    x.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "test":result["test"],"historic_cases_inspected":len(result["cases"]),
        "currently_withheld":result["shadow_withheld"],
        "newly_resolved":len(result["newly_resolved_case_ids"]),
        "reasons":result["reason_counts"],
        "cases":[{"id":v["case_id"],"cause":v["cause"],"anchor":v["anchor_status"],
                  "candidates":[c["edge"] for c in v["candidates"]],
                  "reachable":v["reachable_count"],"reason":v["temporal_reason"]}
                 for v in result["cases"]],
        "default_unchanged":True,"source_truth":"PROVISIONAL"
    },indent=2))

if __name__=="__main__":
    main()
