"""Bounded real UK street-NEIGHBORHOOD detours around mapped turn restrictions.

Independent public OSM snapshot, NEVER a user's route. No remote navigation API.
This tests graph interpretation and legal-alternative *according to OSM only*.
It does NOT certify independent UK legal truth or full-network reachability.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import subprocess
import tempfile
from time import perf_counter_ns
import xml.etree.ElementTree as ET

from benchmarks.real_uk_turn_probe import _eligible, _public_input
from engine import RouteNotFound, shortest_route
from map_data import OSMImportError, Provenance, import_osm_xml

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
MAX_NEIGHBORHOOD_BYTES = 6_000_000


def _parse_public(raw: bytes) -> ET.Element:
    if not raw or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("Refusing unsafe public XML")
    root = ET.fromstring(raw)
    if root.tag != "osm":
        raise ValueError("Expected public OSM root")
    for obj in root.iter():
        if obj.tag in {"node", "way", "relation"} and (
                {"user", "uid", "changeset"} & obj.attrib.keys()):
            raise ValueError("Contributor metadata not permitted")
    return root


def find_candidates(source_raw: bytes, *, limit: int=4,
                    radius_deg: float=0.007) -> list[dict]:
    """Select stable public restriction cases, not a driver-provided location."""
    if not 1 <= limit <= 12 or not 0.002 <= radius_deg <= 0.015:
        raise ValueError("Invalid sample size or public-neighborhood radius")
    root = _parse_public(source_raw)
    nodes = {e.get("id"):e for e in root.findall("node")}
    ways = {e.get("id") for e in root.findall("way")}
    cases=[]
    selected_nodes=set()
    for relation in root.findall("relation"):
        if not _eligible(relation):
            continue
        members=relation.findall("member")
        via=next(m.get("ref") for m in members if m.get("role")=="via")
        frm=next(m.get("ref") for m in members if m.get("role")=="from")
        to=next(m.get("ref") for m in members if m.get("role")=="to")
        if via in selected_nodes or via not in nodes or frm not in ways or to not in ways:
            continue
        try:
            lat=float(nodes[via].attrib["lat"])
            lon=float(nodes[via].attrib["lon"])
        except (ValueError,KeyError):
            continue
        if not all(map(isfinite,(lat,lon))) or not -90<lat<90 or not -180<lon<180:
            continue
        west,south,east,north = lon-radius_deg,lat-radius_deg,lon+radius_deg,lat+radius_deg
        if not(-180 < west < east < 180 and -90 < south < north < 90):
            continue
        cases.append({"relation_id":relation.get("id"),"via_id":via,
                      "bbox":",".join(f"{c:.6f}" for c in (west,south,east,north))})
        selected_nodes.add(via)
        if len(cases)>=limit:
            break
    return cases


def _compile_neighborhood(neighborhood_raw: bytes, restriction_raw: bytes,
                          *, target_relation_id: str, snapshot: str):
    """Add all known applicable restrictions; decline unsafe/partial subsets."""
    root=_parse_public(neighborhood_raw)
    source=_parse_public(restriction_raw)
    target=next((r for r in source.findall("relation")
                 if r.get("id")==target_relation_id),None)
    if target is None or not _eligible(target):
        return None,"target_not_supported"
    nodes={el.get("id") for el in root.findall("node")}
    ways={el.get("id") for el in root.findall("way")}
    members=target.findall("member")
    if any((m.get("ref") not in (ways if m.get("type")=="way" else nodes))
           for m in members):
        return None,"missing_target_way_or_via"
    for relation in source.findall("relation"):
        tags={t.get("k"):t.get("v") for t in relation.findall("tag")}
        if tags.get("type")!="restriction":
            continue
        from_ways={m.get("ref") for m in relation.findall("member")
                   if m.get("role")=="from" and m.get("type")=="way"}
        # Check all known restrictions for roads that may be entered in this
        # neighborhood. Missing to/via objects could change legal outcomes.
        if not from_ways.intersection(ways):
            continue
        from_nodes={m.get("ref") for m in relation.findall("member")
                    if m.get("role")=="via" and m.get("type")=="node"}
        if from_nodes and not from_nodes.intersection(nodes):
            continue
        if any((m.get("ref") not in (ways if m.get("type")=="way" else nodes))
               for m in relation.findall("member")
               if m.get("type") in ("way","node")):
            return None,"incomplete_neighbor_restriction"
        # Conditional/via-way rules: existing importer rejects whole sample,
        # conservatively. Do not silently remove road restrictions.
        root.append(deepcopy(relation))
    raw=ET.tostring(root,encoding="utf-8",xml_declaration=True)
    if len(raw)>MAX_NEIGHBORHOOD_BYTES:
        return None,"prototype_graph_too_large"
    try:
        imported=import_osm_xml(raw,provenance=Provenance(
            "public UK buffered road neighborhood",snapshot,
            "Geofabrik-public-extract","© OpenStreetMap contributors"))
    except (OSMImportError,ValueError):
        return None,"unsupported_graph_or_restriction"
    target_members={m.get("role"):m.get("ref") for m in members}
    target_via="osm:"+target_members["via"]
    frm_way=target_members["from"]
    to_way=target_members["to"]
    pair_list=[]
    for a,b in sorted(imported.graph.prohibited_turns):
        e1,e2=imported.graph.edges[a],imported.graph.edges[b]
        if (e1.target==target_via and e2.source==target_via and
            a.split(":")[1]==frm_way and b.split(":")[1]==to_way and
            e1.access=="allowed" and e2.access=="allowed"):
            pair_list.append((a,b))
    if not pair_list:
        return None,"target_rule_not_applicable_to_motorcar"
    return (imported,pair_list),"ok"


def evaluate_neighborhood(neighborhood_raw: bytes, restriction_raw: bytes,
                          *, relation_id: str, snapshot: str) -> dict:
    """Classify graph-limited detours, with all unproved conditions UNKNOWN."""
    outcome,reason=_compile_neighborhood(neighborhood_raw,restriction_raw,
                              target_relation_id=relation_id,snapshot=snapshot)
    if outcome is None:
        return {"status":"unsupported","reason":reason,"rule_pairs":0,
                "detours_found":0,"no_route_within_buffer":0,
                "independent_legality":False}
    imported,pairs=outcome
    graph=imported.graph
    found=0
    missing=0
    durations=[]
    for in_id,out_id in pairs:
        incoming,outgoing=graph.edges[in_id],graph.edges[out_id]
        begin=perf_counter_ns()
        try:
            route=shortest_route(graph,incoming.target,outgoing.target,
                                 incoming_edge_id=in_id)
        except RouteNotFound:
            missing+=1
        else:
            if not route.edge_ids:
                raise AssertionError("Nontrivial target after turn has empty route")
            prev=in_id
            for eid in route.edge_ids:
                edge=graph.edges[eid]
                if edge.access!="allowed" or (prev,eid) in graph.prohibited_turns:
                    raise AssertionError("Detour violated imported OSM road graph restriction")
                prev=eid
            if route.edge_ids[0]==out_id:
                raise AssertionError("Selected mapped forbidden turn as first action")
            found+=1
        durations.append(round((perf_counter_ns()-begin)/1e6,5))
    return {"status":"map_rule_checked",
            "rule_pairs":len(pairs),
            "detours_found":found,
            "no_route_within_buffer":missing,
            "graph_nodes":len(graph.vertices),
            "graph_edges":len(graph.edges),
            "median_route_compute_ms":sorted(durations)[len(durations)//2],
            "independent_legality":False,
            "full_network_completeness_established":False}


def execute_public_neighborhoods(source_pbf: Path, restriction_xml: Path,
                                 *, snapshot: str, limit: int=4,
                                 radius_deg: float=0.007,
                                 runner=subprocess.run) -> dict:
    """Offline, ephemeral Osmium subgraphs with cautious fail-closed classification."""
    if not source_pbf.name.endswith(".osm.pbf") or not source_pbf.is_file():
        raise ValueError("Expected public OSM PBF")
    restriction_raw=_public_input(restriction_xml)
    candidates=find_candidates(restriction_raw,limit=limit,radius_deg=radius_deg)
    records=[]
    with tempfile.TemporaryDirectory(prefix="public-uk-neighborhood-",dir=RESULTS) as directory:
        temp=Path(directory)
        for i,candidate in enumerate(candidates):
            local_pbf=temp/f"area-{i}.osm.pbf"
            local_xml=temp/f"area-{i}.osm"
            try:
                runner(("osmium","extract","--strategy","complete_ways",
                        "--bbox",candidate["bbox"],
                        str(source_pbf),"-o",str(local_pbf)),
                       check=True,timeout=90,stdout=subprocess.DEVNULL)
                runner(("osmium","cat",str(local_pbf),"-o",str(local_xml),
                        "-f","osm,add_metadata=false"),
                       check=True,timeout=60,stdout=subprocess.DEVNULL)
                if local_xml.stat().st_size>MAX_NEIGHBORHOOD_BYTES:
                    record={"status":"unsupported","reason":"prototype_graph_too_large",
                            "rule_pairs":0,"detours_found":0,"no_route_within_buffer":0,
                            "independent_legality":False}
                else:
                    record=evaluate_neighborhood(local_xml.read_bytes(),restriction_raw,
                               relation_id=candidate["relation_id"],snapshot=snapshot)
            except (subprocess.CalledProcessError,subprocess.TimeoutExpired,OSError):
                record={"status":"unsupported","reason":"osmium_extraction_failed",
                        "rule_pairs":0,"detours_found":0,"no_route_within_buffer":0,
                        "independent_legality":False}
            records.append(record)
    return {
        "classification":"real-public-UK-buffered-graph-OSM-rule-only",
        "source_snapshot":snapshot,
        "restriction_source_sha256":sha256(restriction_raw).hexdigest(),
        "proposed_neighborhoods":limit,
        "neighborhoods_prepared":len(records),
        "neighborhoods_with_checked_rules":sum(x["status"]=="map_rule_checked" for x in records),
        "map_rule_pairs_checked":sum(x["rule_pairs"] for x in records),
        "detours_found_in_bounded_real_road_graph":sum(x["detours_found"] for x in records),
        "no_route_in_bounded_graph_unknown":sum(x["no_route_within_buffer"] for x in records),
        "unsupported_or_incomplete_neighborhoods":sum(x["status"]=="unsupported" for x in records),
        "unsupported_reasons":{k:sum(x.get("reason")==k for x in records)
                               for k in sorted({x.get("reason") for x in records if x.get("reason")})},
        "independent_road_legality_verified":False,
        "full_road_network_completeness_verified":False,
        "real_phone_GPS_tested":False,
        "external_engines_executed":0,
        "navigation_score":None,
        "caveat":"OSM-mapped motorcar rule adherence and found detours in bounded graphs, not verified real UK legal routing or global no-route truth."
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--pbf",type=Path,required=True)
    p.add_argument("--restriction-source",type=Path,required=True)
    p.add_argument("--snapshot",required=True)
    p.add_argument("--limit",type=int,default=4)
    p.add_argument("--radius-deg",type=float,default=0.007)
    args=p.parse_args()
    print(json.dumps(execute_public_neighborhoods(args.pbf,args.restriction_source,
              snapshot=args.snapshot,limit=args.limit,radius_deg=args.radius_deg),indent=2))


if __name__=="__main__":
    main()
