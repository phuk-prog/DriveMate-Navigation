"""Directed route geometry audit against known graph; NOT independently surveyed."""
from math import isfinite
from gps.matcher import _closest_distance_and_bearing
from gps.fix_quality import GPSFix
from engine.arrival_controller import distance_m

def check_route_line(graph, coordinates, edge_ids, points, *, tolerance_m=3.0):
    if not isinstance(edge_ids,(tuple,list)) or not edge_ids:
        raise ValueError("Missing directed route")
    if not isinstance(points,(tuple,list)) or len(points)<2:
        raise ValueError("Missing route polyline")
    if type(tolerance_m) not in (int,float) or not isfinite(tolerance_m) or tolerance_m<=0:
        raise ValueError("Invalid tolerance")
    edges=[]
    for eid in edge_ids:
        if eid not in graph.edges:
            raise ValueError("Unknown road fragment")
        edge=graph.edges[eid]
        if edge.access!="allowed":
            raise ValueError("Road not marked allowed")
        if edges and (edges[-1].target!=edge.source or
                      (edges[-1].edge_id,eid) in graph.prohibited_turns):
            raise ValueError("Disconnected or restricted turn")
        edges.append(edge)
    pts=[]
    for point in points:
        if (not isinstance(point,(tuple,list)) or len(point)!=2 or
            any(type(v) not in (int,float) or not isfinite(v) for v in point) or
            not -90<=point[0]<=90 or not -180<=point[1]<=180):
            raise ValueError("Invalid route geometry point")
        pts.append((float(point[0]),float(point[1])))
    def to_edge(p,e):
        f=GPSFix(0,p[0],p[1],3.0)
        q=_closest_distance_and_bearing(f,coordinates[e.source],coordinates[e.target])
        if q is None:raise ValueError("Invalid zero-distance geometry")
        return q[0]
    vertex_errors=[min(to_edge(p,e) for e in edges) for p in pts]
    missing_nodes=[e.target for e in edges[:-1]
                   if min(distance_m(coordinates[e.target],p) for p in pts)>tolerance_m]
    start_error=distance_m(pts[0],coordinates[edges[0].source])
    end_error=distance_m(pts[-1],coordinates[edges[-1].target])
    passed=(start_error<=tolerance_m and end_error<=tolerance_m
            and max(vertex_errors)<=tolerance_m and not missing_nodes)
    return {"status":"PASS" if passed else "FAIL",
            "max_vertex_error_m":max(vertex_errors),
            "start_error_m":start_error,"end_error_m":end_error,
            "missing_road_nodes":missing_nodes,
            "scope":"Graph-derived geometry, not independent UK map or Android screen"}
