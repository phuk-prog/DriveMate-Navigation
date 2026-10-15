"""Same-metric, same-source *geometry proximity* diagnostic for GPS engines.

All providers are judged with the exact generating OSM directed-link segment,
the same GPS observation, and the same 5 m geometry tolerance. This can show
a snapped point lies NEAR map geometry; it CANNOT independently establish
true road identity, direction, a legal maneuver or live GNSS accuracy.
"""
from __future__ import annotations

from collections import Counter
from math import cos, hypot, isfinite, radians
from typing import Mapping

from engine.routing import RoadGraph

M_PER_LAT = 111195.0
TARGET_TOLERANCE_M = 5.0
COMPETING_LINK_RADIUS_M = 10.0


def closest_point_on_road(point: tuple[float, float],
                          a: tuple[float, float], b: tuple[float,float]
                          ) -> tuple[tuple[float,float],float] | None:
    """Local tangent-plane segment projection; bounded Manchester-size inputs."""
    lat,lon=point
    if any(not isfinite(z) for z in (lat,lon,*a,*b)):
        raise ValueError("Nonfinite road geometry")
    if abs(lat)>90 or abs(lon)>180 or any(abs(q[0])>90 or abs(q[1])>180 for q in (a,b)):
        raise ValueError("Coordinates outside Earth bounds")
    m_lon=M_PER_LAT*cos(radians(lat))
    if m_lon<1.0:
        raise ValueError("Near-pole projection is not supported")
    ax,ay=(a[1]-lon)*m_lon,(a[0]-lat)*M_PER_LAT
    bx,by=(b[1]-lon)*m_lon,(b[0]-lat)*M_PER_LAT
    vx,vy=bx-ax,by-ay
    norm=vx*vx+vy*vy
    if norm<1.e-8:
        return None
    t=max(0.0,min(1.0,-(ax*vx+ay*vy)/norm))
    dx,dy=ax+t*vx,ay+t*vy
    return ((lat+dy/M_PER_LAT,lon+dx/m_lon),hypot(dx,dy))


def _source_way_id(edge_id: str) -> str | None:
    # Our bounded OSM importer emits w:<way_id>:<segment_index>:f|r.
    # Do not pretend arbitrary/third-party edge labels are OSM identities.
    bits=edge_id.split(":")
    if (len(bits)==4 and bits[0]=="w" and bits[1].isdigit()
            and bits[2].isdigit() and bits[3] in ("f","r")):
        return bits[1]
    return None


def expected_road_geometry_probe(
    graph: RoadGraph, coords: Mapping[str,tuple[float,float]],
    expected_edge_id: str, point: tuple[float,float] | None
) -> dict[str,object]:
    """Do not confuse generated-road geometry nearness with true road accuracy.

    Count allowed directed alternatives within 10 metres of the snapped
    location; OSM two-way reverse edges can make road direction ambiguous
    even when their geometry exactly coincides.
    """
    if expected_edge_id not in graph.edges:
        raise ValueError("Unknown generating graph edge")
    if point is None:
        return {"state":"withheld","near_expected_geometry":False,
                "nearby_other_directed_edges":None,"direction_verified":False}
    expected=graph.edges[expected_edge_id]
    projected=closest_point_on_road(point,coords[expected.source],coords[expected.target])
    if projected is None:
        raise ValueError("Degenerate expected road segment")
    distance=projected[1]
    competing=0
    reversed_same_segment=0
    same_way_other_segment=0
    distinct_osm_way=0
    unidentified_other_segment=0
    expected_way=_source_way_id(expected.edge_id)
    for road in graph.edges.values():
        if road.edge_id==expected_edge_id or road.access!="allowed":
            continue
        other=closest_point_on_road(point,coords[road.source],coords[road.target])
        if other is not None and other[1]<=COMPETING_LINK_RADIUS_M:
            competing+=1
            if road.source==expected.target and road.target==expected.source:
                reversed_same_segment+=1
            elif (expected_way is not None
                  and _source_way_id(road.edge_id)==expected_way):
                same_way_other_segment+=1
            elif (expected_way is not None
                  and _source_way_id(road.edge_id) is not None):
                distinct_osm_way+=1
            else:
                unidentified_other_segment+=1
    near=distance<=TARGET_TOLERANCE_M
    return {
        "state":"near_generated_geometry" if near else "off_generated_geometry",
        "near_expected_geometry":near,
        "nearby_other_directed_edges":competing,
        "nearby_reversed_same_segment_edges":reversed_same_segment,
        "nearby_other_segments_same_osm_way":same_way_other_segment,
        "nearby_distinct_osm_way_edges":distinct_osm_way,
        "nearby_unidentified_other_segment_edges":unidentified_other_segment,
        "direction_verified":False,
    }


