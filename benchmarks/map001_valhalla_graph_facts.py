"""Bounded Valhalla 3.9.1 graph metadata study using v3 frozen Manchester OSM.

These are /locate *candidate* directed edge observations, not a complete graph
walk or exact (arrival edge, departure edge) motorcar-turn restriction oracle.
Fail/report absent fields instead of manufacturing a full graph ranking.
"""
from __future__ import annotations
from collections import Counter
import json
from urllib.request import Request,urlopen
import xml.etree.ElementTree as ET
from benchmarks.map001_graph_fact_audit import ROOT,digest,tags
from benchmarks.map001_valhalla_locate import way_midpoint, LOCATE_URL
from benchmarks.map001_v3 import FROZEN_V2_IDS


def expected_direction(t,forward):
    """Use the prospective source contract; keep original reports unchanged."""
    from benchmarks.map001_direction_contract import direction_access
    return direction_access(t, forward)


def summarize_way(wid,located,source_way):
    matches=[]
    for e in located.get("edges",[]) if isinstance(located,dict) else []:
        if not isinstance(e,dict):
            continue
        info=e.get("edge_info")
        value=e.get("way_id")
        if value is None and isinstance(info,dict):
            value=info.get("way_id")
        if str(value)!=wid:continue
        item=e.get("edge") if isinstance(e.get("edge"),dict) else {}
        permission=item.get("access",{})
        car=permission.get("car") if isinstance(permission,dict) else None
        forward=item.get("forward")
        start=item.get("start_restriction",{})
        end=item.get("end_restriction",{})
        restriction_mask={
          "start_car":start.get("car") if isinstance(start,dict) else None,
          "end_car":end.get("car") if isinstance(end,dict) else None,
          "edge_access_restriction":item.get("access_restriction"),
          "simple_turn_mask":item.get("restrictions"),
          "local_edge_index":item.get("local_edge_index"),
          "opposing_edge_index":item.get("opp_index"),
          "destination_only":item.get("destination_only"),
          "not_thru":item.get("not_thru"),
          "part_of_complex_restriction":item.get("part_of_complex_restriction"),
          "access_restrictions_count":len(e["access_restrictions"]) if isinstance(
             e.get("access_restrictions"),list) else None}
        expected=expected_direction(tags(source_way),forward) if type(forward) is bool else "unknown"
        verdict=("UNKNOWN_EDGE_SCHEMA" if type(car) is not bool or type(forward) is not bool
              else "SOURCE_DIRECTION_CONTRADICTION" if expected=="prohibited" and car
              else "MATCHES_EXPLICIT_DENIAL" if expected=="prohibited" and not car
              else "POLICY_CONTEXT_NOT_BINARY" if expected=="contextual"
              else "SOURCE_DIRECTION_VISIBLE" if expected=="allowed" and car
              else "UNKNOWN_OR_OTHER_RESTRICTION")
        matches.append({"forward":forward,"car_access":car,"source_expected":expected,
                        "verdict":verdict, "turn_mask_observation":restriction_mask,
                        "edge_graph_id":e.get("edge_id",{}).get("value") if isinstance(
                              e.get("edge_id"),dict) else None,
                        "end_node_graph_id":item.get("end_node",{}).get("value") if isinstance(
                              item.get("end_node"),dict) else None})
    # Local snapping provides no proof that unreturned source edges don't exist.
    return {"case_id":"manchester-"+wid, "sampled_candidates":len(matches),
            "graph_way_visible":bool(matches),
            "directed_candidate_schema_available":any(
                type(x["forward"]) is bool and type(x["car_access"]) is bool for x in matches),
            "source_contradiction_candidates":sum(x["verdict"]=="SOURCE_DIRECTION_CONTRADICTION"
                                                 for x in matches),
            "contextual_candidate_count":sum(x["verdict"]=="POLICY_CONTEXT_NOT_BINARY"
                                            for x in matches),
            "candidates":matches, "turn_pairs_comparable":False}


