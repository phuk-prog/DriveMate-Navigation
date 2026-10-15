"""Local GraphHopper 11.1 /match GPS diagnostics on pinned public UK roads.

Uses the identical four-fix map-generated scenarios as the actual OSRM and
Valhalla match experiments. Never reads a person's GPS traces. Extended JSON
match output is proximity evidence only, NOT legally correct road/direction.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from time import perf_counter_ns
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request
import xml.etree.ElementTree as ET

from benchmarks.osrm_match_reference import _metres, generate_cases
from benchmarks.graphhopper_live_reference import _OPENER, wait_for_graphhopper
from benchmarks.public_uk_probe import _public_file
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher
from map_data import Provenance, import_osm_xml

MATCH_URL=("http://127.0.0.1:8989/match?"
           "profile=car&type=extended_json&points_encoded=false"
           "&instructions=false&calc_points=true&gps_accuracy=10")
MAX_RESPONSE_BYTES=100_000
MAX_REQUEST_BYTES=3200
NS="http://www.topografix.com/GPX/1/1"
FIXTURE_LABEL="public-uk-map-generated-synthetic"


def research_gpx(fixes) -> bytes:
    """Serialize ephemeral, prevalidated public-map-generated fixes only."""
    if not 3<=len(fixes)<=8:
        raise ValueError("Only 3..8 synthetic research fixes per trace")
    if any(b.timestamp_ms<=a.timestamp_ms for a,b in zip(fixes,fixes[1:])):
        raise ValueError("Observations must be chronological")
    root=ET.Element("gpx",{"version":"1.1","creator":"DMN-public-synthetic",
                           "xmlns":NS})
    trk=ET.SubElement(root,"trk")
    ET.SubElement(trk,"name").text=FIXTURE_LABEL
    seg=ET.SubElement(trk,"trkseg")
    for fix in fixes:
        point=ET.SubElement(seg,"trkpt",{"lat":f"{fix.latitude:.7f}",
                                          "lon":f"{fix.longitude:.7f}"})
        when=datetime.fromtimestamp(fix.timestamp_ms/1000,timezone.utc)
        ET.SubElement(point,"time").text=when.strftime("%Y-%m-%dT%H:%M:%SZ")
    encoded=ET.tostring(root,encoding="utf-8",xml_declaration=True)
    if len(encoded)>MAX_REQUEST_BYTES:
        raise ValueError("Generated synthetic GPX exceeds bounded request size")
    return encoded


def _check_synthetic_gpx(payload: bytes) -> None:
    if not isinstance(payload,bytes) or not 50<len(payload)<=MAX_REQUEST_BYTES:
        raise ValueError("Only bounded generated public GPS fixture accepted")
    if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise ValueError("GPX DTD/entities prohibited")
    root=ET.fromstring(payload)
    if (root.tag!="{"+NS+"}gpx" or root.get("creator")!="DMN-public-synthetic"):
        raise ValueError("Expected public synthetic research GPX")
    tracks=root.findall("{"+NS+"}trk")
    if len(tracks)!=1 or tracks[0].findtext("{"+NS+"}name")!=FIXTURE_LABEL:
        raise ValueError("Only explicitly generated public UK fixtures permitted")
    points=root.findall(".//{"+NS+"}trkpt")
    if not 3<=len(points)<=8:
        raise ValueError("Malformed research GPX trace")
    for point in points:
        lat,lon=float(point.attrib["lat"]),float(point.attrib["lon"])
        if not(isfinite(lat) and isfinite(lon) and -90<=lat<=90 and -180<=lon<=180):
            raise ValueError("Invalid geographic location")
        if point.find("{"+NS+"}time") is None:
            raise ValueError("Missing synthetic GPS timestamp")


def request_local_graphhopper_match(body: bytes) -> dict:
    """POST bounded synthetic GPX to verified local endpoint; never follow redirects."""
    _check_synthetic_gpx(body)
    request=Request(MATCH_URL,data=body,
                    headers={"Content-Type":"application/gpx+xml",
                             "Accept":"application/json"},method="POST")
    try:
        with _OPENER.open(request,timeout=24) as response:
            if response.status!=200:
                raise RuntimeError("Unexpected GraphHopper match HTTP status")
            raw=response.read(MAX_RESPONSE_BYTES+1)
    except HTTPError as exc:
        if exc.code==404:
            raise RuntimeError("GraphHopper /match endpoint is unavailable") from exc
        if exc.code in (400,422):
            return {"no_match":True}
        raise RuntimeError("GraphHopper matching HTTP request failed") from exc
    except (URLError,ConnectionResetError,BrokenPipeError) as exc:
        raise RuntimeError("GraphHopper matching service unavailable") from exc
    if len(raw)>MAX_RESPONSE_BYTES:
        raise ValueError("GraphHopper matching response too large")
    answer=json.loads(raw)
    if not isinstance(answer,dict):
        raise ValueError("Invalid GraphHopper extended_json payload")
    return answer


def flattened_matched_points(response: dict) -> list[tuple[float,float]] | None:
    """One-to-one alignment required before comparing individual fix distances.

    GraphHopper's extended_json stores snapped states as wpts nested by link.
    If some observations are discarded, their order cannot be inferred safely
    from index alone; the caller marks the entire cohort unaligned.
    """
    if not isinstance(response,dict):
        raise ValueError("GraphHopper reply must be a dictionary")
    diary=response.get("diary")
    if not isinstance(diary,dict) or not isinstance(diary.get("entries"),list):
        raise ValueError("GraphHopper extended_json has no diary entries")
    entries=diary["entries"]
    if len(entries)!=1 or not isinstance(entries[0],dict):
        raise ValueError("Expected one route in GraphHopper diary")
    links=entries[0].get("links")
    if not isinstance(links,list):
        raise ValueError("Map matching diary lacks links")
    points=[]
    for link in links:
        if not isinstance(link,dict) or not isinstance(link.get("wpts"),list):
            raise ValueError("GraphHopper link has no matched waypoints")
        for p in link["wpts"]:
            if not isinstance(p,dict):
                raise ValueError("Malformed matched waypoint")
            lat,lon=p.get("y"),p.get("x")
            if type(lat) not in (float,int) or type(lon) not in (float,int):
                raise ValueError("Non-numeric snapped coordinates")
            if not all(map(isfinite,(lat,lon))) or abs(lat)>90 or abs(lon)>180:
                raise ValueError("Snapped point outside coordinate range")
            points.append((float(lat),float(lon)))
    return points


def evaluate(raw: bytes, *, snapshot: str, limit: int=12,
             request: Callable[[bytes],dict]=request_local_graphhopper_match,
             live_graphhopper: bool=False) -> dict:
    if not 1<=limit<=24:
        raise ValueError("Bounded public-road cohort size must be 1..24")
    if live_graphhopper and request is not request_local_graphhopper_match:
        raise ValueError("Injected test doubles cannot be labelled live GraphHopper")
    imported=import_osm_xml(raw,provenance=Provenance(
        "public UK GraphHopper same-fix experiment",snapshot,
        "Geofabrik-UK-pinned-public","© OpenStreetMap contributors"))
    cases=generate_cases(imported,limit)
    matcher=DirectedRoadMatcher(imported.graph,imported.coordinates)
    totals=Counter()
    latencies=[]
    for _,expected_outgoing,fixes in cases:
        simple=matcher.match(fixes[-1])
        temporal=TemporalRoadMatcher(matcher)
        for fix in fixes:
            decision=temporal.update(fix)
        for key,result in (("dmn_single",simple),("dmn_temporal",decision)):
            totals[key+"_correct"]+=int(result.status=="MATCHED"
                                          and result.edge_id==expected_outgoing)
            totals[key+"_wrong"]+=int(result.status=="MATCHED"
                                        and result.edge_id!=expected_outgoing)
            totals[key+"_withheld"]+=int(result.status!="MATCHED")
        began=perf_counter_ns()
        answer=request(research_gpx(fixes))
        latencies.append((perf_counter_ns()-began)/1e6)
        if answer.get("no_match") is True:
            totals["graphhopper_no_match_cases"]+=1
            totals["graphhopper_unmatched_or_unaligned_fixes"]+=len(fixes)
            continue
        positions=flattened_matched_points(answer)
        if len(positions)!=len(fixes):
            totals["graphhopper_unaligned_cases"]+=1
            totals["graphhopper_unmatched_or_unaligned_fixes"]+=len(fixes)
            continue
        totals["graphhopper_matched_cases"]+=1
        for fix,location in zip(fixes,positions):
            distance=_metres((fix.latitude,fix.longitude),location)
            totals["graphhopper_matched_fixes"]+=1
            totals["graphhopper_snapped_within_20m"]+=int(distance<=20)
            totals["graphhopper_snapped_farther_than_20m"]+=int(distance>20)
    n=len(cases)
    assert totals["dmn_single_correct"]+totals["dmn_single_wrong"]+totals["dmn_single_withheld"]==n
    assert totals["dmn_temporal_correct"]+totals["dmn_temporal_wrong"]+totals["dmn_temporal_withheld"]==n
    assert totals["graphhopper_matched_fixes"]+totals["graphhopper_unmatched_or_unaligned_fixes"]==4*n
    return {
        "classification":"UK-OSM-generated-synthetic-GPS-GraphHopper-Match-diagnostic",
        "source_snapshot":snapshot,
        "source_sha256":sha256(raw).hexdigest(),
        "public_road_cases_submitted":n,
        "simulated_GPS_fixes_per_case":4,
        "dmn_single_correct_directed_edge":totals["dmn_single_correct"],
        "dmn_single_wrong_confident_edge":totals["dmn_single_wrong"],
        "dmn_single_withheld":totals["dmn_single_withheld"],
        "dmn_temporal_correct_directed_edge":totals["dmn_temporal_correct"],
        "dmn_temporal_wrong_confident_edge":totals["dmn_temporal_wrong"],
        "dmn_temporal_withheld":totals["dmn_temporal_withheld"],
        "graphhopper_map_match_ok_cases":totals["graphhopper_matched_cases"],
        "graphhopper_map_match_no_match_cases":totals["graphhopper_no_match_cases"],
        "graphhopper_unaligned_cases":totals["graphhopper_unaligned_cases"],
        "graphhopper_matched_fixes":totals["graphhopper_matched_fixes"],
        "graphhopper_snapped_within_20m_of_generated_input":totals["graphhopper_snapped_within_20m"],
        "graphhopper_snapped_farther_than_20m_from_generated_input":totals["graphhopper_snapped_farther_than_20m"],
        "graphhopper_unmatched_or_unaligned_fixes":totals["graphhopper_unmatched_or_unaligned_fixes"],
        "graphhopper_match_http_request_median_ms":round(sorted(latencies)[n//2],4),
        "reference_families_actually_executed":int(live_graphhopper),
        "execution_evidence":"live_local_http" if live_graphhopper else "injected_test_double",
        "reference_version":"GraphHopper 11.1 locally hosted Java 25 server",
        "same_public_osm_subset":True,
        "same_vehicle_access_and_cost_profiles":False,
        "equivalent_road_direction_accuracy_measure":False,
        "independently_surveyed_position_ground_truth":False,
        "live_phone_GPS_measurements":0,
        "external_navigation_superiority_verified":False,
        "navigation_score":None,
        "do_not_rank":True,
        "limitations":[
            "Injected fixes and DMN expected edges are generated from the same OSM graph",
            "GraphHopper snapped GPS points have no comparable DMN directed edge IDs",
            "GraphHopper GPX sequence map matching vs DMN last-edge decision is not an equal feature scope",
            "Only fully aligned extended_json observations are assessed for individual snapped-point proximity",
            "Different graph/profile/timing context; HTTP time does not rank in-process routing speed",
            "No physical GPS, independent UK legal sign truth, lane-level accuracy, real reroute or arrival checks",
        ],
    }


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--snapshot",required=True)
    parser.add_argument("--samples",type=int,default=12)
    args=parser.parse_args()
    raw=_public_file(args.input).read_bytes()
    wait_for_graphhopper()
    print(json.dumps(evaluate(raw,snapshot=args.snapshot,limit=args.samples,
                              live_graphhopper=True),indent=2))


if __name__=="__main__":
    main()
