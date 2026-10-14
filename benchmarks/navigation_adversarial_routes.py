"""Additional independent shortest-route and compound GPS-recovery oracles."""
from decimal import Decimal, ROUND_CEILING
from math import sin,cos,radians,degrees
from random import Random
from engine.routing import RoadEdge, RoadGraph
from engine.reconciled import prepare_navigation
from gps.recovery import RecoveringGpsJourney
from gps.matching import EARTH,Fix

def micro(e):
    return int((Decimal(str(e.estimated_seconds))*1000000).to_integral_value(rounding=ROUND_CEILING))

def route_oracle():
    rng=Random(20261014);errors=[];runs=0
    for case in range(100):
        count=6+case%5
        pts={f'n{i}':(0,i*.0001) for i in range(count)}
        edges=[]
        for i in range(count):
            for j in range(i+1,count):
                if j!=i+1 and rng.random()>.32:continue
                edges.append(RoadEdge(f'e{i}_{j}',f'n{i}',f'n{j}',
                                      40+rng.randint(0,150),15+rng.randint(0,85),'allowed'))
        graph=RoadGraph(pts,edges)
        p=prepare_navigation(graph,pts)
        outgoing={node:[] for node in pts}
        for edge in edges:outgoing[edge.source].append(edge)
        expected=[]
        def brute(node,cost):
            if node==f'n{count-1}':
                expected.append(cost);return
            for e in outgoing[node]:brute(e.target,cost+micro(e))
        brute('n0',0)
        optimum=min(expected)
        for mode in ('dijkstra','astar','alt'):
            actual=p.route('n0',f'n{count-1}',mode=mode)
            cursor='n0';cost=0
            for name in actual.edge_ids:
                edge=p.source_edges[name]
                if edge.source!=cursor:
                    errors.append({'case':case,'mode':mode,'problem':'disconnected route'})
                cursor=edge.target;cost+=micro(edge)
            if cursor!=f'n{count-1}' or cost!=optimum or abs(actual.estimated_seconds*1000000-optimum)>.01:
                errors.append({'case':case,'mode':mode,'cost':cost,'expected':optimum})
            runs+=1
    return {'category':'independent_routing_oracle','graphs':100,'route_executions':runs,'failures':errors[:50]}

def recovery_oracle():
    failures=[];journeys=0;bad_fixes=0
    for direction in (0,90,180,270):
        east,north=sin(radians(direction)),cos(radians(direction))
        def coords(dist):
            return (51.5+degrees(dist*north/EARTH),
                    -.12+degrees(dist*east/(EARTH*cos(radians(51.5)))))
        pts={'start':coords(0),'end':coords(1000)}
        graph=RoadGraph(pts,[RoadEdge('road','start','end',1000,40,'allowed')])
        p=prepare_navigation(graph,pts)
        for gap in (12,60,240):
            for burst in (0,2,5):
                for opposite_heading in (False,True):
                    key=f'{direction}:{gap}:{burst}:{opposite_heading}'
                    g=RecoveringGpsJourney(p,'road',900000)
                    def f(x,t,accuracy=2,heading=None):
                        lat,lon=coords(x)
                        return Fix(lat,lon,t,accuracy,10,heading,
                                   5 if heading is not None else None)
                    for t,x in ((1,400),(2,402),(3,404)):
                        initial=g.observe(f(x,t),t)
                    if initial.status!='tracking':
                        failures.append({'case':key,'reason':'startup '+initial.status})
                        continue
                    trusted=g.snapshot;g.poll(gap+3)
                    if g.guidance_available(gap+3):
                        failures.append({'case':key,'reason':'guidance while GPS missing'})
                    for i in range(burst):
                        t=gap+4+i
                        bad=g.observe(f(460,t,150),t)
                        if bad.guidance_available or g.snapshot!=trusted:
                            failures.append({'case':key,'reason':'bad input changed trusted navigation'})
                        bad_fixes+=1
                    begin=gap+5+burst
                    for i in range(3):
                        t=begin+i
                        angle=(direction+180)%360 if opposite_heading else None
                        result=g.observe(f(470+i,t,heading=angle),t)
                    if opposite_heading:
                        if result.guidance_available or g.snapshot!=trusted:
                            failures.append({'case':key,'reason':'opposing direction accepted'})
                    else:
                        if result.status!='recovered' or not result.guidance_available:
                            failures.append({'case':key,'reason':'could not confirm same-road recovery: '+result.status})
                    journeys+=1
    return {'category':'compound_gps_recovery','journey_cases':journeys,
            'poor_signal_observations':bad_fixes,'failures':failures[:50]}
