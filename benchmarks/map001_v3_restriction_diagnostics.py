"""MAP-001 v3 follow-up: frozen Manchester restriction viability diagnostics.

Only reads the archived v3 OSM snapshot. Does NOT alter the DMN importer or
navigation decisions. Source-tag interpretations are PROVISIONAL, not UK law.
"""
from __future__ import annotations
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from benchmarks.map001_graph_fact_audit import ROOT, digest, tags, isolated
from benchmarks.map001_v2 import access, barrier, merge, related
from map_data import import_osm_xml, Provenance, OSMImportError

TARGETS = ("155729945", "246124643")
VEHICLE_KEYS = ("motorcar", "motor_vehicle", "vehicle", "access")
YES = {"yes", "designated", "permissive"}
NO = {"no", "private", "agricultural", "forestry", "delivery",
      "destination", "customers", "permit"}


def explicit_direction(t, direction):
    """Only categorical directional motor-vehicle tags; unknowns remain UNKNOWN."""
    for key in VEHICLE_KEYS:
        val = t.get(key + ":" + direction)
        if val is not None:
            return ("allowed" if val in YES else "prohibited" if val in NO
                    else "unknown")
    return None


def directed_legs(way, via, nodes):
    t = tags(way)
    refs = [n.get("ref") for n in way.findall("nd")]
    oneway = t.get("oneway", "").lower()
    if not oneway and t.get("junction") in ("roundabout", "circular"):
        oneway = "yes"
    if oneway not in ("", "no", "0", "false", "yes", "1", "true", "-1", "reverse"):
        return {"arrivals": [], "departures": [], "uncertainty": "unknown_oneway"}
    orientations = ("f",) if oneway in ("yes", "1", "true") else (
        ("r",) if oneway in ("-1", "reverse") else ("f", "r"))
    legs = []
    for i, (a,b) in enumerate(zip(refs, refs[1:])):
        for d in orientations:
            origin, destination = (a,b) if d=="f" else (b,a)
            if origin != via and destination != via:
                continue
            direction = "forward" if d=="f" else "backward"
            directional = explicit_direction(t, direction)
            state = merge(access(t),barrier(tags(nodes[origin])),
                          barrier(tags(nodes[destination])))
            if directional is not None:
                # A directional deny is effective even on an otherwise open way.
                state = merge(state, directional) if directional != "allowed" else (
                    "allowed" if state == "allowed" else state)
            legs.append({"id": f"w:{way.get('id')}:{i}:{d}",
                         "orientation": d, "directional_tag": directional,
                         "access": state, "arrives": destination==via,
                         "departs": origin==via})
    return {"arrivals": [x for x in legs if x["arrives"]],
            "departures": [x for x in legs if x["departs"]],
            "uncertainty": None}


def relation_viability(relation, ways, nodes):
    members = relation.findall("member")
    fr = [m.get("ref") for m in members if m.get("type")=="way" and m.get("role")=="from"]
    to = [m.get("ref") for m in members if m.get("type")=="way" and m.get("role")=="to"]
    via = [m.get("ref") for m in members if m.get("type")=="node" and m.get("role")=="via"]
    row = {"relation": relation.get("id"), "restriction": tags(relation).get("restriction"),
           "from": fr, "to": to, "via": via}
    if len(fr) != 1 or len(to) != 1 or len(via) != 1:
        return {**row, "verdict": "UNSUPPORTED_RELATION_SHAPE"}
    if fr[0] not in ways or to[0] not in ways or via[0] not in nodes:
        return {**row, "verdict": "INCOMPLETE_SOURCE"}
    a = directed_legs(ways[fr[0]], via[0], nodes)
    b = directed_legs(ways[to[0]], via[0], nodes)
    arrivals = a["arrivals"]
    departures = b["departures"]
    available_in = [x for x in arrivals if x["access"] == "allowed"]
    available_out = [x for x in departures if x["access"] == "allowed"]
    unresolved = bool(a["uncertainty"] or b["uncertainty"] or
                      any(x["access"]=="unknown" for x in arrivals+departures))
    return {**row, "from_incoming_edges": len(arrivals),
            "from_car_allowed_edges": len(available_in),
            "to_departing_edges": len(departures),
            "to_car_allowed_edges": len(available_out),
            "directional_car_denials": [
                {"way": "from", "edge": x["id"]} for x in arrivals
                if x["directional_tag"] == "prohibited"] +
                [{"way": "to", "edge": x["id"]} for x in departures
                 if x["directional_tag"] == "prohibited"],
            "verdict": ("UNKNOWN_CONDITIONAL_OR_ACCESS" if unresolved else
                        "NO_AVAILABLE_MOTORCAR_MOVEMENT" if not available_in or not available_out
                        else "REPRESENTABLE_MOTORCAR_MOVEMENT")}


