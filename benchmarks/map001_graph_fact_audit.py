"""MAP-001: compare DMN graph facts against frozen public UK OSM ways.

PROVISIONAL source agreement only. No fabricated external graph inspection.
"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from map_data import Provenance, import_osm_xml, OSMImportError
from map_data.osm_xml import DRIVING_SPEEDS, UNCERTAIN_ROADS

ROOT=Path(__file__).resolve().parents[1]/"results"
AREAS=("manchester","birmingham","carlisle","cardiff","glasgow","belfast")
ENGINE_AUDIT={x:"NO_EQUIVALENT_GRAPH_FACT_INSPECTION_ADAPTER"
 for x in ("OSRM","Valhalla","GraphHopper","openrouteservice","BRouter",
           "Itinero","Routino","OsmAnd","Organic Maps")}
ENGINE_AUDIT.update({x:"NO_AUTHORIZED_INTERNAL_GRAPH_INTERFACE"
 for x in ("HERE","Mapbox","TomTom","Google Maps","Waze")})
HIGHWAYS=set(DRIVING_SPEEDS)|set(UNCERTAIN_ROADS)

def digest(x):return sha256(x).hexdigest()
def tags(e):return {n.get("k"):n.get("v") for n in e.findall("tag")}
def source(path):
    raw=path.read_bytes()
    if not 0<len(raw)<=6000000:raise ValueError("source size beyond 6MB")
    tree=ET.fromstring(raw)
    if tree.tag!="osm":raise ValueError("not public OSM")
    nodes={x.get("id"):x for x in tree.findall("node")}
    ways={x.get("id"):x for x in tree.findall("way")}
    restricted=set()
    for rel in tree.findall("relation"):
        if tags(rel).get("type")=="restriction":
            restricted.update(m.get("ref") for m in rel.findall("member")
                              if m.get("type")=="way")
    return raw,nodes,ways,restricted

def choose(ways,nodes,related):
    eligible=[]
    for id,w in sorted(ways.items(),key=lambda x:int(x[0])):
        t=tags(w)
        refs=[n.get("ref") for n in w.findall("nd")]
        if t.get("highway") not in HIGHWAYS or len(refs)<2 or any(r not in nodes for r in refs):
            continue
        k=("conditional" if any(z.endswith(":conditional") for z in t) else
           "oneway" if t.get("oneway") in ("yes","1","true","-1","reverse") else
           "roundabout" if t.get("junction") in ("roundabout","circular") else
           "access" if "motorcar" in t or "access" in t else
           "link" if t.get("highway","").endswith("_link") else
           "service" if t.get("highway") in UNCERTAIN_ROADS else "ordinary")
        eligible.append((id,k,t))
    chosen=[];used=set()
    for kind,number in (("oneway",4),("roundabout",2),("access",3),
                        ("link",3),("service",2),("conditional",2),("ordinary",20)):
        for id,k,t in eligible:
            if k!=kind or id in used:continue
            if sum(v["kind"]==kind for v in chosen)>=number:break
            chosen.append({"way":id,"kind":k,"tags_sha":digest(json.dumps(t,sort_keys=True).encode()),
                           "restriction_related":id in related})
            used.add(id)
            if len(chosen)==20:break
        if len(chosen)==20:break
    if len(chosen)<20:
        for id,k,t in eligible:
            if id not in used:
                chosen.append({"way":id,"kind":k,"tags_sha":digest(json.dumps(t,sort_keys=True).encode()),
                               "restriction_related":id in related})
                used.add(id)
            if len(chosen)==20:break
    if len(chosen)!=20:raise ValueError("Insufficient real drivable source ways")
    return chosen

def isolated(way,nodes):
    root=ET.Element("osm",version="0.6")
    seen=set()
    for ref in way.findall("nd"):
        id=ref.get("ref")
        if id in seen:continue
        seen.add(id)
        n=nodes[id]
        a=ET.SubElement(root,"node",id=id,lat=n.get("lat"),lon=n.get("lon"))
        for k,v in tags(n).items():
            if k in ("barrier","motorcar","vehicle","motor_vehicle","access") or k.endswith(":conditional"):
                ET.SubElement(a,"tag",k=k,v=v)
    w=ET.SubElement(root,"way",id=way.get("id"))
    for n in way.findall("nd"):ET.SubElement(w,"nd",ref=n.get("ref"))
    for k,v in tags(way).items():ET.SubElement(w,"tag",k=k,v=v)
    return ET.tostring(root)

def expected_edges(way):
    t=tags(way);o=t.get("oneway","")
    if not o and t.get("junction") in ("roundabout","circular"):o="yes"
    if o not in ("","no","0","false","yes","1","true","-1","reverse"):return None
    directions=("r",) if o in ("-1","reverse") else (
        ("f",) if o in ("yes","1","true") else ("f","r"))
    refs=[x.get("ref") for x in way.findall("nd")]
    expected={}
    for i,(a,b) in enumerate(zip(refs,refs[1:])):
        for d in directions:
            expected[f"w:{way.get('id')}:{i}:{d}"]=(
                (f"osm:{a}",f"osm:{b}") if d=="f" else (f"osm:{b}",f"osm:{a}"))
    return expected

def judge(area,case,way,nodes):
    ident=case["way"]
    row={"case_id":area+"-"+ident,"source_way":ident,"kind":case["kind"]}
    if case["restriction_related"]:
        return {**row,"result":"NOT_JUDGED","issue":"attached_turn_relation_omitted_from_isolated_case"}
    xml=isolated(way,nodes)
    conditional=b":conditional" in xml
    expectation=expected_edges(way)
    try:
        m=import_osm_xml(xml,provenance=Provenance(area,"public API fetched frozen source",
                "OpenStreetMap bounded case","OpenStreetMap contributors; ODbL"))
    except OSMImportError as e:
        return {**row,"result":"NOT_JUDGED",
                "issue":"conservative_source_rejection","reason":str(e)[:180]}
    if conditional or expectation is None:
        return {**row,"result":"FAIL",
                "issue":"unsupported_source_semantics_were_accepted"}
    actual={eid:(e.source,e.target) for eid,e in m.graph.edges.items()}
    errors=[]
    if set(actual)!=set(expectation):errors.append("direction_or_edge_count")
    if any(actual[eid]!=pair for eid,pair in expectation.items() if eid in actual):
        errors.append("graph_connectivity_or_orientation")
    if any(e.length_m<=0 for e in m.graph.edges.values()):
        errors.append("invalid_segment_length")
    # The importer does not return all source attributes; access/turn
    # completeness is NOT certified by a directed-geometry-only pass.
    return {**row,"result":"FAIL" if errors else "PASS",
            "issue":",".join(errors) if errors else "none",
            "expected_edges":len(expectation),"actual_edges":len(actual)}

def execute():
    sources=[ROOT/("map001-"+n+".osm") for n in AREAS]
    records=[source(path) for path in sources]
    manifest={"trial":"MAP-001","case_count":120,"status":"FROZEN_BEFORE_SCORING",
              "source_ground_truth":"PROVISIONAL_OSM_NOT_SIGNED_ROAD_LAW",
              "areas":[]}
    for name,(raw,nodes,ways,related) in zip(AREAS,records):
        manifest["areas"].append({"area":name,"source_sha256":digest(raw),
            "cases":choose(ways,nodes,related)})
    (ROOT/"map001-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    cases=[]
    # Source hashes and case IDs were frozen above before any DMN imports.
    for spec,(_,nodes,ways,_) in zip(manifest["areas"],records):
        for case in spec["cases"]:
            way=ways[case["way"]]
            if digest(json.dumps(tags(way),sort_keys=True).encode())!=case["tags_sha"]:
                raise ValueError("OSM freeze changed")
            cases.append(judge(spec["area"],case,way,nodes))
    totals=Counter(c["result"] for c in cases)
    report={"trial":"MAP-001","category":"map_data","cases_total":len(cases),
            "source_agreement_pass":totals["PASS"],"source_mismatch_fail":totals["FAIL"],
            "unjudged":totals["NOT_JUDGED"],"cases":cases,
            "competitor_graph_fact_support":ENGINE_AUDIT,
            "full_common_engine_ranking":None,
            "ranking_blocker":"No comparable external directed-graph fact APIs configured",
            "dmn_issues":[x for x in cases if x["result"]=="FAIL"],
            "test_or_data_issues":[x for x in cases if x["result"]=="NOT_JUDGED"],
            "current_real_road_truth_verified":False,
            "navigation_app_tested":False}
    (ROOT/"map001-scorecard.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("trial","cases_total","source_agreement_pass",
            "source_mismatch_fail","unjudged","ranking_blocker")},indent=2),flush=True)
    if report["source_mismatch_fail"]:raise SystemExit("DMN source graph mismatches found")

if __name__=="__main__":execute()
