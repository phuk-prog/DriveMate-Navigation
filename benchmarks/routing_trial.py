"""ROUTE-001 synthetic one-way contract. No independent real-road evidence."""
import argparse
from hashlib import sha256
import json
from math import cos, radians, hypot, isfinite
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener
from benchmarks.osrm_live_reference import NoRedirect
from engine import shortest_route
from map_data import Provenance, import_osm_xml

ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'benchmarks/fixtures/synthetic-route-001.xml'
ORACLE=ROOT/'benchmarks/fixtures/synthetic-route-001.json'
VERSIONS={'DMN':'repository shortest_route','BRouter':'1.7.10 official release; car-vario defaults',
          'OSRM':'5.27.1; car.lua MLD','Valhalla':'3.9.1; auto; polyline6',
          'GraphHopper':'11.1 / Java25; car CH; full GeoJSON geometry',
          'openrouteservice':'10.1.0 / Java25; driving-car; fastest; GeoJSON; no CH/LM/core'}


def load_cases():
    return json.loads(ORACLE.read_text())['cases']


def xy(p):
    return ((p[1]-1)*111195*cos(radians(1)),(p[0]-1)*111195)


def judge(case,points):
    if not isinstance(points,list) or not 2<=len(points)<=2000:
        raise ValueError('Invalid route geometry')
    if any(len(p)!=2 or any(type(v) not in (float,int) or not isfinite(v) for v in p)
           or not -90<=p[0]<=90 or not -180<=p[1]<=180 for p in points):
        raise ValueError('Invalid route coordinate')
    path=list(map(xy,case['path'])); actual=list(map(xy,points))
    distance=lambda a,b:hypot(a[0]-b[0],a[1]-b[1])
    lengths=[distance(a,b) for a,b in zip(path,path[1:])]
    expected=sum(lengths)
    observed=sum(distance(a,b) for a,b in zip(actual,actual[1:]))
    def projection(p):
        options=[]; offset=0
        for a,b,length in zip(path,path[1:],lengths):
            dx,dy=b[0]-a[0],b[1]-a[1]
            t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(length*length)))
            options.append((distance(p,(a[0]+t*dx,a[1]+t*dy)),offset+t*length))
            offset+=length
        return min(options)
    projected=[projection(p) for p in actual]
    # Interior samples reject diagonal corner-cutting even if endpoints are on roads.
    samples=[projection((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))[0]
             for a,b in zip(actual,actual[1:]) for t in (.25,.5,.75)]
    checks={'endpoints_within_2m':distance(actual[0],path[0])<=2 and distance(actual[-1],path[-1])<=2,
            'geometry_on_declared_path':max([d for d,_ in projected]+samples)<=2,
            'forward_progress':all(b[1]>=a[1]-.5 for a,b in zip(projected,projected[1:])),
            'declared_path_length':abs(observed-expected)<=5}
    return {'case_id':case['id'],'outcome':'PASS' if all(checks.values()) else 'FAIL',
            'checks':checks,'failures':[k for k,v in checks.items() if not v],
            'expected_length_m':round(expected,3),'returned_length_m':round(observed,3)}


def report(system,rows):
    return {'test_id':'ROUTE-001','system':system,
            'version':VERSIONS[system],
            'execution':'actual_local_python' if system=='DMN' else 'actual_live_loopback',
            'classification':'synthetic analytical one-way routing only',
            'independent_real_road_truth':False,
            'map_sha256':sha256(MAP.read_bytes()).hexdigest(),
            'oracle_sha256':sha256(ORACLE.read_bytes()).hexdigest(),'cases':rows}


def run_dmn():
    data=import_osm_xml(MAP.read_bytes(),provenance=Provenance(
        'invented ROUTE-001','synthetic-v1','analytical fixture','Synthetic OSM format; no OpenStreetMap contributor road data used'))
    rows=[]
    for case in load_cases():
        source='osm:'+str(case['source_node']); target='osm:'+str(case['target_node'])
        route=shortest_route(data.graph,source,target)
        points=[data.coordinates[source]]+[data.coordinates[data.graph.edges[e].target] for e in route.edge_ids]
        rows.append(judge(case,points))
    return report('DMN',rows)