def isolated_direction_mismatch(way,nodes):
    """Detect a source restriction that the prototype's single-way graph omits."""
    restrictions = [(direction, explicit_direction(tags(way), direction))
                    for direction in ("forward", "backward")]
    restrictions = [(d,v) for d,v in restrictions if v=="prohibited"]
    if not restrictions:
        return []
    try:
        graph=import_osm_xml(isolated(way,nodes),
             provenance=Provenance("Manchester", "v3 archived UK OSM snapshot",
                    "source-direction diagnostics", "OpenStreetMap contributors; ODbL")).graph
    except OSMImportError as exc:
        return [{"status":"NOT_JUDGED","reason":str(exc)[:160]}]
    return [{"source_direction":d,"source_access":v,
             "graph_edge_count":sum(1 for e in graph.edges.values()
                  if e.edge_id.endswith(":f" if d=="forward" else ":r")
                  and e.access=="allowed"),
             "verdict":"SOURCE_DIRECTIONAL_ACCESS_MISMATCH" if any(
                 e.edge_id.endswith(":f" if d=="forward" else ":r")
                 and e.access=="allowed" for e in graph.edges.values()) else "NO_MISMATCH_DETECTED"}
            for d,v in restrictions]


def diagnose(root):
    ways={w.get("id"):w for w in root.findall("way")}
    nodes={n.get("id"):n for n in root.findall("node")}
    relations=root.findall("relation")
    rows=[]
    for wid in TARGETS:
        if wid not in ways:
            rows.append({"source_way":wid,"status":"NOT_JUDGED","reason":"missing_source_way"})
            continue
        rows.append({"source_way":wid,"tags":{k:v for k,v in tags(ways[wid]).items()
                                           if k in {"highway","oneway","vehicle:backward"}},
            "relations":[relation_viability(r,ways,nodes) for r in related(wid,relations)],
            "directional_access_observations":isolated_direction_mismatch(ways[wid],nodes)})
    return rows


def main():
    src=ROOT/"map001-manchester.osm"
    manifest=json.loads((ROOT/"map001-v3-manifest.json").read_text())
    expected=next(x["source_sha256"] for x in manifest["areas"]
                  if x["area"]=="manchester")
    raw=src.read_bytes()
    if digest(raw)!=expected:raise ValueError("Manchester v3 frozen source hash mismatch")
    report={"trial":"MAP-001-V3-MANCHESTER-DIAGNOSTICS",
            "source_sha256":expected,
            "truth":"PROVISIONAL_OSM_SOURCE_NOT_SIGNED_ROAD_LAW",
            "navigation_code_changed":False,"cases":diagnose(ET.fromstring(raw))}
    output=ROOT/"map001-v3-manchester-diagnostics.json"
    output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"trial":report["trial"],
          "cases":[{"way":x["source_way"],
                    "relations":[(r["relation"],r["verdict"]) for r in x.get("relations",[])],
                    "directional":x.get("directional_access_observations",[])}
                   for x in report["cases"]]},indent=2))
if __name__=="__main__":
    main()
