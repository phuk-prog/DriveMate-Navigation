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
from benchmarks.public_route_preferences import probe_preference_diversity
from engine import RouteNotFound, shortest_route
from engine.route_alternatives import generate_route_candidates
from map_data import OSMImportError, Provenance, import_osm_xml
from map_data.osm_xml import DRIVING_SPEEDS, UNCERTAIN_ROADS

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
MAX_NEIGHBORHOOD_BYTES = 6_000_000
MAX_SOURCE_NEIGHBORHOOD_BYTES = 40_000_000


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
    if len(neighborhood_raw)>MAX_SOURCE_NEIGHBORHOOD_BYTES:
        return None,"public_source_neighborhood_too_large"
    full_root=_parse_public(neighborhood_raw)
    source=_parse_public(restriction_raw)
    # Discard non-drivable map objects before the STRICT 6MB graph import.
    # Keep motorcar road access tags, their connected nodes and barriers, and
    # ALL applicable source restriction relations. No conditions are erased.
    motorways={el.get("id"):el for el in full_root.findall("way") if
               any(t.get("k")=="highway" and t.get("v") in
                   (DRIVING_SPEEDS.keys() | UNCERTAIN_ROADS)
                   for t in el.findall("tag"))}
    used_nodes={n.get("ref") for way in motorways.values() for n in way.findall("nd")}
    all_nodes={el.get("id"):el for el in full_root.findall("node")}
    if None in used_nodes or not used_nodes.issubset(all_nodes):
        return None,"incomplete_motorcar_way_geometry"
    root=ET.Element("osm",{"version":"0.6"})
    for node_id in sorted(used_nodes):
        root.append(deepcopy(all_nodes[node_id]))
    for way_id in sorted(motorways):
        root.append(deepcopy(motorways[way_id]))
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
    profile_routable=0
    multi_candidate=0
    fastest_shortest_divergences=0
    independent_legality_gates_tripped=0
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
            # Route-preference research on the SAME verified-map-input case,
            # keeping incoming-edge context and every imported restriction.
            # Generated paths are explicitly UNVERIFIED by UK road law.
            candidate_set = generate_route_candidates(
                graph, incoming.target, outgoing.target,
                snapshot_id=imported.metadata["source_sha256"],
                incoming_edge_id=in_id,
                max_candidates=6, max_detour_searches=8)
            if not candidate_set:
                raise AssertionError("Mapped routable junction yielded no candidates")
            quickest = next(c for c in candidate_set if "fastest" in c.generated_by)
            shortest = next(c for c in candidate_set if "shortest" in c.generated_by)
            if abs(quickest.route.estimated_seconds-route.estimated_seconds)>1e-7:
                raise AssertionError("Fastest profile contradicts independent mapped Dijkstra")
            for candidate in candidate_set:
                check_prev=in_id
                if candidate.as_unverified_option().independently_verified_legal:
                    raise AssertionError("Public map graph cannot certify UK traffic legality")
                independent_legality_gates_tripped+=1
                for proposed_edge_id in candidate.route.edge_ids:
                    proposed=graph.edges[proposed_edge_id]
                    if proposed.access!="allowed" or (
                            check_prev, proposed_edge_id) in graph.prohibited_turns:
                        raise AssertionError("Profile bypassed a mapped road/turn prohibition")
                    check_prev=proposed_edge_id
                if candidate.route.edge_ids and candidate.route.edge_ids[0]==out_id:
                    raise AssertionError("Profile proposed the target forbidden turn")
            profile_routable+=1
            multi_candidate+=int(len(candidate_set)>1)
            fastest_shortest_divergences+=int(
                quickest.route.edge_ids != shortest.route.edge_ids)
            found+=1
        durations.append(round((perf_counter_ns()-begin)/1e6,5))
    # A second, disjoint sample objective: search a bounded number of other
    # map-graph-origin/destination pairs across this same source-complete
    # neighborhood. Do not mistake OSM semantics for independent road truth.
    captured_cases=[]
    def capture_case(pair_index, source, destination, fastest, shortest,
                     balanced, options):
        from benchmarks.uk_preference_case_register import summarise_discriminating_case
        captured_cases.append(summarise_discriminating_case(
            snapshot, imported.metadata["source_sha256"], pair_index,
            source, destination, fastest, shortest, balanced, options))

    diversity=probe_preference_diversity(
        graph,snapshot_id=imported.metadata["source_sha256"],
        maximum_pairs=48, on_discriminating_case=capture_case)
    from benchmarks.uk_preference_case_register import validate_case_register
    register_validation=validate_case_register(
        captured_cases, expected_count=diversity["fastest_and_shortest_different_path_pairs"])
    return {"status":"map_rule_checked",
            "discriminating_case_register":captured_cases,
            "case_register_sha256":register_validation["case_register_sha256"],
            "case_register_count":register_validation["case_count"],
            "rule_pairs":len(pairs),
            "detours_found":found,
            "no_route_within_buffer":missing,
            "profile_routable_for_restricted_turns":profile_routable,
            "profile_cases_with_multiple_mapped_candidates":multi_candidate,
            "profile_fastest_shortest_different_path_cases":fastest_shortest_divergences,
            "generated_paths_kept_unverified":independent_legality_gates_tripped,
            "neighborhood_comparison_pairs_checked":diversity["map_derived_preference_pairs_checked"],
            "neighborhood_pairs_with_multiple_routes":diversity["map_derived_pairs_with_multiple_routes"],
            "neighborhood_fastest_shortest_divergences":diversity["fastest_and_shortest_different_path_pairs"],
            "neighborhood_distinct_balanced_cases":diversity["balanced_distinct_from_both_pairs"],
            "neighborhood_usable_directed_edges":diversity["network_allowed_directed_edges"],
            "neighborhood_physical_cycle_rank_upper_bound":diversity[
                "network_undirected_cycle_rank_upper_bound"],
            "neighborhood_comparison_coverage":diversity["route_preference_discriminating_coverage"],
            "graph_nodes":len(graph.vertices),
            "graph_edges":len(graph.edges),
            "median_route_compute_ms":sorted(durations)[len(durations)//2],
            "independent_legality":False,
            "full_network_completeness_established":False}


def expanded_bbox(bbox: str) -> str | None:
    """At most one bounded retry. Never broaden a test to a whole city."""
    parts=[float(v) for v in bbox.split(",")]
    if len(parts)!=4 or not all(map(isfinite,parts)):
        raise ValueError("Invalid bbox")
    west,south,east,north=parts
    if not (west<east and south<north):
        raise ValueError("Invalid bbox dimensions")
    lat=(south+north)/2
    lon=(west+east)/2
    radius=max((east-west)/2,(north-south)/2)
    new_radius=min(0.014,round(radius*2,6))
    if new_radius <= round(radius, 6):
        return None
    vals=(lon-new_radius,lat-new_radius,lon+new_radius,lat+new_radius)
    if not (-180<vals[0]<vals[2]<180 and -90<vals[1]<vals[3]<90):
        return None
    return ",".join(f"{v:.6f}" for v in vals)


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
            boxes=[candidate["bbox"]]
            bigger=expanded_bbox(candidate["bbox"])
            if bigger is not None:
                boxes.append(bigger)
            # Retry only when a missing referenced road or neighboring turn
            # relation could be completed by a slightly larger public extract.
            # No exceptions are converted into a passing route.
            record=None
            first_status=None
            attempts=0
            for attempt,bbox in enumerate(boxes):
                attempts+=1
                local_pbf=temp/f"area-{i}-{attempt}.osm.pbf"
                local_xml=temp/f"area-{i}-{attempt}.osm"
                try:
                    runner(("osmium","extract","--strategy","complete_ways",
                            "--bbox",bbox,str(source_pbf),"-o",str(local_pbf)),
                           check=True,timeout=90,stdout=subprocess.DEVNULL)
                    runner(("osmium","cat",str(local_pbf),"-o",str(local_xml),
                            "-f","osm,add_metadata=false"),
                           check=True,timeout=60,stdout=subprocess.DEVNULL)
                    if local_xml.stat().st_size>MAX_SOURCE_NEIGHBORHOOD_BYTES:
                        record={"status":"unsupported","reason":"public_source_neighborhood_too_large",
                                "rule_pairs":0,"detours_found":0,"no_route_within_buffer":0,
                                "independent_legality":False}
                    else:
                        record=evaluate_neighborhood(local_xml.read_bytes(),restriction_raw,
                                   relation_id=candidate["relation_id"],snapshot=snapshot)
                except (subprocess.CalledProcessError,subprocess.TimeoutExpired,OSError):
                    record={"status":"unsupported","reason":"osmium_extraction_failed",
                            "rule_pairs":0,"detours_found":0,"no_route_within_buffer":0,
                            "independent_legality":False}
                if first_status is None:
                    first_status=record["status"]
                if (record.get("reason") not in
                        {"incomplete_neighbor_restriction","missing_target_way_or_via"}):
                    break
            assert record is not None
            record["extraction_attempts"]=attempts
            record["recovered_by_wider_public_buffer"]=(
                first_status=="unsupported" and record["status"]=="map_rule_checked")
            records.append(record)
    return {
        "classification":"real-public-UK-buffered-graph-OSM-rule-only",
        "source_snapshot":snapshot,
        "restriction_source_sha256":sha256(restriction_raw).hexdigest(),
        "proposed_neighborhoods":limit,
        "neighborhoods_prepared":len(records),
        "neighborhoods_with_checked_rules":sum(x["status"]=="map_rule_checked" for x in records),
        "buffer_expansion_retries":sum(x["extraction_attempts"]-1 for x in records),
        "neighborhoods_recovered_with_wider_buffer":sum(x["recovered_by_wider_public_buffer"] for x in records),
        "map_rule_pairs_checked":sum(x["rule_pairs"] for x in records),
        "detours_found_in_bounded_real_road_graph":sum(x["detours_found"] for x in records),
        "profile_routable_restriction_cases":sum(x.get("profile_routable_for_restricted_turns",0)
                                               for x in records),
        "profile_cases_with_multiple_mapped_candidates":sum(
            x.get("profile_cases_with_multiple_mapped_candidates",0) for x in records),
        "profile_fastest_shortest_different_path_cases":sum(
            x.get("profile_fastest_shortest_different_path_cases",0) for x in records),
        "generated_paths_kept_unverified":sum(
            x.get("generated_paths_kept_unverified",0) for x in records),
        "neighborhood_comparison_pairs_checked":sum(
            x.get("neighborhood_comparison_pairs_checked",0) for x in records),
        "neighborhood_pairs_with_multiple_routes":sum(
            x.get("neighborhood_pairs_with_multiple_routes",0) for x in records),
        "neighborhood_fastest_shortest_divergences":sum(
            x.get("neighborhood_fastest_shortest_divergences",0) for x in records),
        "discriminating_case_register": [
            c for x in records for c in x.get("discriminating_case_register",[])],
        "case_register_counts_by_neighborhood": [
            x.get("case_register_count",0) for x in records],
        "case_register_all_cases_have_unknown_legality":all(
            c.get("independent_current_uk_road_legality")=="UNKNOWN"
            for x in records for c in x.get("discriminating_case_register",[])),
        "neighborhood_distinct_balanced_cases":sum(
            x.get("neighborhood_distinct_balanced_cases",0) for x in records),
        "neighborhoods_with_physical_cycles":sum(
            x.get("neighborhood_physical_cycle_rank_upper_bound",0)>0 for x in records),
        "neighbor_preference_comparison_coverage":(
            "MAP_DIVERGENCE_OBSERVED" if any(
                x.get("neighborhood_fastest_shortest_divergences",0)>0 for x in records)
            else "INSUFFICIENT"),
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
