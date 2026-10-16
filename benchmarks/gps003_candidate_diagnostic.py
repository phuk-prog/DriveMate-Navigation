"""Read-only candidate-geometry diagnosis on frozen public map and observations."""
import argparse
import json
from hashlib import sha256
from pathlib import Path
from benchmarks.real_map_gps_recovery import freeze
from benchmarks.public_temporal_gps import _bearing, _point, competing_link_evidence
from benchmarks.itinero_public_probe import EXPECTED_XML_HASH, EXPECTED_ARCHIVE_HASH
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher, angular_difference
from gps.temporal_matcher import TemporalRoadMatcher
from map_data import Provenance, import_osm_xml

ROOT=Path(__file__).resolve().parents[1]
TARGETS=(6,8,13,15,16,19,39)
ORACLE_SHA="612f2469facbc4e02fd8233a78d3cb2aa9f1bb40a892efb88e9bf91d116b80b0"

def need(ok,what):
    if not ok: raise ValueError("Frozen-evidence mismatch: "+what)

def relation(graph,a,b):
    x,y=graph.edges[a],graph.edges[b]
    if x.target==y.source: kind="forward_adjacent"
    elif x.source==y.target: kind="backward_adjacent"
    elif x.source==y.source: kind="shared_source"
    elif x.target==y.target: kind="shared_target"
    else: kind="not_adjacent"
    i,j=a.split(":"),b.split(":")
    return {"relationship":kind,"same_osm_way":len(i)==len(j)==4 and i[1]==j[1],
            "same_direction":len(i)==len(j)==4 and i[3]==j[3],
            "forward_turn_permitted_on_imported_map":x.target==y.source and
                (a,b) not in graph.prohibited_turns,
            "independent_road_law":"UNVERIFIED"}

def candidate(graph,c,fix):
    e=graph.edges[c.edge_id]
    return {"edge_id":c.edge_id,"from_vertex":e.source,"to_vertex":e.target,
            "access":e.access,"length_m":round(e.length_m,4),
            "distance_m":round(c.distance_m,4),
            "heading_deg":round(c.heading,4),
            "heading_error_deg":round(angular_difference(c.heading,fix.bearing_deg),4),
            "score":round(c.score,6)}