def run_brouter():
    opener=build_opener(ProxyHandler({}),NoRedirect())
    rows=[]
    for case in load_cases():
        start,end=case['path'][0],case['path'][-1]
        query=urlencode({'lonlats':f'{start[1]},{start[0]}|{end[1]},{end[0]}',
                         'profile':'car-vario','alternativeidx':0,'format':'geojson'})
        with opener.open('http://127.0.0.1:17777/brouter?'+query,timeout=30) as response:
            raw=response.read(200001)
        if len(raw)>200000: raise ValueError('Oversized BRouter response')
        data=json.loads(raw)
        features=data.get('features',[])
        lines=[f['geometry']['coordinates'] for f in features if f.get('geometry',{}).get('type')=='LineString']
        if len(lines)!=1: raise ValueError('Expected one complete BRouter route; no inferred geometry')
        rows.append(judge(case,[[p[1],p[0]] for p in lines[0]]))
    return report('BRouter',rows)


def scoreboard(reports):
    roster=['DMN']+[r['name'] for r in json.loads((ROOT/'config/dmn-engine-first-programme.json').read_text())['reference_families']]
    ids=[c['id'] for c in load_cases()]; supplied={}
    for r in reports:
        if r['system'] in supplied or r['system'] not in roster: raise ValueError('Duplicate or unknown engine')
        if r['map_sha256']!=sha256(MAP.read_bytes()).hexdigest() or r['oracle_sha256']!=sha256(ORACLE.read_bytes()).hexdigest() or [c['case_id'] for c in r['cases']]!=ids or r['test_id']!='ROUTE-001': raise ValueError('Nonmatching cohort')
        if r['execution']!=('actual_local_python' if r['system']=='DMN' else 'actual_live_loopback'): raise ValueError('Not an actual execution')
        if any(c['outcome'] not in ('PASS','FAIL') for c in r['cases']): raise ValueError('Incomplete judged cohort')
        supplied[r['system']]=r
    rows=[]
    for name in roster:
        r=supplied.get(name); reason=(
            'No actual ROUTE-001 execution supplied for this report set' if name in VERSIONS else
            'Routing replay adapter not implemented' if name in ('OsmAnd','Organic Maps') else
            'No permitted automated routing interface established' if name=='Waze' else
            'No configured permitted access and same-fixture interface')
        cases=r['cases'] if r else [{'case_id':cid,'outcome':'NOT_RUN','reason':reason} for cid in ids]
        passed=sum(c['outcome']=='PASS' for c in cases); failed=sum(c['outcome']=='FAIL' for c in cases)
        rows.append({'system':name,'rank':None,'passed':passed,'failed':failed,'not_run':0 if r else 4,'score_out_of_ten':10*passed/4 if r else None,'cases':cases})
    rows.sort(key=lambda r:(r['score_out_of_ten'] is None,-(r['score_out_of_ten'] or 0),r['system']))
    previous=None
    for i,r in enumerate([r for r in rows if r['score_out_of_ten'] is not None],1):
        if r['score_out_of_ten']!=previous: rank=i
        r['rank']=rank;previous=r['score_out_of_ten']
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--engine',choices=list(VERSIONS));p.add_argument('--reports',nargs='*',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if not a.output.resolve().is_relative_to((ROOT/'results').resolve()):raise ValueError('Ephemeral output must stay under results/')
    from benchmarks.routing_references import run_reference
    result=(run_dmn() if a.engine=='DMN' else run_brouter() if a.engine=='BRouter' else run_reference(a.engine)) if a.engine else {'test_id':'ROUTE-001','formula':'10 * passed / 4; ties share rank','rows':scoreboard([json.loads(p.read_text()) for p in a.reports or []])}
    a.output.parent.mkdir(exist_ok=True,parents=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
