"""MAP-001 native node-barrier and source turn-mask evidence, six UK regions.

This is a narrow STRUCTURAL native mask comparison, not complete AutoCost,
routing legality, independent UK road orders, or equivalence of traversal
policy at graph nodes. Conditional and qualified access are always unscored.
"""
from __future__ import annotations
from collections import Counter
import json
import xml.etree.ElementTree as ET

from benchmarks.map001_graph_fact_audit import ROOT, AREAS, digest, source, tags
from benchmarks.map001_v3 import FROZEN_V2_IDS
from benchmarks.map001_native_reference import read_native
from benchmarks.map001_category1_closure import relation_facts, expected_way
from benchmarks.map001_native_reference import align_edge


def native_mask_verdict(rule, source_status, candidates):
    """Compare only a single unambiguous simple 'no_' pair's explicit bit."""
    if not rule.startswith("no_"):
        return "UNSUPPORTED_ONLY_TURN_COMPLETENESS"
    if source_status != "REPRESENTABLE_SOURCE_MOVEMENT":
        return "NOT_JUDGED_SOURCE_MOVEMENT_OR_ACCESS"
    if len(candidates) != 1:
        return "NOT_JUDGED_ZERO_OR_MULTIPLE_NATIVE_PAIRS"
    c=candidates[0]
    if (not c["incoming_car"] or not c["outgoing_car"]
        or c["contextual_native_flags"] or c["local_index"] not in range(8)):
        return "NOT_JUDGED_NATIVE_TURN_POLICY_CONTEXT"
    return "PASS" if c["mask_bit"] else "FAIL"


def candidate_pairs(rel, edges, nodes):
    members=rel.findall("member")
    fr=[m.get("ref") for m in members if m.get("role")=="from" and m.get("type")=="way"]
    to=[m.get("ref") for m in members if m.get("role")=="to" and m.get("type")=="way"]
    via=[m.get("ref") for m in members if m.get("role")=="via" and m.get("type")=="node"]
    if not (len(fr)==len(to)==len(via)==1 and len(members)==3):
        return []
    if via[0] not in nodes:
        return []
    point=(float(nodes[via[0]].get("lat")),float(nodes[via[0]].get("lon")))
    arrivals=[e for e in edges if str(e["way_id"])==fr[0] and len(e.get("shape",[]))>=2
              and max(abs(e["shape"][-1][k]-point[k]) for k in (0,1))<=0.000002]
    bystart={}
    for e in edges:
        bystart.setdefault(e["start_node"],[]).append(e)
    found={}
    for e in arrivals:
        for outgoing in bystart.get(e["end_node"],[]):
            if str(outgoing["way_id"])!=to[0]:
                continue
            if not outgoing.get("shape") or max(abs(outgoing["shape"][0][k]-point[k]) for k in (0,1))>0.000002:
                continue
            index=outgoing.get("local_index")
            mask=e.get("restriction_mask")
            if type(index) is not int or type(mask) is not int:
                continue
            row={
             "incoming_graph_edge":e["graph_id"],"outgoing_graph_edge":outgoing["graph_id"],
             "junction_graph_node":e["end_node"],
             "incoming_car":e["car_access"],"outgoing_car":outgoing["car_access"],
             "local_index":index,"arrival_restriction_mask":mask,
             "mask_bit":(bool(mask&(1<<index)) if 0<=index<8 else None),
             "contextual_native_flags":any([
                 e.get("complex"),outgoing.get("complex"),
                 e.get("start_restriction"),e.get("end_restriction"),
                 outgoing.get("start_restriction"),outgoing.get("end_restriction"),
                 e.get("access_restriction"),outgoing.get("access_restriction"),
                 e.get("destination_only"),outgoing.get("destination_only")])
            }
            found[(e["graph_id"],outgoing["graph_id"])]=row
    return list(found.values())



