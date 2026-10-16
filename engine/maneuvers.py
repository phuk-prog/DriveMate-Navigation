"""Isolated research maneuver semantics; no voice timing or Android integration.

The caller must provide trusted per-edge roundabout metadata for the entire graph.
This prototype supports simple single-carriageway roundabouts, not lane counting.
"""
from math import atan2, cos, degrees, isfinite, radians, sin


def principal_maneuvers(graph, coordinates, edge_ids, roundabout_edges):
    """Return principal turns, refusing invalid paths and partial roundabouts.

    Count one accessible outgoing non-ring spoke junction per traversed ring node.
    Incoming-only feeders, unknown/prohibited access and prohibited turns do not
    count. Metadata is explicit: no guessing a roundabout from road curvature.
    """
    ring=frozenset(roundabout_edges)
    if not ring <= graph.edges.keys():
        raise ValueError('Unknown roundabout edge')
    edges=[graph.edges[e] for e in edge_ids]
    for e in edges:
        if e.access!='allowed':raise ValueError('Non-allowed route edge')
        for node in (e.source,e.target):
            p=coordinates[node]
            if len(p)!=2 or any(type(v) not in (int,float) or not isfinite(v) for v in p) or not -90<=p[0]<=90 or not -180<=p[1]<=180:
                raise ValueError('Invalid coordinate')
    for a,b in zip(edges,edges[1:]):
        if a.target!=b.source or (a.edge_id,b.edge_id) in graph.prohibited_turns:
            raise ValueError('Disconnected or prohibited route turn')
    if edges and (edges[0].edge_id in ring or edges[-1].edge_id in ring):
        raise ValueError('Cannot number partial roundabout')
    result=[];i=1
    while i<len(edges):
        a,b=edges[i-1:i+1]
        if b.edge_id in ring:
            exits=0;visited=set()
            while i<len(edges) and edges[i].edge_id in ring:
                e=edges[i]
                if e.target in visited:raise ValueError('Repeated roundabout junction')
                visited.add(e.target)
                outgoing=[x for x in graph.adjacency[e.target] if x.edge_id not in ring and x.access=='allowed' and (e.edge_id,x.edge_id) not in graph.prohibited_turns]
                if outgoing:exits+=1
                i+=1
            if not exits:raise ValueError('No accessible roundabout exit')
            result.append({'kind':'roundabout','exit':exits})
            i+=1  # ring exit is part of this maneuver, not another turn
            continue
        def bearing(e):
            lat1,lon1=map(radians,coordinates[e.source]);lat2,lon2=map(radians,coordinates[e.target])
            return degrees(atan2(sin(lon2-lon1)*cos(lat2),cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(lon2-lon1)))
        delta=(bearing(b)-bearing(a)+180)%360-180
        if abs(delta)>=150:result.append({'kind':'uturn'})
        elif abs(delta)>=45:result.append({'kind':'right' if delta>0 else 'left'})
        i+=1
    return result
