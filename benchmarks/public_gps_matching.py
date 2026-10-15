"""Public UK road-geometry GPS matching smoke; injected fixes are SIMULATED.

Pinned Geofabrik OpenStreetMap road graph, synthetic observations at geometrical
edge midpoints. Never real phone GNSS or independently measured GPS accuracy.
No coordinates, raw road IDs or user routes are included in the published report.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from math import atan2,cos,degrees,radians
from pathlib import Path

from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from map_data import Provenance,import_osm_xml
from map_data.osm_xml import MAX_INPUT_BYTES

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/"results"


def _bearing(a,b):
    lat=(a[0]+b[0])/2
    east=(b[1]-a[1])*cos(radians(lat))
    north=b[0]-a[0]
    return (degrees(atan2(east,north))+360)%360


def evaluate(raw:bytes, *, snapshot:str,limit:int=30)->dict:
    if not 1<=limit<=100:
        raise ValueError("Limit out of range")
    imported=import_osm_xml(raw,provenance=Provenance(
        "public UK independent bounded map sample",snapshot,
        "Geofabrik-UK-pinned-public", "© OpenStreetMap contributors"))
    matcher=DirectedRoadMatcher(imported.graph,imported.coordinates)
    edges=tuple(e for e in sorted(imported.graph.edges.values(),
                                  key=lambda e:e.edge_id)
                if e.access=="allowed" and e.length_m>=15.0)
    if len(edges)<5:
        raise ValueError("Insufficient varied road edges to exercise matching")
    chosen=edges[::max(1,len(edges)//limit)][:limit]
    counts=Counter()
    for e in chosen:
        a,b=imported.coordinates[e.source],imported.coordinates[e.target]
        lat=(a[0]+b[0])/2
        lon=(a[1]+b[1])/2
        bearing=_bearing(a,b)
        # Three independent, deterministic, simulated observations per real
        # mapped road link. Deltas are ~3 m and are not recorded or uploaded.
        for suffix,dlat,dlon in (("center",0,0),("offset_north",3/111195,0),
                                 ("offset_east",0,3/(111195*cos(radians(lat))))):
            fix=GPSFix(1000,lat+dlat,lon+dlon,3.0,10.0,bearing)
            r=matcher.match(fix)
            counts["normal_total"]+=1
            counts["normal_"+r.status.lower()]+=1
            if r.status=="MATCHED":
                counts["normal_correct_edge"]+=int(r.edge_id==e.edge_id)
                counts["normal_wrong_edge"]+=int(r.edge_id!=e.edge_id)
        # In adversarial cases there must be NO confident road assignment.
        uncertain=matcher.match(GPSFix(1000,lat,lon,90,0,None))
        spike=matcher.match(GPSFix(1000,lat,lon,3,120,bearing))
        stale=matcher.match(GPSFix(1000,lat,lon,3,10,bearing),now_ms=12000)
        for key,r in (("weak_fix",uncertain),("speed_spike",spike),("stale_fix",stale)):
            counts[key+"_total"]+=1
            counts[key+"_safe"]+=int(r.status in ("REJECTED","UNKNOWN","AMBIGUOUS"))
            counts[key+"_confident"]+=int(r.status=="MATCHED")
    return {
        "classification":"public-UK-mapped-road-simulated-GPS-not-device-accuracy",
        "source_snapshot":snapshot,"source_sha256":sha256(raw).hexdigest(),
        "road_graph_vertices":len(imported.graph.vertices),
        "road_graph_directed_edges":len(imported.graph.edges),
        "sampled_distinct_directed_edges":len(chosen),
        "normal_fix_cases":counts["normal_total"],
        "correct_directed_edge_confident":counts["normal_correct_edge"],
        "wrong_directed_edge_confident":counts["normal_wrong_edge"],
        "ambiguous_fix_cases":counts["normal_ambiguous"],
        "unknown_fix_cases":counts["normal_unknown"],
        "adversarial_cases":3*len(chosen),
        "adversarial_safely_not_matched":sum(counts[k+"_safe"] for k in
            ("weak_fix","speed_spike","stale_fix")),
        "adversarial_confident_matches":sum(counts[k+"_confident"] for k in
            ("weak_fix","speed_spike","stale_fix")),
        "actual_phone_GPS_measurements":0,
        "sensor_fusion_implemented":False,
        "full_session_navigation_tested":False,
        "independent_position_ground_truth":False,
        "external_engines_executed":0,
        "navigation_score":None,
        "warning":"Ground truth is the same public road geometry used to create the SIMULATED fixes; this measures algorithm behavior only, not field accuracy."
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--snapshot",required=True)
    p.add_argument("--limit",type=int,default=30)
    args=p.parse_args()
    target=args.input.resolve()
    if target.suffix!=".osm" or not target.is_relative_to(RESULTS.resolve()):
        raise ValueError("Use ephemeral public OSM XML under ignored results/")
    if not target.is_file() or not 0<target.stat().st_size<=MAX_INPUT_BYTES:
        raise ValueError("Missing or oversized public source")
    print(json.dumps(evaluate(target.read_bytes(),snapshot=args.snapshot,
                              limit=args.limit),indent=2))


if __name__=="__main__":
    main()
