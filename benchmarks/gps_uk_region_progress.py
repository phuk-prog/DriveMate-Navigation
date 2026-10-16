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
            if len(chosen)==limit or (same and len(chosen)>=limit//2):break
        if len(chosen)==limit:break
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


def conservative_executable_subset(raw):
    """Exclude uncertain source ways and dependent turn manoeuvres, not tags.

    The prototype importer cannot prove conditional legality. Omitting the
    entire connected restriction cohort is safer than stripping a condition
    and treating the road as unconditionally legal. Keep source hash/audit.
    """
    import xml.etree.ElementTree as ET
    from collections import Counter
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("OSM source with entities/DTD is prohibited")
    root=ET.fromstring(raw)
    ways={w.get("id"):w for w in root.findall("way")}
    nodes={n.get("id"):n for n in root.findall("node")}
    restrictions=[r for r in root.findall("relation")
                  if any(t.get("k")=="type" and t.get("v")=="restriction"
                         for t in r.findall("tag"))]
    flags=Counter()
    def tags(elem):
        return {t.get("k",""):t.get("v","") for t in elem.findall("tag")}
    bad_nodes={node_id for node_id,node in nodes.items()
               if any(k.endswith("conditional") for k in tags(node))}
    forbidden=set()
    for way_id,way in ways.items():
        attributes=tags(way)
        if any(k.endswith("conditional") for k in attributes):
            forbidden.add(way_id)
            flags["conditional_way"]+=1
        if any(nd.get("ref") in bad_nodes for nd in way.findall("nd")):
            forbidden.add(way_id)
            flags["touches_conditional_node"]+=1
        direction=attributes.get("oneway","").lower()
        if direction not in ("","no","0","false","yes","1","true","-1","reverse"):
            forbidden.add(way_id)
            flags["unsupported_oneway"]+=1
    flags["conditional_nodes"]=len(bad_nodes)
    # Unsupported/missing restrictions cause all involved road ways to become
    # unknown in this bounded experiment. Propagate to dependent manoeuvres.
    active=[]
    for relation in restrictions:
        attr=tags(relation)
        members=relation.findall("member")
        froms=[m for m in members if m.get("type")=="way" and m.get("role")=="from"]
        tos=[m for m in members if m.get("type")=="way" and m.get("role")=="to"]
        vias=[m for m in members if m.get("type")=="node" and m.get("role")=="via"]
        rule=attr.get("restriction:motorcar",
             attr.get("restriction:motor_vehicle",attr.get("restriction","")))
        related={m.get("ref") for m in members if m.get("type")=="way"}
        supported=(not any(k.endswith("conditional") for k in attr)
                   and (rule.startswith("no_") or rule.startswith("only_"))
                   and len(froms)==len(tos)==len(vias)==1 and len(members)==3
                   and all(w in ways for w in related) and vias[0].get("ref") in nodes)
        if not supported:
            forbidden.update(related & ways.keys())
            flags["unsupported_restriction_relations"]+=1
        else:
            active.append((relation,related))
    changed=True
    while changed:
        changed=False
        for relation,related in active:
            if related & forbidden:
                add=(related & ways.keys())-forbidden
                forbidden.update(add)
                changed=changed or bool(add)
                if add:flags["excluded_restriction_dependents"]+=len(add)
    for way_id in forbidden:
        if way_id in ways:root.remove(ways[way_id])
    for relation in restrictions:
        related={m.get("ref") for m in relation.findall("member")
                 if m.get("type")=="way"}
        if related & forbidden or any(
            k.endswith("conditional") for k in tags(relation)):
            root.remove(relation)
    # Nonrestriction relations are not interpreted by the motorcar importer.
    for node_id in bad_nodes:
        if node_id in nodes:root.remove(nodes[node_id])
    flags["omitted_complete_ways"]=len(forbidden & ways.keys())
    result=ET.tostring(root,encoding="utf-8",xml_declaration=True)
    if len(result)>6_000_000:
        raise ValueError("Filtered analytical input still exceeds importer limit")
    return result,dict(sorted(flags.items()))

def analyse(name,raw):
    # Historical public XML stays unchanged; unsupported conditions are
    # excluded as entire road ways and connected restrictions, not stripped.
    filtered,exclusions=conservative_executable_subset(raw)
    data=import_osm_xml(filtered,provenance=Provenance(
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
            "scored_subset_sha256":sha256(filtered).hexdigest(),
            "excluded_source_objects":exclusions,
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
            "excluded_source_objects":x["excluded_source_objects"],
            "reverse_checks":len(x["reverse_trajectory_checks"]),
            "safety_failures":x["safety_failure_count"]} for x in regions],
        "independent_road_truth":False},indent=2),flush=True)
    if report["safety_failure_count"]:
        raise SystemExit("Unsafe: confidently wrong source-geometry or reverse-progress edge")

if __name__=="__main__":
    main()
