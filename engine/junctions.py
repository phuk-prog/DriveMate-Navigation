"""Original junction geometry plus evidence-backed static lane indications.

Geometry describes the route, never manufactures a painted lane arrow. Explicit
connectivity takes precedence. No inferred vehicle access or forced lane change.
"""
from dataclasses import dataclass
from math import atan2,degrees,radians,sin,cos
from .roundabouts import path_context

@dataclass(frozen=True)
class JunctionInstruction:
    approach: str
    departure: str
    manoeuvre: str
    angle_degrees: float | None
    lane_indications: tuple
    candidate_lanes: tuple
    direct_connections: tuple
    lane_status: str
    alternatives: tuple

def _bearing(points,a,b):
    if a not in points or b not in points:return None
    p,q=points[a],points[b]
    if p==q or max(abs(p[0]),abs(q[0]))>89.99:return None
    lat1,lat2=radians(p[0]),radians(q[0]);dl=radians(q[1]-p[1])
    x=sin(dl)*cos(lat2);y=cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(dl)
    if abs(x)+abs(y)<1e-15:return None
    return degrees(atan2(x,y))
def direction(points,a,b):
    h1=_bearing(points,a.source,a.target);h2=_bearing(points,b.source,b.target)
    if h1 is None or h2 is None:return 'unknown',None
    delta=(h2-h1+180)%360-180;size=abs(delta)
    if size<=20:return 'through',delta
    if size>=165:return 'reverse',delta
    side='left' if delta<0 else 'right'
    return ('slight_'+side if size<45 else 'sharp_'+side if size>=135 else side),delta

def _family(label):
    return 'left' if label.endswith('left') else 'right' if label.endswith('right') else label

def identify_junctions(p,route,inbound=(),departure=None,timezone_name=None,*,origin_fraction=0,destination_fraction=1000000,actual_origin=False):
    roads,names,catalog,rules,after,times=path_context(p,route,inbound,departure,timezone_name,
        origin_fraction=origin_fraction,destination_fraction=destination_fraction,actual_origin=actual_origin)
    points=p.coordinates or {};result=[]
    for i,(a,b) in enumerate(zip(roads,roads[1:])):
        previous,chosen=names[a],names[b]
        choices=tuple(e for e in catalog.outgoing[previous.target] if rules.legal(after[i],e.edge_id,times[i]))
        connections=p.lane_connections.get((a,b),())
        same_way=a.startswith('w:') and b.startswith('w:') and a.split(':')[1]==b.split(':')[1]
        physical=tuple(catalog.outgoing[previous.target])
        nonreverse=tuple(e for e in physical if e.target!=previous.source)
        if same_way and len(nonreverse)<=1 and not connections:continue
        label,angle=direction(points,previous,chosen)
        evidence=previous.lane_evidence
        indications=evidence.indications if evidence is not None else ()
        lane_status='no_lane_evidence';candidates=();direct=()
        if previous.access=='unknown' or chosen.access=='unknown':lane_status='unverified_access'
        elif evidence is not None and evidence.status=='unverified' or chosen.lane_evidence is not None and chosen.lane_evidence.status=='unverified':lane_status='unverified_lane_evidence'
        elif connections:
            if len(connections)!=1 or connections[0].status!='supported':lane_status='unverified_connectivity'
            else:
                links=connections[0].links
                direct=tuple((x,y) for x,y,change in links if not change)
                bounds_ok=all(isinstance(x,int) and not isinstance(x,bool) and isinstance(y,int) and not isinstance(y,bool) and x>=1 and y>=1 and
                    (evidence is None or evidence.count is None or x<=evidence.count) and
                    (chosen.lane_evidence is None or chosen.lane_evidence.count is None or y<=chosen.lane_evidence.count) for x,y in direct)
                if not bounds_ok:direct=();lane_status='unverified_connectivity'
                elif direct:
                    candidates=tuple(sorted({x for x,y in direct}));lane_status='explicit_connectivity'
                else:lane_status='lane_change_required'
        elif previous.junction=='roundabout' or chosen.junction=='roundabout':lane_status='roundabout_without_connectivity'
        elif evidence is not None and evidence.status=='unverified':lane_status='unverified_lane_evidence'
        elif evidence is not None and evidence.status=='supported':
            if label=='unknown':lane_status='geometry_unavailable'
            elif any(direction(points,previous,e)[0]=='unknown' for e in physical) or sum(_family(direction(points,previous,e)[0])==_family(label) for e in physical)!=1:lane_status='ambiguous_branch'
            else:
                candidates=tuple(j for j,marks in enumerate(indications,1) if label in marks)
                lane_status='indicated' if candidates else 'no_matching_indication'
        manoeuvre=label
        if len(nonreverse)==1 and chosen.target!=previous.source and label not in ('unknown','through'):manoeuvre='follow_road_'+label
        result.append(JunctionInstruction(a,b,manoeuvre,angle,indications,candidates,direct,lane_status,tuple(e.edge_id for e in choices)))
    return tuple(result)
