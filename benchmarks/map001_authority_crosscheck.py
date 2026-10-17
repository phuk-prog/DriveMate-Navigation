"""Match one frozen Manchester OSM motorcar direction to independent official guidance.

The council describes King Street's westbound bus gate between Essex Street
and Cross Street. OSM source identity, endpoint/node topology and orientation
are checked before linking evidence to the way. The council page is public
guidance, NOT a supplied signed traffic order or a dated site survey.
"""
from __future__ import annotations
import json
import xml.etree.ElementTree as ET
from benchmarks.map001_graph_fact_audit import ROOT, digest, tags
from benchmarks.map001_category1_closure import SOURCE_SHA_MANCHESTER

COUNCIL_SOURCE = "https://www.manchester.gov.uk/parking/tickets-and-fines/bus-gates/the-king-street-bus-gate"
TARGET = "155729945"
CROSS = "246124643"
ESSEX = "8878437"


def correlate(ways, nodes):
    row = {"source_way": TARGET, "restriction": "ordinary_motorcar_westbound_prohibited",
           "published_authority": "Manchester City Council",
           "evidence_url": COUNCIL_SOURCE,
           "authority_statement": "King Street westbound Essex Street to Cross Street bus gate, 24 hours",
           "independent_evidence_type": "OFFICIAL_PUBLIC_GUIDANCE_NOT_SIGNED_ORDER",
           "current_signage_field_verified": False,
           "traffic_order_text_verified": False,
           "legal_verdict": "PROVISIONAL_AUTHORITY_CORROBORATION_NOT_CERTIFIED"}
    required = [TARGET, CROSS, ESSEX]
    if any(x not in ways for x in required):
        return {**row, "match": "UNRESOLVED", "reason": "source_way_missing"}
    a, cross, essex = (ways[wid] for wid in required)
    if [tags(w).get("name") for w in (a,cross,essex)] != [
            "King Street", "Cross Street", "Essex Street"]:
        return {**row, "match": "UNRESOLVED", "reason": "street_identity_changed"}
    refs = [n.get("ref") for n in a.findall("nd")]
    cr = {n.get("ref") for n in cross.findall("nd")}
    es = {n.get("ref") for n in essex.findall("nd")}
    if len(refs) < 2 or refs[0] not in cr or refs[-1] not in es:
        return {**row, "match": "UNRESOLVED", "reason": "junction_endpoint_mismatch"}
    if any(r not in nodes for r in refs):
        return {**row, "match": "UNRESOLVED", "reason": "source_nodes_missing"}
    west_lon = float(nodes[refs[0]].get("lon"))
    east_lon = float(nodes[refs[-1]].get("lon"))
    if not west_lon < east_lon:
        return {**row, "match": "UNRESOLVED", "reason": "reverse_direction_not_westbound"}
    if tags(a).get("vehicle:backward") != "no":
        return {**row, "match": "UNRESOLVED", "reason": "source_car_access_changed"}
    return {**row, "match": "MATCHED_SOURCE_WAY_DIRECTION_TO_COUNCIL_DESCRIPTION",
            "backward_direction": "east-to-west Essex Street to Cross Street",
            "source_start_junction": "Cross Street",
            "source_end_junction": "Essex Street",
            "source_start_node": refs[0],
            "source_end_node": refs[-1],
            "source_source_tag": "vehicle:backward=no",
            "public_page_claims_bus_taxi_cycle_exceptions": True,
            "motorcar_access_correlated": "PROHIBITED_WESTBOUND",
            "unverified": ("Physical signs, effective legal order, exceptions, "
                           "historic snapshot date, and field survey not confirmed")}


def run():
    raw = (ROOT/"map001-manchester.osm").read_bytes()
    manifest = json.loads((ROOT/"map001-v3-manifest.json").read_text())
    expected = next(x["source_sha256"] for x in manifest["areas"] if x["area"]=="manchester")
    if digest(raw) != expected or expected != SOURCE_SHA_MANCHESTER:
        raise ValueError("Frozen Manchester case changed")
    src = ET.fromstring(raw)
    ways = {w.get("id"):w for w in src.findall("way")}
    nodes = {n.get("id"):n for n in src.findall("node")}
    matched = correlate(ways,nodes)
    result = {"trial": "MAP-001-OFFICIAL-UK-EVIDENCE-1",
              "frozen_source_sha256":expected,
              "authority_page_checked_by_research": "2026-10-16",
              "authority_page_revalidated_live_by_ci":False,
              "case":matched,
              "full_uk_road_legality_ranking": None,
              "source_osm_copyright": "OpenStreetMap contributors; ODbL"}
    (ROOT/"map001-official-manchester.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"trial":result["trial"],"case":matched["source_way"],
                      "match":matched["match"],
                      "legal_verdict":matched["legal_verdict"]},indent=2))
    if matched["match"] != "MATCHED_SOURCE_WAY_DIRECTION_TO_COUNCIL_DESCRIPTION":
        raise SystemExit("Official guidance cannot be linked to this source without review")


if __name__=="__main__":
    run()
