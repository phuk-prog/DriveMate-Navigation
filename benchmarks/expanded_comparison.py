"""Execute actual backends on held-out authored maps; preserve raw evidence.

Algorithms consuming DriveMate-imported transitions are labelled separately.
No fake competitor output, performance winner, lane or live recovery claim.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time
from urllib.parse import urlencode

from benchmarks.expanded_fixture import suite, judge, legal_paths, mutation_controls
from benchmarks.whole_drive import prepared
from benchmarks.whole_drive_reference import ways, post, gpx
from benchmarks.import_restriction_compare import PIN, port, request, decode_response
from benchmarks.cloud_reference import call, parse, call_match, parse_match, polyline6
from engine.routing import RouteNotFound

LABELS = {'drivemate':'DriveMate', 'graphhopper':'GraphHopper', 'osrm':'OSRM MLD',
          'osrm-ch':'OSRM CH', 'valhalla':'Valhalla', 'routingkit':'RoutingKit CH', 'pgrouting':'pgRouting'}


@contextmanager
def graphhopper(jar, data, out):
    if hashlib.sha512(jar.read_bytes()).hexdigest()!=PIN:
        raise ValueError('GraphHopper runtime checksum mismatch')
    http,admin=port(),port()
    osm=out/'expanded.osm';osm.write_bytes(data['osm'])
    config=out/'config.yml'
    config.write_text(f'''graphhopper:
  datareader.file: "{osm.as_posix()}"
  graph.location: "{(out/'cache').as_posix()}"
  graph.encoded_values: car_access,car_average_speed,road_access,osm_way_id
  import.osm.ignored_highways: footway,construction,cycleway,path,steps
  prepare.min_network_size: 0
  profiles:
    - name: car
      turn_costs:
        vehicle_types: [motorcar, motor_vehicle]
        u_turn_costs: 60
      custom_model_files: [car.json]
  profiles_ch: []
  profiles_lm: []
server:
  application_connectors:
    - type: http
      port: {http}
      bind_host: 127.0.0.1
  admin_connectors:
    - type: http
      port: {admin}
      bind_host: 127.0.0.1
  request_log:
    appenders: []
''')
    with (out/'server.log').open('w') as log:
        proc=subprocess.Popen(['java','-Xmx256m','-jar',str(jar.resolve()),'server',str(config)],
                              stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+60
            while proc.poll() is None and time.monotonic()<deadline:
                try:
                    info=request(http,'/info')
                    if info.get('version')=='11.1': break
                except (OSError,ValueError): pass
                time.sleep(.2)
            else: raise RuntimeError('GraphHopper unavailable or version mismatch')
            yield http
        finally:
            proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill();proc.wait()


def distance(a,b):
    return math.hypot((a[0]-b[0])*111195.0802,
                      (a[1]-b[1])*111195.0802*math.cos(math.radians(a[0])))


def shape_roads(data,points):
    """Attribute geometry to AUTHOR segments, independent of candidate importer.

    Densify at <=2m, tolerate <=2m quantization/simplification error. Direction
    and access are checked even when a single roundabout way ID hides reversal.
    Off-map or ambiguous geometry is unresolved rather than declared illegal.
    """
    if not points or len(points)<2: return None,'unresolved'
    anchor=next(iter(data['nodes'].values()))
    east=111195.0802*math.cos(math.radians(anchor[0]))
    def xy(p): return ((p[1]-anchor[1])*east,(p[0]-anchor[0])*111195.0802)
    segments=[];buckets={}
    for wid,way in data['ways'].items():
        for a,b in zip(way['nodes'],way['nodes'][1:]):
            left,right=xy(data['nodes'][a]),xy(data['nodes'][b])
            dx,dy=right[0]-left[0],right[1]-left[1]
            segment=(wid,left,dx,dy,dx*dx+dy*dy,way['tags'].get('access')=='no')
            segments.append(segment)
            for ix in range(math.floor((min(left[0],right[0])-2)/100),math.floor((max(left[0],right[0])+2)/100)+1):
                for iy in range(math.floor((min(left[1],right[1])-2)/100),math.floor((max(left[1],right[1])+2)/100)+1):
                    buckets.setdefault((ix,iy),[]).append(segment)
    selected=[]
    for l,r in zip(points,points[1:]):
        a,b=xy(l),xy(r);dx,dy=b[0]-a[0],b[1]-a[1]
        length=math.hypot(dx,dy)
        if length<.1: continue
        count=math.ceil(length/2)
        for i in range(count):
            q=(i+.5)/count;mx,my=a[0]+q*dx,a[1]+q*dy
            candidates=[]
            for wid,origin,sx,sy,sq,blocked in buckets.get((math.floor(mx/100),math.floor(my/100)),()):
                t=((mx-origin[0])*sx+(my-origin[1])*sy)/sq
                if not -.002<=t<=1.002: continue
                dist=math.hypot(mx-origin[0]-t*sx,my-origin[1]-t*sy)
                alignment=(dx*sx+dy*sy)/(length*math.sqrt(sq))
                if dist<=2 and abs(alignment)>.8:
                    candidates.append((dist,wid,alignment,blocked))
            if not candidates: return None,'unresolved'
            candidates.sort();best=candidates[0]
            if len(candidates)>1 and candidates[1][0]-best[0]<.15 and candidates[1][1]!=best[1]:
                return None,'unresolved'
            if best[2]<0 or best[3]: return None,'fail'
            if not selected or selected[-1]!=best[1]: selected.append(best[1])
    return (selected,'pass') if selected else (None,'unresolved')


def route_shape(engine,raw):
    if engine=='graphhopper':
        coords=raw.get('paths',[{}])[0].get('points',{}).get('coordinates',())
        return [(x[1],x[0]) for x in coords]
    if engine.startswith('osrm'):
        coords=raw.get('routes',[{}])[0].get('geometry',{}).get('coordinates',())
        return [(x[1],x[0]) for x in coords]
    return [p for leg in raw.get('trip',{}).get('legs',()) for p in polyline6(leg['shape'])]


def endpoint_check(engine, response, data, case):
    """Do not award path success when service snapped to a different endpoint."""
    if engine=='graphhopper':
        paths=response.get('paths',())
        if not paths: return None
        points=paths[0].get('points',{}).get('coordinates')
        if not points: return None
        ends=[(v[1],v[0]) for v in (points[0],points[-1])]
    elif engine.startswith('osrm'):
        routes=response.get('routes',())
        if not routes: return None
        points=routes[0].get('geometry',{}).get('coordinates')
        if not points: return None
        ends=[(v[1],v[0]) for v in (points[0],points[-1])]
    else:
        legs=response.get('trip',{}).get('legs',())
        if not legs: return None
        ends=[polyline6(legs[0]['shape'])[0],polyline6(legs[-1]['shape'])[-1]]
    errors=[distance(v,data['nodes'][n]) for v,n in zip(ends,(case['start'],case['end']))]
    return {'within_2m':max(errors)<=2,'errors_m':errors}


def gh_route(http, data, case, *, instructions=True):
    params=[('point',','.join(map(str,data['nodes'][n]))) for n in (case['start'],case['end'])]
    params += [('profile','car'),('details','osm_way_id'),('instructions',str(instructions).lower()),('points_encoded','false')]
    raw=request(http,'/route?'+urlencode(params))
    path,unreachable=decode_response(raw)
    # Failure to locate an endpoint is not proved network disconnection.
    exits=tuple(i.get('exit_number') for i in raw.get('paths',[{}])[0].get('instructions',())
                if i.get('sign')==6)
    return raw,path,unreachable,exits


def clean_trace(data, case):
    """Coordinate-only stream generated from independent allowed roads, not router output."""
    allowed=legal_paths(data,case)
    if not allowed: raise ValueError('Cannot generate a clean legal trace for no-route case')
    path=allowed[0];samples=[];t=100.
    node=case['start']
    for path_index,wid in enumerate(path):
        refs=data['ways'][wid]['nodes']
        # All cases start at complete ways or within a multi-segment way.
        at=refs.index(node)
        target=case['end'] if path_index==len(path)-1 else data['ways'][path[path_index+1]]['nodes'][0]
        end_at=refs.index(target,at+1)
        for a,b in zip(refs[at:end_at],refs[at+1:end_at+1]):
            left,right=data['nodes'][a],data['nodes'][b]
            count=max(3,math.ceil(distance(left,right)/25))
            for k in range(count):
                q=.1+.8*k/(count-1)
                samples.append({'lat':left[0]+q*(right[0]-left[0]),
                                'lon':left[1]+q*(right[1]-left[1]),'t':t,
                                'accuracy_m':3,'injected_fault':False})
                t+=1.
            node=b
    if not 3<=len(samples)<=100: raise ValueError('Trace exceeds common adapter bound')
    return list(path),samples


def candidate_trace(p, samples):
    from gps.matching import Matcher, Fix
    matcher=Matcher(p);selected=[];rejected=[]
    for i,s in enumerate(samples):
        m=matcher.observe(Fix(s['lat'],s['lon'],s['t'],3),s['t'])
        if m.status=='matched': selected.append(m.road)
        else: rejected.append({'sample':i,'status':m.status})
    return ways(selected),rejected


def execute(engine, data, out, *, http=None, binary=None, version=None):
    p=prepared(data['osm']);rows=[]
    for c in data['cases']:
        raw=None;exits=None;no_route=False;observed=None;error=None
        try:
            if engine=='drivemate':
                try:
                    r=p.route('osm:'+str(c['start']),'osm:'+str(c['end']))
                    observed=ways(r.edge_ids)
                    exits=tuple(x.exit_number for x in p.roundabouts(r))
                except RouteNotFound: no_route=True
            elif engine=='graphhopper':
                raw,observed,no_route,exits=gh_route(http,data,c)
            elif engine in ('osrm','osrm-ch','valhalla'):
                raw=call(engine,p,c['start'],c['end'])
                observed,exits,no_route=parse(engine,p,raw)
            elif engine=='routingkit':
                from benchmarks.routingkit_reference import execute as run
                observed=run(binary,p,'osm:'+str(c['start']),'osm:'+str(c['end']))
                no_route=observed is None
            else:
                from benchmarks.pgrouting_reference import execute as run
                observed=run(p,'osm:'+str(c['start']),'osm:'+str(c['end']))
                no_route=observed is None
            declared=observed
            geometry_status=None
            if raw is not None and not no_route:
                observed,geometry_status=shape_roads(data,route_shape(engine,raw))
            result=judge(data,c,observed,no_route)
            result['native_declared_ways']=declared
            result['independent_geometry_status']=geometry_status
            if geometry_status=='fail':
                result['status']='fail';result['issue']='Independent geometry proves reversed one-way or prohibited-access traversal'
            if raw is not None:
                (out/(c['id'].replace('/','_')+'_route.json')).write_text(json.dumps(raw,indent=2))
                endpoint=endpoint_check(engine,raw,data,c)
                result['endpoint_check']=endpoint
                if (observed is not None or geometry_status=='fail') and (endpoint is None or not endpoint['within_2m']):
                    result['status']='unresolved'
                    result['issue']='Endpoint snapping/geometry differs from exact-node protocol (>2m or unavailable)'
            result['exit_status']=('not_supported' if exits is None else
                'unresolved' if result['status']=='unresolved' else
                'pass' if exits==(c['exit_number'],) else 'fail') if c['exit_number'] is not None else None
            result['actual_exit_numbers']=exits
        except (OSError,ValueError,KeyError,IndexError,subprocess.SubprocessError) as exc:
            error=f'{type(exc).__name__}: {str(exc)[:220]}'
            result={'status':'unresolved','issue':error,'exit_status':'unresolved' if c['exit_number'] else None}
        rows.append({**c,**result})
    traces=[]
    supported=engine in ('drivemate','graphhopper','osrm','osrm-ch','valhalla')
    for c in data['cases']:
        if c['id'].split('/')[-1] not in ('no_chained_turn','only_chained_turn',
                                         'no_inside_via_reset','asymmetric_ring_exit_5','compound_no_only_detour'): continue
        if not supported:
            traces.append({'case':c['id'],'status':'not_supported','issue':'Routing algorithm has no trace interface'})
            continue
        expected,samples=clean_trace(data,c)
        try:
            rejected=[]
            if engine=='drivemate': actual,rejected=candidate_trace(p,samples)
            elif engine=='graphhopper':
                raw=post(http,gpx(samples));actual,_=decode_response(raw)
            else:
                raw=call_match(engine,p,samples);actual=parse_match(engine,p,raw)
            if engine!='drivemate':
                (out/(c['id'].replace('/','_')+'_match.json')).write_text(json.dumps(raw,indent=2))
            status='unresolved' if actual is None else 'pass' if actual==expected else 'fail'
            issue=None if status=='pass' else 'Unmappable output' if actual is None else 'Wrong observed road sequence'
        except (OSError,ValueError,KeyError,IndexError) as exc:
            actual=None;rejected=[];status='unresolved';issue=f'{type(exc).__name__}: {str(exc)[:220]}'
        traces.append({'case':c['id'],'split':c['split'],'status':status,'issue':issue,
            'sample_count':len(samples),'input_sha256':hashlib.sha256(json.dumps(samples,sort_keys=True).encode()).hexdigest(),
            'expected_ways':expected,'actual_ways':actual,'rejected_clean_samples':rejected,
            'scope':'Complete observed sequence only; per-fix rejection diagnostics separate; coordinate-only candidate streaming vs external batch; no controller/recovery ranking'})
    result={'engine':engine,'label':LABELS[engine],'version':version,'fresh_execution':True,
        'driving_side':data['driving_side'],
        'dataset_sha256':data['dataset_sha256'],'protocol':data['protocol'],
        'commit_sha':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'cohort':'supplied-transition-algorithm' if engine in ('routingkit','pgrouting') else 'native-road-import',
        'route_cases':rows,'clean_traces':traces,'mutation_controls':mutation_controls(data),
        'limits': ['Synthetic authored permissions; no real-world legal truth',
                   'Route score is legal reachability/destination, not cost optimality or speed',
                   'Replan starts fresh with no incoming-road history',
                   'GPS loss/recovery, spiral lane occupancy and voice timing not supported by common interface',
                   'Turn/access parsing supplied to RoutingKit/pgRouting by candidate importer; separate cohort']}
    (out/'expanded.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'engine':LABELS[engine],'routes':len(rows),
        'passed':sum(x['status']=='pass' for x in rows),'failed':sum(x['status']=='fail' for x in rows),
        'unresolved':sum(x['status']=='unresolved' for x in rows),'traces':len(traces)}))
    from benchmarks.fault_comparison import run as run_faults
    run_faults(engine,data,out,p,http=http)
    from benchmarks.route_quality import run as run_quality
    run_quality(engine,data,out,p,http=http,binary=binary)
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--engine',choices=LABELS,required=True)
    ap.add_argument('--jar',type=Path);ap.add_argument('--binary',type=Path);ap.add_argument('--version',required=True)
    args=ap.parse_args();data=suite()
    out=Path('results/expanded/'+args.engine).resolve();out.mkdir(parents=True,exist_ok=True)
    if args.engine=='graphhopper':
        with graphhopper(args.jar,data,out) as http:
            execute(args.engine,data,out,http=http,version=args.version)
    else:
        if args.engine in ('osrm','osrm-ch','valhalla'):
            p=prepared(data['osm']);case=data['cases'][0];deadline=time.monotonic()+240
            while True:
                try:
                    raw=call(args.engine,p,case['start'],case['end'])
                    if raw.get('routes') or raw.get('trip',{}).get('legs'): break
                except (OSError,ValueError): pass
                if time.monotonic()>deadline: raise RuntimeError('Expanded service did not become map-ready')
                time.sleep(1)
        execute(args.engine,data,out,binary=args.binary,version=args.version)


if __name__=='__main__': main()