def original_uk_pairs(graph):
    pairs=[]
    for e in sorted(graph.edges.values(),key=lambda e:e.edge_id):
        if e.access!="allowed" or e.length_m<20:continue
        for f in graph.adjacency[e.target]:
            if f.access=="allowed" and f.length_m>=15 and (e.edge_id,f.edge_id) not in graph.prohibited_turns:
                pairs.append((e,f))
    return pairs[::max(1,len(pairs)//40)][:40]

def analyze(raw):
    manifest=freeze(raw)
    need(sha256((json.dumps(manifest,indent=2)+"\n").encode()).hexdigest()==ORACLE_SHA,
         "original GPS oracle")
    oldgps=json.loads((ROOT/"references/gps003-real-map-20261016.json").read_text())["report"]
    olduk=json.loads((ROOT/"references/gps001-uk-topology-20261015.json").read_text())["report"]
    need(oldgps["oracle_sha256"]==ORACLE_SHA and oldgps["passed"]==8 and oldgps["total"]==24,
         "old GPS003 result")
    need(olduk["source_sha256"]==EXPECTED_XML_HASH and
         (olduk["temporal_correct"],olduk["temporal_confident_wrong"],olduk["temporal_withheld"])==(17,0,23),
         "old UK40 result")
    imported=import_osm_xml(raw,provenance=Provenance("public GPS diagnostic","Geofabrik260901",
         "Geofabrik-public-pinned","OpenStreetMap contributors; ODbL"))
    graph,coords=imported.graph,imported.coordinates
    matcher=DirectedRoadMatcher(graph,coords)
    actualold={c["case_id"]:c for c in oldgps["cases"]}
    gps=[]
    for base in ("GPS-003-B1","GPS-003-B2"):
        name=base+"-clear"
        spec=next(c for c in manifest["cases"] if c["id"]==name)
        first=spec["events"][0]
        need(sum(c["base_segment"]==base and c["events"][0]==first for c in manifest["cases"])==8,
             base+" eight repeated initial fixes")
        fix=GPSFix(*first["fix"])
        options=matcher._candidates(fix)
        status=matcher.match(fix,now_ms=first["now_ms"])
        previous=actualold[name]["events"][0]
        need(status.status==previous["actual_status"]=="AMBIGUOUS" and
             status.reason==previous["reason"] and len(options)==previous["candidates"]==2 and
             not previous["passed"],base+" unchanged first-fix failure")
        gps.append({"base":base,"case_id":name,"repeat_count":8,"fix":first["fix"],
             "required_edge":spec["expected_edge"],"status":status.status,
             "reason":status.reason,"candidates":[candidate(graph,c,fix) for c in options],
             "relationship":relation(graph,options[0].edge_id,options[1].edge_id),
             "score_gap":round(options[1].score-options[0].score,6)})
    pairs=original_uk_pairs(graph)
    need(len(pairs)==40,"original deterministic UK40 selection")
    oldcases={x["case_id"]:x for x in olduk["case_diagnostics"]}
    uk=[]
    for n in TARGETS:
        case=f"TGP-{n:03d}"
        incoming,outgoing=pairs[n-1]
        first=GPSFix(1000,*_point(coords[incoming.source],coords[incoming.target],.70),
                     3.,10.,_bearing(coords[incoming.source],coords[incoming.target]))
        second=GPSFix(9000,*_point(coords[outgoing.source],coords[outgoing.target],.20),
                      3.,10.,_bearing(coords[outgoing.source],coords[outgoing.target]))
        temporal=TemporalRoadMatcher(matcher)
        anchored=temporal.update(first)
        aid=temporal.anchor_edge_id
        need(aid is not None,case+" anchor")
        options=matcher._candidates(second)
        byid={x.edge_id:x for x in options}
        direct,reachable=set(),set()
        for edge_id in temporal._plausible_edges(second):
            edge=graph.edges[edge_id]
            if edge_id==aid or (graph.edges[aid].target==edge.source and
                                (aid,edge_id) not in graph.prohibited_turns):
                direct.add(edge_id)
            distance=temporal._connection_length(aid,edge_id)
            if distance is not None and temporal._transition_fits_time(aid,edge_id,second,distance):
                reachable.add(edge_id)
        result=temporal.update(second)
        old=oldcases[case]
        need(anchored.status==old["initial_anchor_status"] and
             result.status==old["temporal_status"]=="AMBIGUOUS" and
             len(direct)==old["direct_candidates"]==1 and
             len(reachable)==old["time_reachable_candidates"]==2,
             case+" current diagnostic differs from old")
        need(outgoing.edge_id in direct and outgoing.edge_id in reachable,
             case+" expected direct edge missing")
        alt=reachable-direct
        need(len(alt)==1,case+" unexpected alternate candidate count")
        alt_id=next(iter(alt))
        need(outgoing.edge_id in byid and alt_id in byid,case+" candidate details missing")
        observed=competing_link_evidence(temporal,second,direct,reachable)
        expected=old["competing_link_details"]
        need(len(observed)==len(expected)==1,case+" historical candidate geometry missing")
        for key in ("relationship","same_osm_way","same_direction_flag"):
            need(observed[0][key]==expected[0][key],case+" changed "+key)
        for key in ("direct_position_residual_m","alternative_position_residual_m",
                    "heading_difference_deg","bounded_connector_from_direct_m"):
            need(abs(observed[0][key]-expected[0][key])<.03,case+" changed "+key)
        uk.append({"case_id":case,"anchor_edge":aid,"expected_edge":outgoing.edge_id,
             "status":result.status,"direct_candidate":candidate(graph,byid[outgoing.edge_id],second),
             "alternative":candidate(graph,byid[alt_id],second),
             "relationship":relation(graph,outgoing.edge_id,alt_id),
             "connector_m":observed[0]["bounded_connector_from_direct_m"],
             "matches_historical_metrics":True})
    return {"trial":"GPS-003-CANDIDATE-DIAGNOSTIC","classification":"read-only map-derived",
            "map_sha256":EXPECTED_XML_HASH,"frozen_oracle_sha256":ORACLE_SHA,
            "gps003":gps,"uk40":uk,"gps003_original":"8/24 passed, 16/24 failed",
            "uk40_original":"17/40 correct, 0 wrong, 23 withheld",
            "engine_behavior_changed":False,"acceptance_changed":False,
            "independent_road_truth":False,"competitor_ranking":None}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--map",type=Path,required=True)
    p.add_argument("--archive-hash",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    results=(ROOT/"results").resolve()
    need(a.map.resolve().is_relative_to(results) and a.map.suffix==".osm","map must be ignored results XML")
    need(a.output.resolve().is_relative_to(results) and a.output.suffix==".json",
         "output must be ignored results JSON")
    need(json.loads(a.archive_hash.read_text())["archive_sha256"]==EXPECTED_ARCHIVE_HASH,
         "archive hash must remain pinned")
    raw=a.map.read_bytes()
    need(sha256(raw).hexdigest()==EXPECTED_XML_HASH,"historical XML must remain identical")
    report=analyze(raw)
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"gps003":report["gps003"],"uk40":report["uk40"],
                      "no_behavior_change":True},indent=2))

if __name__=="__main__":
    main()
