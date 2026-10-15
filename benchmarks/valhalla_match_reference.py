"""Valhalla trace_attributes GPS reference on pinned public UK OSM samples.

Valhalla is run only on localhost, with a separate, version-pinned container.
Shares exact generated GPS shapes and source OSM as OSRM and DMN. Counts
snapped-point proximity, NOT independently validated road/lane legality.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from math import isfinite
from pathlib import Path
from time import perf_counter_ns
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request

from benchmarks.osrm_match_reference import _metres, generate_cases
from benchmarks.public_uk_probe import _public_file
from benchmarks.match_geometry_truth import (
    report_geometry_last_fix, projected_dmn_result,
    ensure_geometry_denominators, geometry_summary)
from benchmarks.valhalla_live_reference import _OPENER,wait_for_local_router
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher
from map_data import Provenance,import_osm_xml

TRACE_URL="http://127.0.0.1:8002/trace_attributes"
MAX_REPLY_BYTES=100_000


def trace_body(fixes) -> bytes:
    if not 3<=len(fixes)<=8:
        raise ValueError("Need bounded 3..8 public synthetic fixes")
    data={
        "costing":"auto",
        "shape_match":"map_snap",
        "shape":[{"lat":fix.latitude,"lon":fix.longitude,
                  "type":"via","search_radius":20} for fix in fixes],
    }
    result=json.dumps(data,separators=(",",":")).encode("utf-8")
    if len(result)>1600:
        raise ValueError("Too many fix bytes")
    return result


def local_valhalla_trace(body:bytes)->dict:
    if not isinstance(body,bytes) or not 10<len(body)<=1600:
        raise ValueError("Only bounded artificial trace bodies permitted")
    payload=json.loads(body)
    if payload.get("costing")!="auto" or payload.get("shape_match")!="map_snap":
        raise ValueError("Unsupported Valhalla trace options")
    if not isinstance(payload.get("shape"),list) or not 3<=len(payload["shape"])<=8:
        raise ValueError("No bounded trace shape")
    request=Request(TRACE_URL,body,{"Content-Type":"application/json"},method="POST")
    try:
        with _OPENER.open(request,timeout=22) as response:
            if response.status!=200:
                raise RuntimeError("Valhalla trace non-200 HTTP status")
            raw=response.read(MAX_REPLY_BYTES+1)
    except HTTPError as exc:
        if exc.code in (400,404,422):
            return {"unroutable":True}
        raise RuntimeError("Valhalla trace HTTP failed") from exc
    except (URLError, ConnectionResetError, BrokenPipeError) as exc:
        raise RuntimeError("Valhalla local matching server unavailable") from exc
    if len(raw)>MAX_REPLY_BYTES:
        raise ValueError("Valhalla trace result too large")
    response=json.loads(raw)
    if not isinstance(response,dict):
        raise ValueError("Valhalla trace response must be a dictionary")
    return response


def evaluate(raw: bytes, *, snapshot:str,limit:int=12,
             request:Callable[[bytes],dict]=local_valhalla_trace,
             live_valhalla:bool=False)->dict:
    if not 1<=limit<=24:
        raise ValueError("Sample count must be 1..24")
    imported=import_osm_xml(raw,provenance=Provenance(
        "public UK Valhalla same-shape experiment",snapshot,
        "Geofabrik-public-UK-pinned","© OpenStreetMap contributors"))
    cases=generate_cases(imported,limit)
    single=DirectedRoadMatcher(imported.graph,imported.coordinates)
    totals=Counter()
    latencies=[]
    for _,edge,fixes in cases:
        simple=single.match(fixes[-1])
        temporal=TemporalRoadMatcher(single)
        for fix in fixes:
            latest=temporal.update(fix)
        for prefix,decision in (("dmn_single",simple),("dmn_temporal",latest)):
            report_geometry_last_fix(
                totals,"geometry_"+prefix,imported.graph,imported.coordinates,edge,
                projected_dmn_result(decision,fixes[-1],imported.graph,imported.coordinates))
            totals[prefix+"_correct"]+=int(decision.status=="MATCHED" and decision.edge_id==edge)
            totals[prefix+"_wrong"]+=int(decision.status=="MATCHED" and decision.edge_id!=edge)
            totals[prefix+"_withheld"]+=int(decision.status!="MATCHED")
        begin=perf_counter_ns()
        response=request(trace_body(fixes))
        latencies.append((perf_counter_ns()-begin)/1e6)
        if not isinstance(response,dict):
            raise ValueError("Invalid Valhalla trace response")
        if response.get("unroutable"):
            totals["valhalla_no_trace"]+=1
            report_geometry_last_fix(totals,"geometry_external",imported.graph,
                                      imported.coordinates,edge,None)
            continue
        matched=response.get("matched_points")
        if not isinstance(matched,list) or len(matched)!=len(fixes):
            raise ValueError("Valhalla response lacks one point per input")
        totals["valhalla_trace_ok"]+=1
        last=matched[-1]
        if last is None or (isinstance(last,dict) and last.get("type")=="unmatched"):
            position=None
        elif isinstance(last,dict) and last.get("type") in ("matched","interpolated"):
            position=(last.get("lat"),last.get("lon"))
        else:
            raise ValueError("Unexpected Valhalla last-fix classification")
        report_geometry_last_fix(totals,"geometry_external",imported.graph,
                                  imported.coordinates,edge,position)
        for fix,point in zip(fixes,matched):
            totals["valhalla_point_total"]+=1
            if point is None or (isinstance(point,dict) and point.get("type")=="unmatched"):
                totals["valhalla_point_unmatched"]+=1
                continue
            if not isinstance(point,dict) or point.get("type") not in ("matched","interpolated"):
                raise ValueError("Unrecognized Valhalla matched point status")
            lat,lon=point.get("lat"),point.get("lon")
            if any(type(x) not in (int,float) or not isfinite(x) for x in (lat,lon)):
                raise ValueError("Matched Valhalla coordinates are invalid")
            if abs(lat)>90 or abs(lon)>180:
                raise ValueError("Matched Valhalla coordinates are out of range")
            distance=_metres((fix.latitude,fix.longitude),(lat,lon))
            totals["valhalla_within_20m"]+=int(distance<=20)
            totals["valhalla_farther_than_20m"]+=int(distance>20)
    from hashlib import sha256
    n=len(cases)
    ensure_geometry_denominators(totals,("geometry_dmn_single","geometry_dmn_temporal",
                                          "geometry_external"),n)
    return {
        "classification":"public-UK-OSM-generated-GPS-Valhalla-trace_attributes-vs-DMN-diagnostic",
        "source_snapshot":snapshot,
        "source_sha256":sha256(raw).hexdigest(),
        "public_road_cases_sent_to_both":n,
        "simulated_GPS_fixes_per_case":4,
        "dmn_single_correct_directed_edge":totals["dmn_single_correct"],
        "dmn_single_wrong_confident_edge":totals["dmn_single_wrong"],
        "dmn_single_withheld":totals["dmn_single_withheld"],
        "dmn_temporal_correct_directed_edge":totals["dmn_temporal_correct"],
        "dmn_temporal_wrong_confident_edge":totals["dmn_temporal_wrong"],
        "dmn_temporal_withheld":totals["dmn_temporal_withheld"],
        "valhalla_trace_ok_cases":totals["valhalla_trace_ok"],
        "valhalla_no_trace_cases":totals["valhalla_no_trace"],
        "valhalla_tracepoints_total":totals["valhalla_point_total"],
        "valhalla_tracepoints_unmatched":totals["valhalla_point_unmatched"],
        "valhalla_snapped_within_20m_of_input":totals["valhalla_within_20m"],
        "valhalla_snapped_farther_than_20m_from_input":totals["valhalla_farther_than_20m"],
        "external_reference_families_executed":int(live_valhalla),
        "execution_evidence":"live_local_http" if live_valhalla else "injected_test_double",
        "external_reference_version":"Valhalla 3.9.1 pinned container",
        "same_public_osm_input":True,
        "same_engine_car_profiles":False,
        "equivalent_correct_road_metric":False,
        "actual_surveyed_position_ground_truth":False,
        "common_last_fix_source_geometry_proxy":{
            "dmn_single":geometry_summary(totals,"geometry_dmn_single"),
            "dmn_temporal":geometry_summary(totals,"geometry_dmn_temporal"),
            "valhalla_trace":geometry_summary(totals,"geometry_external"),
        },
        "common_proxy_is_independent_truth":False,
        "common_proxy_proves_correct_road_direction":False,
        "navigation_score":None,
        "do_not_rank":True,
        "note":"Valhalla point proximity, not directed-edge accuracy; version/profile and runner differences prevent a fair ranked accuracy or speed result.",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--snapshot",required=True)
    p.add_argument("--samples",type=int,default=12)
    args=p.parse_args()
    raw=_public_file(args.input).read_bytes()
    wait_for_local_router()
    print(json.dumps(evaluate(raw,snapshot=args.snapshot,limit=args.samples,
                              live_valhalla=True),indent=2))


if __name__=="__main__":
    main()
