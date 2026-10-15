"""Live *local* OSRM Match vs DMN GPS-matching diagnostic on identical UK samples.

This module makes the first external GPS matching reference executable, not
merely a routing proxy. Public, OSM-derived artificial fixes only; actual OSRM
returned snapped locations are judged for PROXIMITY to generated coordinates,
not independently surveyed road/lane truth. Never award a navigation score.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from math import asin, cos, degrees, atan2, radians, sin, sqrt, isfinite
from pathlib import Path
from time import perf_counter_ns
from typing import Callable

from urllib.request import build_opener

from benchmarks.osrm_live_reference import NoRedirect, BASE_URL, wait_for_local_router
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher
from map_data import Provenance, import_osm_xml
from benchmarks.public_uk_probe import _public_file

MATCH_PREFIX = BASE_URL + "/match/v1/driving/"
MAX_REPLY_BYTES = 100_000
OPENER = build_opener(NoRedirect())


def _bearing(start, finish) -> float:
    lat = (start[0]+finish[0])/2
    dx = (finish[1]-start[1])*cos(radians(lat))
    dy = finish[0]-start[0]
    return (degrees(atan2(dx,dy))+360)%360


def _point(a, b, fraction) -> tuple[float, float]:
    return (a[0]+(b[0]-a[0])*fraction,
            a[1]+(b[1]-a[1])*fraction)


def _metres(a, b) -> float:
    lat1,lon1,lat2,lon2=map(radians,(*a,*b))
    s=sin((lat2-lat1)/2)**2+cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 12_742_000*asin(min(1,sqrt(max(0,s))))


def local_match_url(fixes: list[GPSFix]) -> str:
    """Accept only bounded, validated artificial GPS inputs for localhost OSRM."""
    if not 3<=len(fixes)<=8:
        raise ValueError("OSRM Match requires 3..8 research input fixes")
    if any(f.timestamp_ms%1000 for f in fixes):
        raise ValueError("Use whole-second GPS timestamps")
    if any(b.timestamp_ms<=a.timestamp_ms for a,b in zip(fixes,fixes[1:])):
        raise ValueError("GPS timestamps must increase strictly")
    positions=";".join(f"{f.longitude:.7f},{f.latitude:.7f}" for f in fixes)
    radiuses=";".join(str(max(3,min(20,int(round(f.horizontal_accuracy_m*2))))) for f in fixes)
    times=";".join(str(f.timestamp_ms//1000) for f in fixes)
    return (MATCH_PREFIX + positions +
            "?overview=false&steps=false&gaps=ignore&tidy=true"
            "&radiuses=" + radiuses + "&timestamps=" + times)


def request_local_osrm_match(url: str) -> dict:
    if not url.startswith(MATCH_PREFIX) or len(url)>1600:
        raise ValueError("OSRM Match must use the fixed localhost endpoint")
    with OPENER.open(url, timeout=12) as response:
        if response.status!=200:
            raise ValueError("Local OSRM Match returned non-200 HTTP status")
        raw=response.read(MAX_REPLY_BYTES+1)
    if len(raw)>MAX_REPLY_BYTES:
        raise ValueError("OSRM Match output exceeds bounded adapter limit")
    payload=json.loads(raw)
    if not isinstance(payload,dict) or payload.get("code") not in ("Ok","NoMatch","NoSegment"):
        raise ValueError("OSRM Match returned an unsupported response or error")
    return payload


def generate_cases(imported, limit: int):
    graph=imported.graph
    coords=imported.coordinates
    pairs=[]
    for incoming in sorted(graph.edges.values(),key=lambda e:e.edge_id):
        if incoming.access!="allowed" or incoming.length_m<25:
            continue
        for outgoing in graph.adjacency[incoming.target]:
            if outgoing.access!="allowed" or outgoing.length_m<20:
                continue
            if (incoming.edge_id,outgoing.edge_id) in graph.prohibited_turns:
                continue
            pairs.append((incoming,outgoing))
    if not pairs:
        raise ValueError("Not enough public-road adjoining edges")
    chosen=pairs[::max(1,len(pairs)//limit)][:limit]
    result=[]
    for first,second in chosen:
        a,b=coords[first.source],coords[first.target]
        c,d=coords[second.source],coords[second.target]
        points=[_point(a,b,.20),_point(a,b,.75),
                _point(c,d,.25),_point(c,d,.80)]
        bearings=[_bearing(a,b)]*2+[_bearing(c,d)]*2
        timestamps=[1000,9000,17000,25000]
        fixes=[GPSFix(t,lat,lon,3.0,10.0,bearing)
               for t,(lat,lon),bearing in zip(timestamps,points,bearings)]
        result.append((first.edge_id,second.edge_id,fixes))
    return result


def evaluate(raw: bytes, *, snapshot: str, limit: int=12,
             request: Callable[[str],dict]=request_local_osrm_match) -> dict:
    if not 1<=limit<=24:
        raise ValueError("Bounded sample count must be in 1..24")
    imported=import_osm_xml(raw,provenance=Provenance(
        "public UK same-source OSRM map matching",snapshot,
        "Geofabrik-public-UK-pinned","© OpenStreetMap contributors"))
    graph=imported.graph
    matcher=DirectedRoadMatcher(graph,imported.coordinates)
    cases=generate_cases(imported,limit)
    counts=Counter()
    osrm_latencies=[]
    for _,outgoing,fixes in cases:
        target=fixes[-1]
        single=matcher.match(target)
        temporal=TemporalRoadMatcher(matcher)
        for fix in fixes:
            latest=temporal.update(fix)
        for prefix,r in (("dmn_single",single),("dmn_temporal",latest)):
            counts[prefix+"_correct_edge"]+=int(r.status=="MATCHED" and r.edge_id==outgoing)
            counts[prefix+"_wrong_confident_edge"]+=int(r.status=="MATCHED" and r.edge_id!=outgoing)
            counts[prefix+"_withheld"]+=int(r.status!="MATCHED")
        # Exactly the same four generated GNSS coordinates are fed to OSRM.
        url=local_match_url(fixes)
        begin=perf_counter_ns()
        response=request(url)
        osrm_latencies.append((perf_counter_ns()-begin)/1e6)
        if not isinstance(response,dict):
            raise ValueError("OSRM Match response was not an object")
        code=response.get("code")
        if code=="Ok":
            trace=response.get("tracepoints")
            matchings=response.get("matchings")
            if not isinstance(trace,list) or len(trace)!=len(fixes):
                raise ValueError("OSRM returned Ok without matching tracepoint positions")
            if not isinstance(matchings,list) or not matchings:
                raise ValueError("OSRM returned Ok without matched road candidates")
            counts["osrm_ok"]+=1
            for original,snapped in zip(fixes,trace):
                counts["osrm_fix_points"]+=1
                if snapped is None:
                    counts["osrm_fix_unmatched"]+=1
                    continue
                if not isinstance(snapped,dict) or not isinstance(snapped.get("location"),list):
                    raise ValueError("OSRM returned malformed snapped tracepoint")
                loc=snapped["location"]
                if len(loc)!=2 or any(type(v) not in (float,int) or not isfinite(v) for v in loc):
                    raise ValueError("OSRM snapped point is invalid")
                lon,lat=loc
                if abs(lat)>90 or abs(lon)>180:
                    raise ValueError("OSRM snapped point falls outside geographical bounds")
                distance=_metres((original.latitude,original.longitude),(lat,lon))
                counts["osrm_snap_within_20m_of_input"]+=int(distance<=20)
                counts["osrm_snap_more_than_20m_from_input"]+=int(distance>20)
        elif code in ("NoMatch","NoSegment"):
            counts["osrm_no_match"]+=1
        else:
            raise ValueError("OSRM reference endpoint or version was not available")
    n=len(cases)
    return {
        "classification":"public-UK-OSM-generated-GPS-local-OSRM-Match-vs-DMN-diagnostic",
        "source_snapshot":snapshot,
        "source_sha256":sha256(raw).hexdigest(),
        "public_road_cases_sent_to_both":n,
        "simulated_GPS_fixes_per_case":4,
        "dmn_single_correct_directed_edge":counts["dmn_single_correct_edge"],
        "dmn_single_wrong_confident_edge":counts["dmn_single_wrong_confident_edge"],
        "dmn_single_withheld":counts["dmn_single_withheld"],
        "dmn_temporal_correct_directed_edge":counts["dmn_temporal_correct_edge"],
        "dmn_temporal_wrong_confident_edge":counts["dmn_temporal_wrong_confident_edge"],
        "dmn_temporal_withheld":counts["dmn_temporal_withheld"],
        "osrm_match_ok_cases":counts["osrm_ok"],
        "osrm_no_match_cases":counts["osrm_no_match"],
        "osrm_tracepoints_total":counts["osrm_fix_points"],
        "osrm_tracepoints_unmatched":counts["osrm_fix_unmatched"],
        "osrm_snapped_within_20m_of_generated_input":counts["osrm_snap_within_20m_of_input"],
        "osrm_snapped_farther_than_20m_from_generated_input":counts["osrm_snap_more_than_20m_from_input"],
        "osrm_match_requests_executed":len(osrm_latencies),
        "osrm_match_http_request_median_ms":round(sorted(osrm_latencies)[n//2],4),
        "external_reference_families_executed":1,
        "external_reference_version":"OSRM 5.27.1 (locally containerized)",
        "identical_public_osm_extract_supplied":True,
        "identical_routing_profiles":False,
        "equivalent_position_accuracy_measure":False,
        "independent_position_ground_truth":False,
        "real_device_GPS_measurements":0,
        "navigation_score":None,
        "do_not_rank":True,
        "limitations":[
            "Generated test fixes and target DMN edge IDs originate from the same OSM map",
            "OSRM Match snaps to independently profiled OSRM roads and does not return DMN edge IDs",
            "OSRM snapped point proximity does not demonstrate correct direction, road, lane or legal movement",
            "OSRM Match uses 4-point trace and HTTP; DMN candidate metrics evaluate the final fix",
            "OSRM HTTP latency is not comparable to in-process Python matching latency",
        ],
    }


def main():
    p=argparse.ArgumentParser(description="Strict localhost OSRM Match on public UK geometry only")
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--snapshot",required=True)
    p.add_argument("--samples",type=int,default=12)
    args=p.parse_args()
    raw=_public_file(args.input).read_bytes()
    wait_for_local_router()
    print(json.dumps(evaluate(raw,snapshot=args.snapshot,limit=args.samples),indent=2))


if __name__=="__main__":
    main()
