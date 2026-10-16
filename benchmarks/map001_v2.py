"""MAP-001 v2: source-direction, access and relation-context study, real UK ways.

Case selection reuses v1 on six NEWLY fetched OSM source slices; do not compare
raw score changes as a same-input before/after. No independent road-law proof.
"""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from benchmarks.map001_graph_fact_audit import (
    ROOT,AREAS,source,choose,digest,tags,expected_edges,ENGINE_AUDIT)
from map_data import import_osm_xml,Provenance,OSMImportError
from map_data.osm_xml import DRIVING_SPEEDS,UNCERTAIN_ROADS

CLASSES=set(DRIVING_SPEEDS)|set(UNCERTAIN_ROADS)
OPEN={"yes","designated","permissive"}
CLOSED={"no","private","agricultural","forestry","delivery","destination","customers","permit"}
BLOCK={"bollard","block","cycle_barrier","bus_trap"}

def access(t):
    for key in ("motorcar","motor_vehicle","vehicle","access"):
        if key in t:
            return "allowed" if t[key] in OPEN else "prohibited" if t[key] in CLOSED else "unknown"
    return "unknown" if t.get("highway") in UNCERTAIN_ROADS else "allowed"

def barrier(t):
    b=t.get("barrier")
    if not b:return "allowed"
    for key in ("motorcar","motor_vehicle","vehicle","access"):
        if key in t:
            return ("prohibited" if t[key] in CLOSED else
                    "allowed" if t[key] in OPEN and b not in BLOCK else "unknown")
    return "prohibited" if b in BLOCK else "unknown"

def merge(*v):
    return "prohibited" if "prohibited" in v else "unknown" if "unknown" in v else "allowed"

def related(id,relations):
    return [r for r in relations if tags(r).get("type")=="restriction" and
            any(m.get("type")=="way" and m.get("ref")==id for m in r.findall("member"))]

def context(id,ways,nodes,relations):
    rels=related(id,relations)
    included={id}
    for r in rels:
        included.update(m.get("ref") for m in r.findall("member") if m.get("type")=="way")
    if not included.issubset(ways):return None,"missing_relation_source_way"
    via={m.get("ref") for r in rels for m in r.findall("member")
         if m.get("type")=="node" and m.get("role")=="via"}
    if any(tags(r).get("restriction","").startswith("only_") for r in rels):
        included.update(wid for wid,w in ways.items()
                        if tags(w).get("highway") in CLASSES and
                        any(n.get("ref") in via for n in w.findall("nd")))
    if len(included)>80:return None,"too_many_context_ways"
    usednodes={n.get("ref") for wid in included for n in ways[wid].findall("nd")}
    if not usednodes.issubset(nodes):return None,"incomplete_context_nodes"
    root=ET.Element("osm",version="0.6")
    for node in sorted(usednodes,key=int):root.append(deepcopy(nodes[node]))
    for wid in sorted(included,key=int):root.append(deepcopy(ways[wid]))
    for rel in rels:root.append(deepcopy(rel))
    return ET.tostring(root),None

def source_edges(way,nodes):
    geom=expected_edges(way)
    if geom is None:return None
    result={}
    t=tags(way)
    refs=[n.get("ref") for n in way.findall("nd")]
    for i,(a,b) in enumerate(zip(refs,refs[1:])):
        status=merge(access(t),barrier(tags(nodes[a])),barrier(tags(nodes[b])))
        for orient in ("f","r"):
            eid=f"w:{way.get('id')}:{i}:{orient}"
            if eid in geom:result[eid]=(*geom[eid],status)
    return result

def restriction_expectation(rels,allways,nodes):
    edges={}
    for w in allways.values():
        sub=source_edges(w,nodes)
        if sub:edges.update(sub)
    result=set()
    for r in rels:
        t=tags(r)
        if any(k.endswith(":conditional") for k in t):return None,"conditional_relation"
        excepts={s.strip() for s in t.get("except","").replace(",",";").split(";")}
        if "motorcar" in excepts:continue
        rule=t.get("restriction:motorcar",t.get("restriction:motor_vehicle",t.get("restriction","")))
        members=r.findall("member")
        fr=[m.get("ref") for m in members if m.get("role")=="from" and m.get("type")=="way"]
        to=[m.get("ref") for m in members if m.get("role")=="to" and m.get("type")=="way"]
        via=[m.get("ref") for m in members if m.get("role")=="via" and m.get("type")=="node"]
        if not (len(fr)==len(to)==len(via)==1 and len(members)==3 and
                (rule.startswith("no_") or rule.startswith("only_"))):
            return None,"unsupported_relation_shape"
        v="osm:"+via[0]
        arrivals={eid for eid,(_,end,_) in edges.items()
                  if eid.split(":")[1]==fr[0] and end==v}
        intended={eid for eid,(start,_,_) in edges.items()
                  if eid.split(":")[1]==to[0] and start==v}
        if not arrivals or not intended:return None,"unrepresentable_relation"
        outgoing={eid for eid,(start,_,_) in edges.items() if start==v}
        result.update((a,b) for a in arrivals
                      for b in (intended if rule.startswith("no_") else outgoing-intended))
    return result,None

