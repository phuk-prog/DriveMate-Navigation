"""MAP-001: all 34 withheld ordinary-motorcar access ways + 7 timed ways.

Execute DMN's *actual* frozen OSM importer/route gate on the exact originally
selected six UK regions. Context assertions are test inputs, not a grant
of road-law entitlement. Never rewrite frozen source or engine permissions.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from benchmarks.map001_graph_fact_audit import ROOT, AREAS, digest, isolated, source, tags
from benchmarks.map001_v3 import FROZEN_V2_IDS
from benchmarks.map001_category1_closure import audit_way
from benchmarks.map001_conditional_research import parse_source, UK
from map_data import JourneyAccessContext, OSMImportError, Provenance, import_osm_xml
from engine.routing import RouteNotFound, shortest_route

MODE_KEYS = ("motorcar", "motor_vehicle", "vehicle", "access")
CONTEXTUAL = {"private": "OWNER_AUTHORIZATION",
              "destination": "QUALIFYING_JOURNEY_DESTINATION",
              "permit": "AUTHORITY_ISSUED_WAY_PERMISSION"}
EXPECTED_FAMILIES = {"UNSPECIFIED_SERVICE": 14, "OWNER_AUTHORIZATION": 9,
                     "QUALIFYING_JOURNEY_DESTINATION": 8,
                     "AUTHORITY_ISSUED_WAY_PERMISSION": 2,
                     "UNKNOWN_PHYSICAL_GATE": 1}
EXPECTED_CONDITIONAL = {"glasgow": 2, "belfast": 5}
EXPECTED_SOURCE_SHA = {
    "manchester": "34438baa7a28c55958cd5ba7ac3909a551c51197911963364d27a26eefe8973a",
    "birmingham": "247e476db82b05a0058426eca28be70a8b46d1ff61124f07a495fa7f8f5b5143",
    "carlisle": "c61e5e60a41522eb0082b9d3492bb8c0c7a35bb4619592f67b83173ff9581bcb",
    "cardiff": "f29485925412a371accce5988db014a14921ec6c69b060202dba3d8fb59efc3a",
    "glasgow": "75f81359413bdf2f9000aaaa4bcefe225a3aed7be6fce423ba7a05a2fc225660",
    "belfast": "adb098fd26fb9e9e3e44872642ec30823682b91862999a48732b3c3ceb300900",
}
# Public council guidance supports existence of relevant *schemes*, not legal
# permission for a specific frozen OSM edge. None are signed-order or field proof.
AUTHORITY_RESEARCH = {
 "birmingham": {
  "url": "https://www.birmingham.gov.uk/directory_record/136446/moor_street_queensway_outside_moor_street_station",
  "scope": "Moor Street Queensway bus gate only; distinct source-way extent not established"},
 "cardiff": {
  "url": "https://www.cardiff.gov.uk/trafficaccesspermits",
  "scope": "Council permit programme; no selected-way entitlement independently verified"},
 "belfast": {
  "url": "https://www.nidirect.gov.uk/articles/pedestrian-zone-permits",
  "scope": "Pedestrian zone exceptions; delivery, badge and street extent are vehicle-specific"},
 "glasgow": {
  "url": "https://onlineservices.glasgow.gov.uk/CouncillorsandCommittees/viewSelectedDocument.asp?c=P62AFQDNUTDNDN0G2U",
  "scope": "Published People First Zone plans; completion and legal effective date unresolved"},
}


def source_family(way, nodes):
    t=tags(way)
    # Explicit motorcar > motor_vehicle > vehicle > general access, matching
    # source-mode selection; only the source *reason*, not a legal verdict.
    value=next((t[k] for k in MODE_KEYS if k in t), None)
    if value in CONTEXTUAL:
        return CONTEXTUAL[value]
    if value is None and t.get("highway") in {"service", "track"}:
        return "UNSPECIFIED_SERVICE"
    refs=[n.get("ref") for n in way.findall("nd")]
    if value is None and any(
        tags(nodes[n]).get("barrier") in {"gate", "lift_gate", "swing_gate", "cattle_grid"}
        for n in refs):
        return "UNKNOWN_PHYSICAL_GATE"
    return "UNCLASSIFIED_UNCERTAINTY"


def base_verdict(loaded):
    states=Counter(x.access for x in loaded.graph.edges.values())
    return "SAFE_WITHHELD" if states and states["unknown"] and not states["allowed"] else "REVIEW",dict(states)


def scenario(way, nodes, area, family):
    wid=way.get("id")
    raw=isolated(way,nodes)
    sha=digest(raw)
    p=Provenance(area,"frozen v3 selected public OSM", "MAP-001 source-context audit",
                 "OpenStreetMap contributors; ODbL")
    default=import_osm_xml(raw, provenance=p)
    verdict,base_states=base_verdict(default)
    # An assertion for a different way must NEVER unlock this one.
    unrelated=JourneyAccessContext(sha,authorized_way_ids=frozenset({"99999999999999999"}),
                                   destination_way_ids=frozenset({"99999999999999999"}),
                                   destination_node="osm:"+way.findall("nd")[-1].get("ref"))
    # The real importer rightly rejects missing IDs before constructing a
    # journey view. Rejection is stronger evidence than an unchanged graph.
    wrong=None
    rejected_unrelated=False
    try:
        wrong=import_osm_xml(raw,provenance=p,access_context=unrelated)
    except OSMImportError as exc:
        rejected_unrelated="absent source objects" in str(exc)
        if not rejected_unrelated:
            raise
    wrong_states=(Counter(e.access for e in wrong.graph.edges.values())
                  if wrong is not None else Counter())
    wrong_safe=(not any(x.access=="allowed" for x in wrong.graph.edges.values())
                if wrong is not None else rejected_unrelated)
    if family=="QUALIFYING_JOURNEY_DESTINATION":
        destination="osm:"+way.findall("nd")[-1].get("ref")
        ctx=JourneyAccessContext(sha,destination_node=destination,
                                 destination_way_ids=frozenset({wid}))
        contextual_label="HYPOTHETICAL_MATCHED_JOURNEY_DESTINATION"
        expected="allowed"
    else:
        ctx=JourneyAccessContext(sha,authorized_way_ids=frozenset({wid}))
        contextual_label=("HYPOTHETICAL_MATCHED_WAY_PERMISSION"
                          if family=="OWNER_AUTHORIZATION"
                          else "PERMISSION_CANNOT_INVENT_UNMAPPED_AUTHORIZATION")
        expected="allowed" if family=="OWNER_AUTHORIZATION" else "unknown"
    contextual=import_osm_xml(raw,provenance=p,access_context=ctx)
    contextual_states=Counter(e.access for e in contextual.graph.edges.values())
    # The importer supports private/destination evidence only, not general
    # permit traffic orders; a test assertion is never proof of real permission.
    context_correct=all(e.access==expected or e.access=="prohibited"
                        for e in contextual.graph.edges.values())
    if family in ("OWNER_AUTHORIZATION","QUALIFYING_JOURNEY_DESTINATION"):
        context_correct=context_correct and contextual_states["allowed"]>0
    else:
        context_correct=context_correct and contextual_states["allowed"]==0
    default_unchanged=all(e.access==default.graph.edges[k].access
                          for k,e in import_osm_xml(raw,provenance=p).graph.edges.items())
    start="osm:"+way.findall("nd")[0].get("ref")
    end="osm:"+way.findall("nd")[-1].get("ref")
    def routed(graph):
        try:
            result=shortest_route(graph,start,end)
            return bool(result.edge_ids)
        except RouteNotFound:
            return False
    baseline_route=routed(default.graph)
    wrong_route=routed(wrong.graph) if wrong is not None else False
    contextual_route=routed(contextual.graph)
    route_contract=not baseline_route and not wrong_route and (
        contextual_route if expected=="allowed" else not contextual_route)
    return {"source_way":wid,"family":family,
            "isolated_input_sha256":sha,"source_highway":tags(way).get("highway"),
            "selected_mode_tags":{k:tags(way)[k] for k in MODE_KEYS if k in tags(way)},
            "baseline_states":base_states, "baseline_policy":verdict,
            "unrelated_context_states":dict(wrong_states),
            "unrelated_context_input_rejected":rejected_unrelated,
            "unrelated_context_graph_created":wrong is not None,
            "unrelated_context_safely_withheld":wrong_safe,
            "matched_scenario":contextual_label,
            "matched_scenario_states":dict(contextual_states),
            "matched_scenario_matches_supported_engine_policy":context_correct,
            "original_source_and_unscoped_import_unchanged":default_unchanged,
            "actual_route_search_observation":{"default_can_route":baseline_route,
                "unrelated_context_can_route":wrong_route,
                "hypothetical_matched_can_route":contextual_route},
            "route_safety_gate_pass":route_contract,
            "legal_permission_proven":False, "current_road_legality":"NOT_JUDGED",
            "competitor_profile_equivalence":"UNSUPPORTED"}


def conditioned_way(way, nodes, area):
    wid=way.get("id");t=tags(way)
    expressions={k:v for k,v in t.items() if k.endswith(":conditional")}
    if not expressions:
        raise ValueError("Expected frozen conditional way missing its expression")
    raw=isolated(way,nodes)
    p=Provenance(area,"frozen v3","conditional research only","OpenStreetMap contributors; ODbL")
    rejected=False
    try:
        import_osm_xml(raw,provenance=p)
    except OSMImportError as e:
        rejected="conditional" in str(e).lower()
    observations=[]
    for k,expr in sorted(expressions.items()):
        cond=parse_source(expr)
        observations.append({
         "tag":k,"source_expression":expr,
         "qualified_value":cond.value,
         "source_interval_local_minutes":[cond.start,cond.end],
         "instants_utc": [{
          "utc":utc.isoformat(),
          "local":utc.astimezone(UK).isoformat(),
          "source_expression_active":cond.active(utc.astimezone(UK))}
          for utc in (datetime(2026,1,15,8,tzinfo=timezone.utc),
                      datetime(2026,7,15,8,tzinfo=timezone.utc),
                      datetime(2026,10,14,12,tzinfo=timezone.utc),
                      datetime(2026,10,14,20,tzinfo=timezone.utc))],
         "ordinary_motorcar_legal_permission": "NOT_ESTABLISHED",
         "legal_date_or_signed_order_verified":False})
    return {"source_way":wid,"source_way_name":t.get("name"),
            "source_sha256":digest(raw),
            "always_safe_import_rejection":rejected,
            "expressions":observations,
            "current_road_legality":"NOT_JUDGED",
            "scope":"SOURCE_CLOCK_SYNTAX_ONLY_NO_ROUTING_OVERRIDE"}


def run():
    manifest=json.loads((ROOT/"map001-v3-manifest.json").read_text())
    if [x["area"] for x in manifest["areas"]] != list(AREAS):
        raise ValueError("Six original regions missing or reordered")
    contextual=[];conditional=[]
    for spec in manifest["areas"]:
        area=spec["area"]
        raw,nodes,ways,_=source(ROOT/("map001-"+area+".osm"))
        if digest(raw)!=spec["source_sha256"] or digest(raw)!=EXPECTED_SOURCE_SHA[area]:
            raise ValueError("Non-frozen UK map input for "+area)
        if [x["way"] for x in spec["cases"]]!=FROZEN_V2_IDS[area]:
            raise ValueError("Original 120-way ID cohort changed")
        rels=ET.fromstring(raw).findall("relation")
        for wid in FROZEN_V2_IDS[area]:
            existing=audit_way(area,wid,ways,nodes,rels)
            if existing["verdict"]!="SAFE_WITHHELD":
                continue
            way=ways[wid]
            if existing["reason"]=="unknown_access_not_road_law":
                row=scenario(way,nodes,area,source_family(way,nodes))
                row.update({"area":area,"original_verdict":"SAFE_WITHHELD",
                            "official_reference":AUTHORITY_RESEARCH.get(area),
                            "official_covers_exact_way_and_time":False})
                contextual.append(row)
            elif existing["reason"]=="conditional_source_requires_vehicle_time_policy":
                row=conditioned_way(way,nodes,area)
                row.update({"area":area,"original_verdict":"SAFE_WITHHELD",
                            "official_reference":AUTHORITY_RESEARCH.get(area),
                            "official_covers_exact_way_and_time":False})
                conditional.append(row)
            else:
                raise ValueError("New safety-unknown category: "+existing["reason"])
    if len(contextual)!=34 or len(conditional)!=7:
        raise ValueError("Unchanged withheld cohort required (34 and 7)")
    families=Counter(x["family"] for x in contextual)
    if dict(families)!=EXPECTED_FAMILIES:
        raise ValueError("Access-source reason taxonomy drift")
    condition_regions=Counter(x["area"] for x in conditional)
    if dict(condition_regions)!=EXPECTED_CONDITIONAL:
        raise ValueError("Conditional selection drift")
    failures=[x for x in contextual
              if (x["baseline_policy"]!="SAFE_WITHHELD"
                  or not x["unrelated_context_safely_withheld"]
                  or not x["matched_scenario_matches_supported_engine_policy"]
                  or not x["route_safety_gate_pass"]
                  or not x["original_source_and_unscoped_import_unchanged"])]
    failures.extend(x for x in conditional if not x["always_safe_import_rejection"])
    report={"trial":"MAP-001-ALL-41-WITHHELD-ACCESS-1",
            "cases_total":41,"unknown_access_cases":contextual,"conditional_access_cases":conditional,
            "source_family_counts":dict(families),"conditional_region_counts":dict(condition_regions),
            "policy_control_pass":41-len(failures),"policy_control_fail":len(failures),
            "legal_correctness_pass":0,"independently_authorized_access":0,
            "road_law_verdict":"ALL_41_STILL_REQUIRE_CASE_SPECIFIC_INDEPENDENT_EVIDENCE",
            "permission_assertions_in_tests_only":True,
            "dmn_runtime_changed":False,
            "comparable_native_graph_oracle":"NOT_ESTABLISHED_FOR_CONTEXTUAL_PROFILES",
            "failures":failures,
            "evidence_level":"ARCHIVED_OSM_TAGS_AND_REAL_DMN_IMPORTER_POLICY",
            "frozen_source_sha256":EXPECTED_SOURCE_SHA}
    (ROOT/"map001-remaining-access.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in
        ("trial","cases_total","source_family_counts","conditional_region_counts",
         "policy_control_pass","policy_control_fail","legal_correctness_pass")},indent=2),flush=True)
    if failures:
        raise SystemExit("DMN safety regression in withheld-context cohort")


if __name__=="__main__":
    run()