def report_geometry_last_fix(acc: Counter, prefix: str, graph: RoadGraph,
                             coords: Mapping[str,tuple[float,float]],
                             generating_edge: str, point: tuple[float,float] | None
                             ) -> None:
    evidence=expected_road_geometry_probe(graph,coords,generating_edge,point)
    acc[prefix+"_evaluated"]+=1
    if evidence["state"]=="withheld":
        acc[prefix+"_withheld"]+=1
    elif evidence["near_expected_geometry"]:
        acc[prefix+"_near_geometry"]+=1
        if evidence["nearby_other_directed_edges"]:
            acc[prefix+"_near_but_other_roads_plausible"]+=1
        if evidence["nearby_reversed_same_segment_edges"]:
            acc[prefix+"_near_with_reverse_same_segment"]+=1
        if evidence["nearby_other_segments_same_osm_way"]:
            acc[prefix+"_near_with_other_same_way_segment"]+=1
        if evidence["nearby_distinct_osm_way_edges"]:
            acc[prefix+"_near_with_distinct_osm_way"]+=1
        if evidence["nearby_unidentified_other_segment_edges"]:
            acc[prefix+"_near_with_unidentified_other_segment"]+=1
        if (evidence["nearby_reversed_same_segment_edges"]
                ==evidence["nearby_other_directed_edges"]
                and evidence["nearby_other_directed_edges"]>0):
            acc[prefix+"_near_reverse_only"]+=1
    else:
        acc[prefix+"_off_geometry"]+=1


def ensure_geometry_denominators(acc: Counter, prefixes: tuple[str,...], samples:int) -> None:
    for prefix in prefixes:
        if acc[prefix+"_evaluated"]!=samples:
            raise AssertionError("Common source geometry sample denominator differs")
        if (acc[prefix+"_near_geometry"]+acc[prefix+"_off_geometry"]
                +acc[prefix+"_withheld"]!=samples):
            raise AssertionError("Unexplained source-geometry observation outcomes")


def geometry_summary(acc: Counter, prefix: str) -> dict[str,int]:
    return {
        "total":acc[prefix+"_evaluated"],
        "near_generating_road_within_5m":acc[prefix+"_near_geometry"],
        "farther_than_5m_from_generating_road":acc[prefix+"_off_geometry"],
        "not_alignable_or_withheld":acc[prefix+"_withheld"],
        "near_but_alternative_directed_roads_within_10m":
            acc[prefix+"_near_but_other_roads_plausible"],
        "near_and_reverse_same_segment_present":
            acc[prefix+"_near_with_reverse_same_segment"],
        "near_and_reverse_same_segment_only":acc[prefix+"_near_reverse_only"],
        "near_and_other_segment_same_osm_way_present":
            acc[prefix+"_near_with_other_same_way_segment"],
        "near_and_distinct_osm_way_present":
            acc[prefix+"_near_with_distinct_osm_way"],
        "near_and_unidentified_other_segment_present":
            acc[prefix+"_near_with_unidentified_other_segment"],
    }


def projected_dmn_result(result, fix, graph:RoadGraph,
                         coords:Mapping[str,tuple[float,float]]
                         ) -> tuple[float,float] | None:
    if result.status!="MATCHED":
        return None
    edge=graph.edges[result.edge_id]
    result=closest_point_on_road((fix.latitude,fix.longitude),
                                 coords[edge.source],coords[edge.target])
    return result[0] if result is not None else None