def audit(area,selected,ways,nodes,relations):
    id=selected["way"]
    row={"case_id":area+"-"+id,"source_way":id,"kind":selected["kind"]}
    xml,problem=context(id,ways,nodes,relations)
    if problem:return {**row,"verdict":"NOT_JUDGED","type":"TEST_DATA","reason":problem}
    root=ET.fromstring(xml)
    refs=related(id,relations)
    contained={x.get("id"):x for x in root.findall("way")}
    expected=source_edges(ways[id],nodes)
    if expected is None:return {**row,"verdict":"NOT_JUDGED","type":"SOURCE","reason":"unrecognized_direction"}
    dynamic=any(any(k.endswith(":conditional") for k in tags(o)) for o in root)
    try:
        imported=import_osm_xml(xml,provenance=Provenance(area,"v2 live API frozen before test",
                "public UK OSM source context","OpenStreetMap contributors; ODbL"))
    except OSMImportError as e:
        return {**row,"verdict":"SAFE_WITHHELD" if dynamic else "NOT_JUDGED",
                "type":"DMN_COVERAGE" if dynamic else "DMN_OR_TEST",
                "reason":"conditional_not_supported" if dynamic else "import_rejected",
                "detail":str(e)[:160]}
    if dynamic:return {**row,"verdict":"FAIL","type":"DMN_SAFETY","reason":"conditional_source_accepted"}
    actual={eid:(e.source,e.target,e.access) for eid,e in imported.graph.edges.items()
            if eid.split(":")[1]==id}
    errors=[]
    if set(actual)!=set(expected):errors.append("missing_or_extra_edge")
    if any(actual[k]!=v for k,v in expected.items() if k in actual):
        errors.append("access_direction_or_endpoints")
    turn_truth,missing=restriction_expectation(refs,contained,nodes)
    if missing:
        return {**row,"verdict":"FAIL" if errors else "NOT_JUDGED",
                "type":"DMN" if errors else "TEST_OR_SOURCE",
                "reason":",".join(errors) if errors else missing}
    if turn_truth-imported.graph.prohibited_turns:errors.append("missing_prohibited_turn")
    return {**row,"verdict":"FAIL" if errors else "PASS",
            "type":"DMN" if errors else "SOURCE_AGREEMENT",
            "reason":",".join(errors) if errors else "source_context_agrees",
            "relation_count":len(refs),"expected_turn_pairs":len(turn_truth),
            "expected_directed_edges":len(expected),"observed_directed_edges":len(actual)}

def execute():
    snapshots=[source(ROOT/("map001-"+name+".osm")) for name in AREAS]
    manifest={"trial":"MAP-001-V2","case_total":120,"areas":[]}
    for name,(raw,nodes,ways,linked) in zip(AREAS,snapshots):
        manifest["areas"].append({"area":name,"raw_source_sha256":digest(raw),
                                   "cases":choose(ways,nodes,linked)})
    (ROOT/"map001-v2-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    rows=[]
    for spec,(raw,nodes,ways,_) in zip(manifest["areas"],snapshots):
        if digest(raw)!=spec["raw_source_sha256"]:raise ValueError("frozen source mismatch")
        relations=ET.fromstring(raw).findall("relation")
        for selected in spec["cases"]:
            w=ways[selected["way"]]
            if digest(json.dumps(tags(w),sort_keys=True).encode())!=selected["tags_sha"]:
                raise ValueError("frozen case changed")
            rows.append(audit(spec["area"],selected,ways,nodes,relations))
    summary=Counter(x["verdict"] for x in rows)
    causes=Counter((x["type"],x["reason"]) for x in rows if x["verdict"]!="PASS")
    report={"trial":"MAP-001-V2","category":"map_data","cases":rows,"case_total":len(rows),
            "counts":dict(summary),"issues":[{"type":t,"reason":r,"count":count}
                     for (t,r),count in sorted(causes.items())],
            "external_graph_fact_engines":ENGINE_AUDIT,
            "overall_engine_rankings":None,
            "source_truth":"PROVISIONAL_OSM_NOT_REAL_ROAD_LAW",
            "same_snapshot_as_v1":False,
            "app_tested":False}
    (ROOT/"map001-v2-scorecard.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"trial":report["trial"],"counts":report["counts"],
                      "issues":report["issues"]},indent=2),flush=True)
    if summary["FAIL"]:raise SystemExit("Source graph mismatch found; inspect cases")

if __name__=="__main__":execute()
