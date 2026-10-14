"""Independently oracled synthetic navigation stress tests. No real GPS or competitor claims."""
from math import sin, cos, radians, degrees, pi
from pathlib import Path
import json
from engine.routing import RoadEdge, RoadGraph, Route, RouteNotFound
from engine.reconciled import prepare_navigation
from gps.matching import EARTH, Fix, Matcher

def xy(x,y,lat=51.5,lon=-.12):
    return lat+degrees(y/EARTH),lon+degrees(x/(EARTH*cos(radians(lat))))

def error(rows,case,message):
    if len(rows)<50:rows.append({'case':case,'failure':str(message)})

def ring(n,radius,extra=False):
    pts={'origin':xy(radius+120,0)}
    for i in range(n):
        theta=2*pi*i/n
        pts['r'+str(i)]=xy(radius*cos(theta),-radius*sin(theta))
        if i:pts['d'+str(i)]=xy((radius+120)*cos(theta),-(radius+120)*sin(theta))
    roads=[RoadEdge('entry','origin','r0',120,30,'allowed')]
    roads += [RoadEdge('ring'+str(i),'r'+str(i),'r'+str((i+1)%n),
                       2*radius*sin(pi/n),30,'allowed','roundabout') for i in range(n)]
    roads += [RoadEdge('exit'+str(i),'r'+str(i),'d'+str(i),120,30,'allowed') for i in range(1,n)]
    if extra:roads.append(RoadEdge('extra','r0','r2',120,30,'allowed','roundabout'))
    return prepare_navigation(RoadGraph(pts,roads),pts)

def roundabout_sweep():
    failures=[];exits=0;unsupported=0
    for n in range(3,13):
        for radius in (15,30,65,140,300):
            p=ring(n,radius)
            for ordinal in range(1,n):
                case=f'{n}:{radius}:{ordinal}'
                route=p.route('origin','d'+str(ordinal))
                expected=('entry',)+tuple('ring'+str(i) for i in range(ordinal))+('exit'+str(ordinal),)
                if route.edge_ids!=expected:error(failures,case,'wrong road sequence')
                guidance=p.roundabouts(route)
                if len(guidance)!=1 or guidance[0].exit_number!=ordinal or guidance[0].status!='numbered':
                    error(failures,case,'incorrect roundabout exit')
                if any(j.candidate_lanes or j.direct_connections for j in p.junctions(route)):
                    error(failures,case,'invented lane evidence')
                exits+=1
            p=ring(n,radius,extra=True)
            route=Route(('entry','ring0','ring1','exit2'),0,0)
            guidance=p.roundabouts(route)
            if len(guidance)!=1 or guidance[0].exit_number is not None or guidance[0].status!='unsupported_roundabout_topology':
                error(failures,f'{n}:{radius}:extra','unsafe roundabout numbering on non-simple topology')
            unsupported+=1
    return dict(category='roundabout_geometry',exit_cases=exits,unsupported_topologies=unsupported,failures=failures)

def junction_sweep():
    failures=[];legal=0;prohibited=0
    for arms in range(3,13):
        for scale in (50,100,200):
            pts={'start':xy(0,-150),'centre':xy(0,0)}
            edges=[RoadEdge('in','start','centre',150,30,'allowed')]
            for i in range(arms):
                bearing=radians(-150+300*i/(arms-1))
                pts['dest'+str(i)]=xy(scale*sin(bearing),scale*cos(bearing))
                edges.append(RoadEdge('out'+str(i),'centre','dest'+str(i),scale,30,'allowed'))
            banned=arms//2
            p=prepare_navigation(RoadGraph(pts,edges,(('in','out'+str(banned)),)),pts)
            for i in range(arms):
                case=f'{arms}:{scale}:{i}'
                if i==banned:
                    try:p.route('start','dest'+str(i))
                    except RouteNotFound:prohibited+=1
                    else:error(failures,case,'illegal turn accepted')
                else:
                    route=p.route('start','dest'+str(i))
                    if route.edge_ids!=('in','out'+str(i)):error(failures,case,'wrong exit arm')
                    instructions=p.junctions(route)
                    if len(instructions)!=1 or instructions[0].departure!='out'+str(i):
                        error(failures,case,'incorrect junction')
                    if any(j.candidate_lanes or j.direct_connections for j in instructions):
                        error(failures,case,'invented lanes')
                    legal+=1
    return dict(category='multi_arm_junctions',legal_turn_cases=legal,banned_turn_cases=prohibited,failures=failures)

def gps_sweep():
    failures=[];faults=0;controls=0
    for latitude in (-60,0,51.5,75):
        for heading in range(0,360,30):
            e,n=sin(radians(heading)),cos(radians(heading))
            def point(distance):
                return xy(e*distance,n*distance,latitude,10)
            pts={'start':point(0),'end':point(1000)}
            p=prepare_navigation(RoadGraph(pts,[RoadEdge('road','start','end',1000,50,'allowed')]),pts)
            for accuracy in (2,6,12):
                for kind in ('poor','stale','future','speed','old','jump','wrong_heading'):
                    m=Matcher(p)
                    a,b=point(500)
                    first=m.observe(Fix(a,b,1,accuracy,7),1)
                    if first.status!='matched':
                        error(failures,kind,'initial position failed')
                        continue
                    a,b=point(5100 if kind=='jump' else 505)
                    kwargs=dict(timestamp=2,accuracy_m=accuracy,speed_mps=7)
                    if kind=='poor':kwargs['accuracy_m']=150
                    if kind=='speed':kwargs['speed_mps']=90
                    if kind=='old':kwargs['timestamp']=1
                    if kind=='wrong_heading':
                        kwargs.update(bearing_degrees=(heading+180)%360,bearing_accuracy_degrees=5)
                    now=7 if kind=='stale' else 1 if kind=='future' else 2
                    r=m.observe(Fix(a,b,**kwargs),now)
                    expected=dict(poor='poor_accuracy',stale='stale_fix',future='future_fix',
                         speed='impossible_speed',old='out_of_order',jump='impossible_jump',
                         wrong_heading='direction_mismatch')[kind]
                    if r.status!=expected or m.last is not first:
                        error(failures,f'{latitude}:{heading}:{accuracy}:{kind}',r.status)
                    faults+=1
                    a,b=point(505)
                    valid=m.observe(Fix(a,b,2,accuracy,7),2)
                    if valid.status!='matched' or valid.road!='road':
                        error(failures,f'{latitude}:{heading}:{accuracy}:{kind}:valid',valid.status)
                    controls+=1
    return dict(category='gps_corruption',fault_cases=faults,valid_fix_controls=controls,failures=failures)

def run():
    from benchmarks.navigation_adversarial_routes import route_oracle, recovery_oracle
    checks=[roundabout_sweep(),junction_sweep(),gps_sweep(),route_oracle(),recovery_oracle()]
    result={'classification':'Executed synthetic candidate checks only; no physical GPS or consumer apps',
            'categories_executed':len(checks),'checks':checks,
            'failure_count':sum(len(c['failures']) for c in checks)}
    folder=Path('results/navigation_adversarial');folder.mkdir(parents=True,exist_ok=True)
    (folder/'report.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'categories':len(checks),'failures':result['failure_count'],
          'roundabouts':checks[0]['exit_cases'],'junctions':checks[1]['legal_turn_cases'],
          'gps_faults':checks[2]['fault_cases']}))
    return result

if __name__=='__main__':
    raise SystemExit(1 if run()['failure_count'] else 0)