def only_native_junction_verdict(rel, ways, nodes, edges, source_status, pairs):
    """Compare complete source-qualified outgoing native mask bits (not AutoCost)."""
    if source_status != "REPRESENTABLE_SOURCE_MOVEMENT" or len(pairs)!=1:
        return "NOT_JUDGED_ONLY_SOURCE_OR_PAIR", []
    pair=pairs[0]
    if (not pair["incoming_car"] or not pair["outgoing_car"]
            or pair["contextual_native_flags"]):
        return "NOT_JUDGED_ONLY_NATIVE_CONTEXT", []
    arr=[e for e in edges if e["graph_id"]==pair["incoming_graph_edge"]]
    if len(arr)!=1:
        return "NOT_JUDGED_ONLY_AMBIGUOUS_ARRIVAL", []
    incoming=arr[0]
    members=rel.findall("member")
    targets=[m.get("ref") for m in members if m.get("role")=="to" and m.get("type")=="way"]
    vias=[m.get("ref") for m in members if m.get("role")=="via" and m.get("type")=="node"]
    if len(targets)!=1 or len(vias)!=1 or vias[0] not in nodes:
        return "NOT_JUDGED_ONLY_SOURCE_SHAPE", []
    point=(float(nodes[vias[0]].get("lat")),float(nodes[vias[0]].get("lon")))
    all_out=[e for e in edges if e["start_node"]==pair["junction_graph_node"] and e["car_access"]]
    out=[e for e in all_out if e.get("shape") and
         max(abs(e["shape"][0][k]-point[k]) for k in (0,1))<=0.000002]
    if len(out)!=len(all_out) or len(out)<2:
        return "NOT_JUDGED_ONLY_MISSING_ALTERNATIVES", []
    checks=[]
    for e in out:
        wid=str(e["way_id"])
        if wid not in ways or e.get("local_index") not in range(8):
            return "NOT_JUDGED_ONLY_MISSING_GRAPH_SOURCE", checks
        if any(e.get(k) for k in ("complex","start_restriction","end_restriction",
                                  "access_restriction","destination_only")):
            return "NOT_JUDGED_ONLY_NATIVE_CONTEXT", checks
        source_expected,issue=expected_way(ways[wid],nodes)
        mapped=align_edge(e,ways[wid],nodes)
        if issue or not mapped or any(
                eid not in source_expected or source_expected[eid][2]!="allowed"
                for eid in mapped):
            return "NOT_JUDGED_ONLY_OTHER_EXIT_ACCESS", checks
        prohibited=bool(incoming["restriction_mask"] & (1<<e["local_index"]))
        expected=wid!=targets[0]
        checks.append({"outgoing_graph_id":e["graph_id"],
                       "outgoing_osm_way":wid,
                       "outgoing_local_index":e["local_index"],
                       "expected_mask_prohibits":expected,
                       "observed_mask_prohibits":prohibited,
                       "source_segments":mapped,
                       "agrees":prohibited==expected})
    if not any(not x["expected_mask_prohibits"] for x in checks):
        return "NOT_JUDGED_ONLY_INTENDED_EXIT_MISSING",checks
    if not any(x["expected_mask_prohibits"] for x in checks):
        return "NOT_JUDGED_ONLY_NO_ALTERNATIVE",checks
    return ("PASS" if all(x["agrees"] for x in checks) else "FAIL"),checks

def assess_relation(area,rel,ways,nodes,edges):
    source=relation_facts(rel,ways,nodes)
    rule=tags(rel).get("restriction:motorcar",
         tags(rel).get("restriction:motor_vehicle",
         tags(rel).get("restriction","")))
    row={"area":area,"relation_id":rel.get("id"),
         "rule":rule,"source_applicability":source["verdict"],
         "source_rule_tags":{k:v for k,v in tags(rel).items()
                             if k in ("restriction","restriction:conditional","except","restriction:motorcar")},
         "independent_road_law":False,
         "full_turn_legality":"NOT_INSPECTED"}
    if any(k.endswith(":conditional") for k in tags(rel)):
        return {**row,"verdict":"NOT_JUDGED_CONDITIONAL_RELATION","native_pairs":[]}
    if source["verdict"]=="EXCEPTED_MOTORCAR":
        return {**row,"verdict":"NOT_JUDGED_MOTORCAR_EXEMPT","native_pairs":[]}
    pairs=candidate_pairs(rel,edges,nodes)
    if rule.startswith("only_"):
        status,alternatives=only_native_junction_verdict(
            rel,ways,nodes,edges,source["verdict"],pairs)
    else:
        status=native_mask_verdict(rule,source["verdict"],pairs)
        alternatives=[]
    return {**row,"verdict":status,"native_pairs":pairs,
            "native_only_exit_completeness_evidence":alternatives,
            "scope":"SOURCE_PROHIBITED_TURN_VS_NATIVE_MASK_BITS_ONLY",
            "native_route_autocost_checked":False}


