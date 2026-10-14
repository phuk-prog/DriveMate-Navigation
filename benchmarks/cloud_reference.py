"""Original local-service adapters for GitHub-hosted isolated references.

Geometry decoding is an adapter, not a competitor implementation. Unmappable
geometry is unknown, never fabricated path success. Raw responses are retained.
"""
import argparse,json,time,math,urllib.request,urllib.error
from urllib.parse import urlencode
from pathlib import Path
from benchmarks.whole_drive import fixture,prepared,reference_requests
from benchmarks.whole_drive_reference import ways
from gps.matching import Matcher

def polyline6(text):
    if not isinstance(text,str) or len(text)>200000:raise ValueError('Invalid bounded polyline')
    index=0;lat=lon=0;points=[]
    while index<len(text):
        delta=[]
        for _ in range(2):
            value=shift=0
            while True:
                if index>=len(text) or shift>35:raise ValueError('Malformed polyline')
                b=ord(text[index])-63;index+=1
                if not 0<=b<=63:raise ValueError('Malformed polyline character')
                value|=(b&31)<<shift;shift+=5
                if b<32:break
            delta.append(-(value//2)-1 if value&1 else value//2)
        lat+=delta[0];lon+=delta[1];points.append((lat/1e6,lon/1e6))
    return points

def geometry_ways(p,points):
    matcher=Matcher(p);nodepoints={n:matcher._xy(*v) for n,v in p.coordinates.items()};nodes=[]
    for point in points:
        xy=matcher._xy(*point);distance,node=min((math.hypot(xy[0]-v[0],xy[1]-v[1]),n) for n,v in nodepoints.items())
        if distance>1:return None
        if not nodes or nodes[-1]!=node:nodes.append(node)
    edges={}
    for name,e in p.source_edges.items():edges.setdefault((e.source,e.target),[]).append(name)
    names=[]
    for a,b in zip(nodes,nodes[1:]):
        candidates=edges.get((a,b),())
        if len(candidates)!=1:return None
        names.append(candidates[0])
    return ways(names) if len(nodes)>1 else None

def call(engine,p,start,end):
    a,b=p.coordinates['osm:'+str(start)],p.coordinates['osm:'+str(end)]
    if engine=='osrm':
        path='/route/v1/driving/'+f'{a[1]},{a[0]};{b[1]},{b[0]}?'+urlencode({'steps':'true','geometries':'geojson','overview':'full','annotations':'nodes'})
        url='http://127.0.0.1:5000'+path
    else:
        payload={'locations':[{'lat':v[0],'lon':v[1],'type':'break'} for v in (a,b)],'costing':'auto','units':'kilometers','shape_format':'polyline6'}
        url=urllib.request.Request('http://127.0.0.1:8002/route',
            data=json.dumps(payload,separators=(',',':')).encode('utf-8'),
            headers={'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(url,timeout=10) as r:return json.load(r)
    except urllib.error.HTTPError as e:return json.loads(e.read())

def parse(engine,p,response):
    if engine=='osrm':
        if response.get('code')=='NoRoute':return None,(),True
        if response.get('code')!='Ok' or not response.get('routes'):return None,(),False
        r=response['routes'][0];points=[(v[1],v[0]) for v in r['geometry']['coordinates']]
        exits=tuple(step['maneuver']['exit'] for leg in r['legs'] for step in leg['steps'] if step['maneuver'].get('type') in ('roundabout','rotary') and 'exit' in step['maneuver'])
    else:
        if response.get('error_code') in (442,443):return None,(),True
        if not response.get('trip',{}).get('legs'):return None,(),False
        points=[];exits=[]
        for leg in response['trip']['legs']:
            points.extend(polyline6(leg['shape']))
            exits.extend(m['roundabout_exit_count'] for m in leg['maneuvers'] if m.get('roundabout_exit_count'))
        exits=tuple(exits)
    return geometry_ways(p,points),exits,False

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--engine',choices=['osrm','valhalla'],required=True);ap.add_argument('--version',required=True);a=ap.parse_args()
    p=prepared();out=Path('results/cloud_'+a.engine);out.mkdir(parents=True,exist_ok=True)
    deadline=time.monotonic()+240
    while True:
        try:
            probe=call(a.engine,p,1,4)
            if probe.get('routes') or probe.get('trip',{}).get('legs'):break
        except (OSError,ValueError):pass
        if time.monotonic()>deadline:raise RuntimeError('Reference did not become route-ready')
        time.sleep(1)
    rows=[]
    for c in reference_requests():
        r=call(a.engine,p,*c['nodes']);(out/(c['id']+'.json')).write_text(json.dumps(r,indent=2))
        route,exits,no_route=parse(a.engine,p,r)
        if c['ways'] is None:status='pass' if no_route else 'unknown' if route is None else 'fail'
        elif route is None:status='unknown'
        else:status='pass' if route==c['ways'] and ('exit_number' not in c or exits==(c['exit_number'],)) else 'fail'
        rows.append({'case':c['id'],'expected_ways':c['ways'],'actual_ways':route,'roundabout_exits':exits,'status':status})
    result={'engine':a.engine,'version':a.version,'fresh_execution':True,'dataset_sha256':__import__('hashlib').sha256(fixture()).hexdigest(),'cases':rows,
            'scope':'Synthetic static route/exit semantics only; geometry adapter gaps are unknown, not scored as passes','score_out_of_10':round(10*sum(r['status']=='pass' for r in rows)/len(rows),2) if not any(r['status']=='unknown' for r in rows) else None}
    (out/'comparison.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
