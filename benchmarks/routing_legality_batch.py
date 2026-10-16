"""ROUTE-002: frozen synthetic motorcar access, turn and rerouting controls."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import socket
from time import monotonic,sleep
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request

from benchmarks.routing_trial import judge as judge_geometry, VERSIONS
from benchmarks.routing_references import OPENER,route_request,route_points
from engine import shortest_route,RouteNotFound
from map_data import Provenance,import_osm_xml

ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'benchmarks/fixtures/synthetic-route-002.xml'
ORACLE=ROOT/'benchmarks/fixtures/synthetic-route-002.json'


def load_cases():return json.loads(ORACLE.read_text())['cases']


def judge_case(case,result):
    status=result['status']
    row={'case_id':case['id'],'cohort':case['cohort'],'expected':case['expected'],'actual':status}
    if status in ('UNRESOLVED','UNSUPPORTED'):
        return {**row,'outcome':status,'reason':result['reason'],'checks':{}}
    if status not in ('ROUTE','NO_ROUTE'):raise ValueError('Unknown engine outcome')
    if case['expected']=='NO_ROUTE':
        checks={'no_route_returned':status=='NO_ROUTE'}
        return {**row,'outcome':'PASS' if all(checks.values()) else 'FAIL','checks':checks,
                'failures':[] if all(checks.values()) else ['route_returned_for_unreachable_exact_destination']}
    if status=='NO_ROUTE':
        return {**row,'outcome':'FAIL','checks':{'required_route_returned':False},'failures':['missing_required_route']}
    variants=case.get('accepted_paths',[case['path']])
    alternatives=[judge_geometry({**case,'path':path},result['points']) for path in variants]
    judged=next((r for r in alternatives if r['outcome']=='PASS'),min(alternatives,key=lambda r:len(r['failures'])))
    return {**judged,**row,'accepted_legal_variants':len(variants)}


def report(system,rows):
    return {'test_id':'ROUTE-002','classification':'synthetic analytical motorcar access/turn/rerouting only',
            'system':system,'version':VERSIONS[system],
            'execution':'actual_local_python' if system=='DMN' else 'actual_live_loopback',
            'map_sha256':sha256(MAP.read_bytes()).hexdigest(),
            'oracle_sha256':sha256(ORACLE.read_bytes()).hexdigest(),
            'independent_real_world_legality':False,'cases':rows}


def run_dmn():
    data=import_osm_xml(MAP.read_bytes(),provenance=Provenance(
        'synthetic ROUTE-002','synthetic-v1','hand-authored analytical controls',
        'Synthetic OSM format; no OpenStreetMap contributor road data used'))
    rows=[]
    for case in load_cases():
        source='osm:'+str(case['source_node']);target='osm:'+str(case['target_node'])
        try:
            route=shortest_route(data.graph,source,target,incoming_edge_id=case.get('incoming_edge'),blocked_edges=case.get('blocked_edges',[]))
            points=[data.coordinates[source]]+[data.coordinates[data.graph.edges[e].target] for e in route.edge_ids]
            result={'status':'ROUTE','points':points}
        except RouteNotFound:result={'status':'NO_ROUTE'}
        rows.append(judge_case(case,result))
    return report('DMN',rows)


def classify_response(system,http_status,raw):
    """Only documented route-search failures count as NO_ROUTE, never generic HTTP failures."""
    if len(raw)>200000:raise ValueError('Oversized route response')
    try:data=json.loads(raw)
    except (ValueError,UnicodeDecodeError):data={}
    if system=='OSRM' and http_status in (200,400) and data.get('code')=='NoRoute':return {'status':'NO_ROUTE','provider_reason':'NoRoute'}
    if system=='Valhalla' and http_status==400 and data.get('error_code')==442:return {'status':'NO_ROUTE','provider_reason':'Valhalla442'}
    if system=='GraphHopper' and http_status==400 and any('ConnectionNotFoundException' in str(h.get('details','')) for h in data.get('hints',[])):
        return {'status':'NO_ROUTE','provider_reason':'ConnectionNotFoundException'}
    if system=='openrouteservice' and http_status==404 and data.get('error',{}).get('code')==2009:
        return {'status':'NO_ROUTE','provider_reason':'ORS2009'}
    if system=='BRouter' and http_status==400:
        text=raw.decode('utf-8',errors='replace').strip()
        if text.startswith(('no track found','start island detected for section ','target island detected for section ')):
            return {'status':'NO_ROUTE','provider_reason':text[:120]}
    if http_status!=200:
        return {'status':'UNRESOLVED','reason':f'HTTP{http_status}; no documented no-route output: '+raw.decode('utf-8',errors='replace')[:250]}
    if system=='BRouter':
        lines=[f['geometry']['coordinates'] for f in data.get('features',[]) if f.get('geometry',{}).get('type')=='LineString']
        if len(lines)!=1:return {'status':'UNRESOLVED','reason':'No single complete BRouter route geometry'}
        points=[[p[1],p[0]] for p in lines[0]]
    else:
        try:points=route_points(system,data)
        except (KeyError,TypeError,ValueError) as exc:
            return {'status':'UNRESOLVED','reason':'Unalignable route geometry: '+str(exc)[:160]}
    return {'status':'ROUTE','points':points}


def wait_reference(system):
    if system=='BRouter':
        deadline=monotonic()+30
        while monotonic()<deadline:
            try:
                with socket.create_connection(('127.0.0.1',17777),timeout=1):return
            except OSError:sleep(.5)
        raise TimeoutError('BRouter startup unavailable')
    elif system=='OSRM':
        from benchmarks.osrm_live_reference import wait_for_local_router
        wait_for_local_router()
    elif system=='Valhalla':
        from benchmarks.valhalla_live_reference import wait_for_local_router
        wait_for_local_router()
    elif system=='GraphHopper':
        from benchmarks.graphhopper_live_reference import wait_for_graphhopper
        wait_for_graphhopper()
    elif system=='openrouteservice':
        from benchmarks.ors_snap_reference import wait_for_ors
        wait_for_ors()
    else:raise ValueError('Unknown live reference')


def run_external(system):
    wait_reference(system);rows=[]
    for case in load_cases():
        if case['cohort']=='dmn-state':
            rows.append(judge_case(case,{'status':'UNSUPPORTED','reason':'Current integrated endpoint has no equivalent incoming-edge or arbitrary blocked-link state interface.'}));continue
        if system=='BRouter':
            query=urlencode({'lonlats':'|'.join(f'{p[1]},{p[0]}' for p in (case['start'],case['end'])),'profile':'car-vario','alternativeidx':0,'format':'geojson'})
            request=Request('http://127.0.0.1:17777/brouter?'+query)
        else:request=route_request(system,case['start'],case['end'])
        try:
            with OPENER.open(request,timeout=30) as response:
                status=response.status;raw=response.read(200001)
        except HTTPError as exc:status=exc.code;raw=exc.read(200001)
        result=classify_response(system,status,raw)
        row=judge_case(case,result)
        if result.get('provider_reason'):row['provider_reason']=result['provider_reason']
        rows.append(row)
    return report(system,rows)


def scorecard(reports):
    ids=[c['id'] for c in load_cases()];shared=[c['id'] for c in load_cases() if c['cohort']=='shared-static']
    supplied={}
    for r in reports:
        if r['system'] in supplied or r['test_id']!='ROUTE-002':raise ValueError('Duplicate or wrong trial')
        if r['map_sha256']!=sha256(MAP.read_bytes()).hexdigest() or r['oracle_sha256']!=sha256(ORACLE.read_bytes()).hexdigest() or [c['case_id'] for c in r['cases']]!=ids:raise ValueError('Mismatched frozen cohort')
        if r['execution']!=('actual_local_python' if r['system']=='DMN' else 'actual_live_loopback'):raise ValueError('Not actual execution')
        supplied[r['system']]=r
    roster=['DMN']+[r['name'] for r in json.loads((ROOT/'config/dmn-engine-first-programme.json').read_text())['reference_families']]
    if not set(supplied)<=set(roster):raise ValueError('Unknown engine')
    rows=[]
    for name in roster:
        r=supplied.get(name)
        reason=('No ROUTE-002 execution supplied for runnable reference' if name in VERSIONS else
                'Executable app/native routing harness not implemented' if name in ('OsmAnd','Organic Maps') else
                'No permitted automated routing interface established' if name=='Waze' else
                'No configured permitted access and same-fixture interface')
        cases=r['cases'] if r else [{'case_id':cid,'outcome':'NOT_RUN','reason':reason} for cid in ids]
        judged=[c for c in cases if c['case_id'] in shared]
        complete=r and all(c['outcome'] in ('PASS','FAIL') for c in judged)
        passed=sum(c['outcome']=='PASS' for c in judged)
        rows.append({'system':name,'rank':None,'passed_shared':passed,'failed_shared':sum(c['outcome']=='FAIL' for c in judged),
                     'judged_shared_cases':sum(c['outcome'] in ('PASS','FAIL') for c in judged),
                     'score_out_of_ten':round(10*passed/len(shared),3) if complete else None,
                     'all_cases_passed':sum(c['outcome']=='PASS' for c in cases),'unsupported':sum(c['outcome']=='UNSUPPORTED' for c in cases),
                     'unresolved':sum(c['outcome']=='UNRESOLVED' for c in cases),'not_run':sum(c['outcome']=='NOT_RUN' for c in cases),'cases':cases})
    rows.sort(key=lambda r:(r['score_out_of_ten'] is None,-(r['score_out_of_ten'] or 0),r['system']))
    previous=None
    for i,r in enumerate([r for r in rows if r['score_out_of_ten'] is not None],1):
        if r['score_out_of_ten']!=previous:rank=i
        r['rank']=rank;previous=r['score_out_of_ten']
    return {'test_id':'ROUTE-002','formula':'10 * passed / five frozen shared-static cases; ties share rank; incomplete shared cohorts unranked',
            'ranked_case_ids':shared,'state_cases_ranked_with_static':False,'rows':rows}


def main():
    p=argparse.ArgumentParser();p.add_argument('--engine',choices=list(VERSIONS));p.add_argument('--reports',nargs='*',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if not a.output.resolve().is_relative_to((ROOT/'results').resolve()):raise ValueError('Ephemeral reports stay under results')
    result=(run_dmn() if a.engine=='DMN' else run_external(a.engine)) if a.engine else scorecard([json.loads(p.read_text()) for p in a.reports or []])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