def barrier_case(area,way,nodes,edges):
    wid=way.get("id")
    refs=[n.get("ref") for n in way.findall("nd")]
    barriers=[{"osm_node":ref,
               "source_tags":{k:v for k,v in tags(nodes[ref]).items()
                              if k in ("barrier","motorcar","motor_vehicle","vehicle","access")}}
              for ref in refs if ref in nodes and "barrier" in tags(nodes[ref])]
    if not barriers:
        return None
    native=[{key:e.get(key) for key in ("graph_id","way_id","car_access",
            "start_restriction","end_restriction","access_restriction","restriction_mask",
            "complex","destination_only")}
            for e in edges if str(e["way_id"])==wid]
    return {"area":area,"source_way":wid,"source_node_barriers":barriers,
            "native_edge_indicators":native,
            "source_car_rule":"NODE_BARRIER_REQUIRES_TRAVERSAL_POLICY_CHECK",
            "native_node_policy_equivalent":False,
            "scored":False,"verdict":"NOT_JUDGED_NATIVE_NODE_TRAVERSAL",
            "reason":"DIRECTED_EDGE_CAR_ACCESS_NOT_COMPLETE_NODE_BARRIER_ROUTABILITY"}


def run():
    manifest=json.loads((ROOT/"map001-v3-manifest.json").read_text())
    if [x["area"] for x in manifest["areas"]]!=list(AREAS):
        raise ValueError("Original UK region cohort changed")
    restrictions=[];barriers=[];region_meta=[]
    for spec in manifest["areas"]:
        area=spec["area"]
        raw,nodes,ways,_=source(ROOT/("map001-"+area+".osm"))
        if digest(raw)!=spec["source_sha256"] or [c["way"] for c in spec["cases"]]!=FROZEN_V2_IDS[area]:
            raise ValueError("Frozen sources / selected ways changed")
        native_file=(ROOT/("map001-valhalla-native.jsonl" if area=="manchester"
                           else "map001-valhalla-native-"+area+".jsonl"))
        edges,footer,native_sha=read_native(native_file)
        region_meta.append({"area":area,"source_sha256":digest(raw),
                            "native_graph_sha256":native_sha,
                            "native_complete_edges":footer["directed_edges"]})
        root=ET.fromstring(raw)
        selected=set(FROZEN_V2_IDS[area])
        for rel in root.findall("relation"):
            if tags(rel).get("type")!="restriction":
                continue
            if not any(m.get("type")=="way" and m.get("ref") in selected
                       for m in rel.findall("member")):
                continue
            restrictions.append(assess_relation(area,rel,ways,nodes,edges))
        for wid in FROZEN_V2_IDS[area]:
            result=barrier_case(area,ways[wid],nodes,edges)
            if result:
                barriers.append(result)
    scores=Counter(x["verdict"] for x in restrictions)
    report={"trial":"MAP-001-NATIVE-SIX-REGION-TURNS-BARRIERS",
            "source_restrictions_checked":len(restrictions),
            "barrier_ways_checked":len(barriers),
            "native_mask_structural_verdicts":dict(scores),
            "cases":restrictions, "node_barriers":barriers,
            "areas":region_meta,
            "fully_equivalent_native_turn_policy":False,
            "fully_equivalent_node_barrier_traversal":False,
            "uk_legal_signage_road_truth_verified":False,
            "independent_legal_turn_ranking":None,
            "engine_behavior_changed":False,
            "failures":[x for x in restrictions if x["verdict"]=="FAIL"],
            "incomplete_equivalence_reason":"AutoCost, traffic orders, complex restrictions, vehicle purpose, permits, and node transit not evaluated"}
    (ROOT/"map001-native-turn-barrier.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in
         ("trial","source_restrictions_checked","barrier_ways_checked",
          "native_mask_structural_verdicts","fully_equivalent_native_turn_policy")},indent=2),flush=True)
    if len(restrictions)!=26:
        raise SystemExit("Relation selection incomplete (expected 26 original selected-way relations)")
    if scores["FAIL"]:
        raise SystemExit("Native mask contradicts source no-turn relation; investigate case artifact")


if __name__=="__main__":
    run()
