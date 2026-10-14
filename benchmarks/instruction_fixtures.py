"""Original synthetic instruction fixtures, shared by tests and replay sweeps."""
from math import cos,radians,degrees
from gps.matching import Fix,EARTH
from gps.recovery import RecoveringGpsJourney
from engine.routing import RoadGraph,RoadEdge
from engine.reconciled import prepare_navigation
from engine.lanes import parse_lane_evidence

def crossroads(gap=40,latitude=0,access='allowed',turns=(),lanes=True,detour=False):
    xy={'w':(-500,0),'j':(0,0),'k':(0,gap),'end':(300,gap),'straight':(100,0),'north':(0,gap+100)}
    points={n:(latitude+degrees(y/EARTH),degrees(x/(EARTH*cos(radians(latitude))))) for n,(x,y) in xy.items()}
    evidence=parse_lane_evidence({'lanes':'3','turn:lanes':'unknown|through|right' if lanes=='invalid' else 'left|through|right'},'f',True) if lanes else None
    edges=[RoadEdge('a','w','j',500,72,access,lane_evidence=evidence),RoadEdge('b','j','k',gap,36,'allowed'),
           RoadEdge('c','k','end',300,36,'allowed'),RoadEdge('straight','j','straight',100,36,'allowed'),
           RoadEdge('north','k','north',100,36,'allowed')]
    if detour:edges.append(RoadEdge('detour','straight','k',120,36,'allowed'))
    p=prepare_navigation(RoadGraph(points,edges,turns),points)
    return RecoveringGpsJourney(p,'c',800000)

def observe(g,x,y,t,speed=10,accuracy=2,heading=90):
    lat0=g.p.coordinates['w'][0];scale=cos(radians(lat0))
    f=Fix(lat0+degrees(y/EARTH),degrees(x/(EARTH*scale)),t,accuracy,speed,heading,5 if heading is not None else None)
    return g.observe(f,t)

def start(g,distance=150,speed=10):
    for t in (1,2,3):s=observe(g,-distance-3+t,0,t,speed)
    return s
