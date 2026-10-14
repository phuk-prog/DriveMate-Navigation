"""Actual larger-map engine runs; distance objective and service timings explicit."""
import json
import subprocess
import time
from pathlib import Path
from benchmarks.route_quality_fixture import PROTOCOL,judge_route,controls
from benchmarks.expanded_comparison import gh_route,shape_roads,route_shape,endpoint_check
from benchmarks.cloud_reference import call,parse
from benchmarks.whole_drive_reference import ways
from engine.routing import RouteNotFound


def turns(engine,raw,p=None,route=None):
    if engine=='drivemate':
        values=[x.manoeuvre for x in p.junctions(route)]
        return ['left' if x.endswith('left') else 'right' for x in values if x.endswith(('left','right'))]
    if engine=='graphhopper':
        signs=[x['sign'] for x in raw['paths'][0]['instructions']]
        return ['left' if s<0 else 'right' for s in signs if s in (-3,-2,-1,1,2,3)]
    if engine.startswith('osrm'):
        manoeuvres=[x['maneuver'] for l in raw['routes'][0]['legs'] for x in l['steps']]
        return [('left' if 'left' in m['modifier'] else 'right') for m in manoeuvres
                if m.get('type') not in ('depart','arrive') and
                ('left' in m.get('modifier','') or 'right' in m.get('modifier',''))]
    if engine=='valhalla':
        types=[x['type'] for l in raw['trip']['legs'] for x in l['maneuvers']]
        return ['right' if t in (9,10,11) else 'left' for t in types if t in (9,10,11,14,15,16)]
    return None


def query(engine,data,p,c,http,binary):
    raw=None;route=None;no_route=False
    if engine=='drivemate':
        try:
            route=p.route('osm:'+str(c['start']),'osm:'+str(c['end']));path=ways(route.edge_ids)
        except RouteNotFound:path=None;no_route=True
    elif engine=='graphhopper':raw,path,no_route,_=gh_route(http,data,c)
    elif engine in ('osrm','osrm-ch','valhalla'):
        raw=call(engine,p,c['start'],c['end']);path,_,no_route=parse(engine,p,raw)
    else:
        if engine=='routingkit':
            from benchmarks.routingkit_reference import execute
            path=execute(binary,p,'osm:'+str(c['start']),'osm:'+str(c['end']))
        else:
            from benchmarks.pgrouting_reference import execute
            path=execute(p,'osm:'+str(c['start']),'osm:'+str(c['end']))
        no_route=path is None
    return path,no_route,raw,route


def run(engine,data,out,p,*,http=None,binary=None):
    rows=[];out=Path(out)
    for c in data['quality_cases']:
        raw=None
        try:
            started=time.perf_counter_ns()
            path,no_route,raw,route=query(engine,data,p,c,http,binary)
            elapsed=(time.perf_counter_ns()-started)/1e6
            geometry_status=None
            if raw is not None and not no_route:path,geometry_status=shape_roads(data,route_shape(engine,raw))
            row=judge_route(data,c,path,no_route)
            if geometry_status=='fail':row.update(status='fail',issue='Independent geometry proves prohibited direction/access')
            if raw is not None and path is not None:
                check=endpoint_check(engine,raw,data,c)
                if not check or not check['within_2m']:row.update(status='unresolved',issue='Endpoint snap exceeds exact-node protocol')
            row['response_ms']=elapsed
            actual=None
            if c['expected_turns'] is not None:
                actual=turns(engine,raw,p,route) if engine not in ('routingkit','pgrouting') else None
                row['instruction_status']=('not_supported' if actual is None else
                    'unresolved' if row['status']!='pass' else 'pass' if actual==c['expected_turns'] else 'fail')
            else:row['instruction_status']=None
            row['actual_turns']=actual;row['actual_ways']=path
        except (OSError,ValueError,KeyError,IndexError,TypeError,AttributeError,subprocess.SubprocessError) as exc:
            row={'status':'unresolved','issue':f'{type(exc).__name__}: {str(exc)[:180]}',
                 'instruction_status':'unresolved' if c['expected_turns'] is not None else None}
        if raw is not None:(out/(c['id'].replace('/','_')+'_quality_route.json')).write_text(json.dumps(raw,indent=2))
        rows.append(c|row)
    record={'engine':engine,'protocol':PROTOCOL,'fresh_execution':True,
            'dataset_sha256':data['dataset_sha256'],
            'commit_sha':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'cohort':'supplied-transition-algorithm' if engine in ('routingkit','pgrouting') else 'native-road-import',
            'cases':rows,'judge_controls':controls(data),
            'limits':['Distance above independently shortest legal path, not identical vendor costing',
                      'Response timings include wrapper/process/serialization overhead; jobs use different hosts',
                      'Stateless missed-turn restart, not live off-route detection or incoming restriction history',
                      'Fixed 90-degree turn families only; no lane occupancy, spoken timing or arrival rank']}
    (out/'quality.json').write_text(json.dumps(record,indent=2)+'\n')
    if engine=='graphhopper':
        from benchmarks.route_quality_speed import paired
        (out/'quality_speed.json').write_text(json.dumps(paired(data,p,http),indent=2)+'\n')
    print(json.dumps({'quality_engine':engine,'cases':len(rows),'failed':sum(r['status']=='fail' for r in rows),
                      'unresolved':sum(r['status']=='unresolved' for r in rows)}))
    return record