def request_batches(locations,size=4):
    if not 1<=size<=4:raise ValueError("Maximum four locations per request")
    rows=[]
    for i in range(0,len(locations),size):
        batch=locations[i:i+size]
        body=json.dumps({"costing":"auto","verbose":True,"locations":batch},
                        separators=(",",":")).encode()
        if len(body)>10000:raise ValueError("Request larger than 10 KB")
        req=Request(LOCATE_URL,data=body,headers={"Content-Type":"application/json"},
                    method="POST")
        with urlopen(req,timeout=30) as res:
            raw=res.read(500001)
        if len(raw)>500000:raise ValueError("Response larger than 500KB")
        part=json.loads(raw)
        if not isinstance(part,list) or len(part)!=len(batch):
            raise ValueError("Unexpected Valhalla graph metadata schema")
        rows.extend(part)
    if len(rows)!=len(locations):
        raise ValueError("Incomplete Valhalla case coverage")
    return rows


def main():
    manifest=json.loads((ROOT/"map001-v3-manifest.json").read_text())
    expected=next(x["source_sha256"] for x in manifest["areas"] if x["area"]=="manchester")
    raw=(ROOT/"map001-manchester.osm").read_bytes()
    if digest(raw)!=expected:raise ValueError("Non-identical source snapshot")
    root=ET.fromstring(raw)
    ways={w.get("id"):w for w in root.findall("way")}
    nodes={n.get("id"):n for n in root.findall("node")}
    wanted=FROZEN_V2_IDS["manchester"]
    if any(x not in ways for x in wanted):raise ValueError("Original source way absent")
    locations=[way_midpoint(ways[wid],nodes) for wid in wanted]
    returned=request_batches(locations)
    cases=[summarize_way(wid,data,ways[wid]) for wid,data in zip(wanted,returned)]
    counts=Counter({"way_visible":sum(x["graph_way_visible"] for x in cases),
                    "directed_access_schema":sum(x["directed_candidate_schema_available"]
                                                 for x in cases),
                    "source_contradiction_candidates":sum(x["source_contradiction_candidates"]
                                                         for x in cases),
                    "contextual_candidate_count":sum(x["contextual_candidate_count"]
                                                    for x in cases)})
    report={"trial":"MAP-001-V3-VALHALLA-GRAPH-FACTS",
       "engine":"Valhalla 3.9.1, locally imported frozen OSM",
       "source_sha256":expected,"cases_total":len(cases),"counts":dict(counts),
       "evidence":"PROVISIONAL_OSM_SOURCE_GRAPH_CANDIDATES",
       "car_access_flag_not_equivalent_to_private_or_destination_permission":True,
       "policy_context_status":"NOT_SCORED_AS_WRONG_OR_CORRECT",
       "graph_coverage":"SPATIAL_SAMPLE_NOT_EXHAUSTIVE_DIRECTED_EDGES",
       "complete_turn_pair_exposure":False,
       "turn_mask_interpretation":"per-edge flags only; no relation-level pair legality",
       "full_category1_ranking":None,
       "candidate_graph_ids_available":sum(x["edge_graph_id"] is not None
           for c in cases for x in c["candidates"]),
       "candidate_end_node_ids_available":sum(x["end_node_graph_id"] is not None
           for c in cases for x in c["candidates"]),
       "simple_turn_masks_available":sum(x["turn_mask_observation"]["simple_turn_mask"] is not None
           for c in cases for x in c["candidates"]),
       "missing_edge_detection":"UNSUPPORTED_SPATIAL_SAMPLING",
       "native_tile_adapter":"NOT_IMPLEMENTED_REQUIRES_GRAPHREADER_AND_PROFILE_RULES",
       "cases":cases}
    (ROOT/"map001-v3-valhalla-graph-facts.json").write_text(
        json.dumps(report,indent=2)+"\n")
    print(json.dumps({"trial":report["trial"],"counts":report["counts"],
                     "fully_comparable_turn_pairs":False},indent=2))
    if counts["way_visible"]==0:
        raise SystemExit("No correlated way IDs; adapter unsupported")
if __name__=="__main__":
    main()
