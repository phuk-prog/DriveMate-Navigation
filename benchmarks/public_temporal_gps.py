"""Compare stateless vs temporal DMN matching on an identical public UK map.

Input GPS observations are entirely MAP-DERIVED simulated trajectories, with
known generating OSM directed edges. The road source, not independent survey,
defines truth; no phone/GNSS or external provider accuracy is measured.
Report only aggregate counts and deliberately withhold risky assignments.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from math import atan2, cos, degrees, radians
from pathlib import Path

from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher
from map_data import Provenance, import_osm_xml
from map_data.osm_xml import MAX_INPUT_BYTES

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/"results"

def _bearing(p,q):
    lat=(p[0]+q[0])/2
    return (degrees(atan2((q[1]-p[1])*cos(radians(lat)),q[0]-p[0]))+360)%360

def _point(p,q,ratio):
    return (p[0]+(q[0]-p[0])*ratio,p[1]+(q[1]-p[1])*ratio)

def evaluate(raw:bytes, *, snapshot:str,limit:int=40)->dict:
    if not 1<=limit<=100:
        raise ValueError("Limit must be between 1 and 100")
    imported=import_osm_xml(raw,provenance=Provenance(
        "pinned public UK temporal road replay",snapshot,
        "Geofabrik-public-pinned","© OpenStreetMap contributors"))
    graph=imported.graph
    coords=imported.coordinates
    single=DirectedRoadMatcher(graph,coords)
    candidates=[]
    for parent in sorted(graph.edges.values(),key=lambda e:e.edge_id):
        if parent.access!="allowed" or parent.length_m<20:
            continue
        for successor in graph.adjacency[parent.target]:
            if successor.access!="allowed" or successor.length_m<15 or (
                    parent.edge_id,successor.edge_id) in graph.prohibited_turns:
                continue
            candidates.append((parent,successor))
    # Stable stratified scan, no user-specified origin/destination.
    chosen=candidates[::max(1,len(candidates)//limit)][:limit]
    summary=Counter()
    for incoming,outgoing in chosen:
        a,b=coords[incoming.source],coords[incoming.target]
        c,d=coords[outgoing.source],coords[outgoing.target]
        lat1,lon1=_point(a,b,0.70)
        lat2,lon2=_point(c,d,0.20)
        heading1=_bearing(a,b)
        heading2=_bearing(c,d)
        # 30-second spacing is explicitly under the anchor expiry only if
        # the second input is near enough. For baseline, use 8 seconds.
        first=GPSFix(1000,lat1,lon1,3.0,10.0,heading1)
        second=GPSFix(9000,lat2,lon2,3.0,10.0,heading2)
        baseline=single.match(second)
        temporal=TemporalRoadMatcher(single)
        anchor=temporal.update(first)
        improved=temporal.update(second)
        summary["selected_pairs"]+=1
        summary["initial_confident_anchor"]+=int(anchor.status=="MATCHED" and anchor.edge_id==incoming.edge_id)
        summary["baseline_correct"]+=int(baseline.status=="MATCHED" and baseline.edge_id==outgoing.edge_id)
        summary["baseline_wrong"]+=int(baseline.status=="MATCHED" and baseline.edge_id!=outgoing.edge_id)
        summary["baseline_withheld"]+=int(baseline.status!="MATCHED")
        summary["temporal_correct"]+=int(improved.status=="MATCHED" and improved.edge_id==outgoing.edge_id)
        summary["temporal_wrong"]+=int(improved.status=="MATCHED" and improved.edge_id!=outgoing.edge_id)
        summary["temporal_withheld"]+=int(improved.status!="MATCHED")
        summary["resolved_from_baseline_withheld"]+=int(
            baseline.status!="MATCHED" and improved.status=="MATCHED" and improved.edge_id==outgoing.edge_id)
        # Explicit adversarial controls: bad GNSS speed and unknown accuracy.
        spike=TemporalRoadMatcher(single)
        spike.update(first)
        bad=spike.update(GPSFix(2000,lat2,lon2,3.0,120.0,heading2))
        weak=TemporalRoadMatcher(single)
        weak.update(first)
        faded=weak.update(GPSFix(9000,lat2,lon2,90.0,0.0,None))
        summary["spike_rejected"]+=int(bad.status=="REJECTED")
        summary["weak_not_matched"]+=int(faded.status!="MATCHED")
    return {
        "classification":"temporal-vs-single-OSM-geometry-derived-simulated-uk",
        "source_snapshot":snapshot,"source_sha256":sha256(raw).hexdigest(),
        "road_graph_vertices":len(graph.vertices),
        "road_graph_edges":len(graph.edges),
        "same_candidate_journeys":summary["selected_pairs"],
        "initial_confident_anchors":summary["initial_confident_anchor"],
        "single_correct":summary["baseline_correct"],
        "single_confident_wrong":summary["baseline_wrong"],
        "single_withheld":summary["baseline_withheld"],
        "temporal_correct":summary["temporal_correct"],
        "temporal_confident_wrong":summary["temporal_wrong"],
        "temporal_withheld":summary["temporal_withheld"],
        "rescued_from_single_withheld":summary["resolved_from_baseline_withheld"],
        "implausible_speed_rejected":summary["spike_rejected"],
        "weak_fix_safely_withheld":summary["weak_not_matched"],
        "independently_verified_legal_turns":0,
        "actual_phone_GPS_measurements":0,
        "sensor_fusion_implemented":False,
        "external_navigation_engines_run":0,
        "full_end_to_end_journeys_verified":0,
        "score_out_of_ten":None,
        "warning":"Both matchers judged against SAME OSM-derived paths; this is not surveyed position truth or independent UK road legality."
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--snapshot",required=True)
    parser.add_argument("--limit",type=int,default=40)
    args=parser.parse_args()
    path=args.input.resolve()
    if path.suffix!=".osm" or not path.is_relative_to(RESULTS.resolve()):
        raise ValueError("Nonpersonal public OSM XML must be under ignored results/")
    if not path.is_file() or not 0<path.stat().st_size<=MAX_INPUT_BYTES:
        raise ValueError("Missing or oversized public extract")
    print(json.dumps(evaluate(path.read_bytes(),snapshot=args.snapshot,limit=args.limit),indent=2))

if __name__=="__main__":
    main()
