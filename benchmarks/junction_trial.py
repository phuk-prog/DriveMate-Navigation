"""JUNCTION-001 synthetic analytical paths and principal maneuvers, not road truth."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
from urllib.request import Request
from engine import shortest_route
from engine.maneuvers import principal_maneuvers
from map_data import Provenance, import_osm_xml
from benchmarks.routing_trial import judge, ROOT, VERSIONS
from benchmarks.routing_references import OPENER, route_request, route_points
from benchmarks.routing_legality_batch import wait_reference
MAP=ROOT/'benchmarks/fixtures/synthetic-junction-001.xml'
ORACLE=MAP.with_suffix('.json')


def cases():return json.loads(ORACLE.read_text())['cases']


def load_map():
    data=import_osm_xml(MAP.read_bytes(),provenance=Provenance('invented JUNCTION-001','synthetic-v1','analytical fixture','Synthetic OSM format; no OpenStreetMap contributor road data used'))
    ways={w.get('id') for w in ET.fromstring(MAP.read_bytes()).findall('way') if any(t.get('k')=='junction' and t.get('v')=='roundabout' for t in w.findall('tag'))}
    ring={e for e in data.graph.edges if e.split(':')[1] in ways}
    return data,ring


def judged(case,points,maneuvers,raw):
    row=judge(case,points)
    row['checks']['principal_maneuvers']=maneuvers==case['maneuvers']
    row['failures']=[k for k,v in row['checks'].items() if not v]
    row.update(outcome='FAIL' if row['failures'] else 'PASS',expected_maneuvers=case['maneuvers'],returned_maneuvers=maneuvers,raw_maneuvers=raw)
    return row


def report(system,rows):
    return dict(test_id='JUNCTION-001',system=system,version=VERSIONS[system],instructions_enabled=True,execution='actual_local_python' if system=='DMN' else 'actual_live_loopback',classification='synthetic analytical only',independent_real_road_truth=False,map_sha256=sha256(MAP.read_bytes()).hexdigest(),oracle_sha256=sha256(ORACLE.read_bytes()).hexdigest(),cases=rows)


def run_dmn():
    data,ring=load_map();rows=[]
    for c in cases():
        s='osm:'+str(c['source_node']);t='osm:'+str(c['target_node'])
        r=shortest_route(data.graph,s,t)
        points=[data.coordinates[s]]+[data.coordinates[data.graph.edges[e].target] for e in r.edge_ids]
        m=principal_maneuvers(data.graph,data.coordinates,r.edge_ids,ring)
        rows.append(judged(c,points,m,{'edge_ids':r.edge_ids,'roundabout_edges':sorted(ring)}))
    return report('DMN',rows)


def normalize(system,data):
    out=[]
    if system=='OSRM':
        raw=[s['maneuver'] for s in data['routes'][0]['legs'][0]['steps']]
        for m in raw:
            k=m['type']
            if k in ('depart','arrive','continue','new name','exit roundabout','exit rotary'):continue
            if k in ('roundabout','rotary'):out.append({'kind':'roundabout','exit':m.get('exit')})
            else:out.append({'kind':m.get('modifier','unknown')})
    elif system=='Valhalla':
        raw=data['trip']['legs'][0]['maneuvers']
        for m in raw:
            t=m['type']
            if t in (0,1,2,3,4,5,6,7,8,27):continue
            out.append({'kind':'roundabout','exit':m.get('roundabout_exit_count')} if t==26 else {'kind':{10:'right',15:'left'}.get(t,'unknown:'+str(t))})
    elif system=='GraphHopper':
        raw=data['paths'][0]['instructions']
        for m in raw:
            t=m['sign']
            if t in (0,4,5):continue
            out.append({'kind':'roundabout','exit':m.get('exit_number')} if t==6 else {'kind':{-2:'left',2:'right'}.get(t,'unknown:'+str(t))})
    elif system=='openrouteservice':
        raw=[s for seg in data['features'][0]['properties']['segments'] for s in seg['steps']]
        for m in raw:
            t=m['type']
            if t in (6,8,10,11):continue
            out.append({'kind':'roundabout','exit':m.get('exit_number')} if t==7 else {'kind':{0:'left',1:'right'}.get(t,'unknown:'+str(t))})
    elif system=='BRouter':
        raw=data['features'][0]['properties'].get('voicehints',[])
        for m in raw:
            t=m[1]
            if t==1:continue
            out.append({'kind':'roundabout','exit':abs(m[2])} if t in (13,14) else {'kind':{2:'left',5:'right'}.get(t,'unknown:'+str(t))})
    else:raise ValueError('Unknown family')
    return out,raw


def request(system,start,end):
    if system=='BRouter':
        return Request('http://127.0.0.1:17777/brouter?'+urlencode(dict(lonlats=f'{start[1]},{start[0]}|{end[1]},{end[0]}',profile='car-vario',alternativeidx=0,format='geojson',timode=3)))
    req=route_request(system,start,end)
    if req.data:
        body=json.loads(req.data)
        if system=='openrouteservice':body['instructions']=True
        return Request(req.full_url,json.dumps(body).encode(),{'Content-Type':'application/json'})
    return Request(req.full_url.replace('steps=false','steps=true').replace('instructions=false','instructions=true'))


def run_reference(system):
    wait_reference(system);rows=[]
    for c in cases():
        try:
            with OPENER.open(request(system,c['path'][0],c['path'][-1]),timeout=30) as response:raw=response.read(200001)
            if len(raw)>200000:raise ValueError('Oversized response')
            d=json.loads(raw)
            points=([[p[1],p[0]] for p in d['features'][0]['geometry']['coordinates']] if system=='BRouter' else route_points(system,d))
            m,raw_m=normalize(system,d)
            rows.append(judged(c,points,m,raw_m))
        except Exception as e:
            rows.append(dict(case_id=c['id'],outcome='UNRESOLVED',reason=type(e).__name__+': '+str(e)[:150]))
    return report(system,rows)


def main():
    p=argparse.ArgumentParser();p.add_argument('--engine',choices=list(VERSIONS),required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if not a.output.resolve().is_relative_to((ROOT/'results').resolve()):raise ValueError('Output outside results')
    r=run_dmn() if a.engine=='DMN' else run_reference(a.engine)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
    if a.engine=='DMN' and any(c['outcome']!='PASS' for c in r['cases']):raise SystemExit(1)

if __name__=='__main__':main()
