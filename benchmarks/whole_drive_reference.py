"""Fresh isolated GraphHopper execution on the exact authored whole-drive map.

Routing/roundabout semantics and clean batch-matched path comparisons only. A
batch GPX matcher is not a live controller or voice/arrival timing comparison.
No external code is copied into DriveMate; no commercial SDK/API is invoked.
"""
import argparse,hashlib,json,subprocess,time,urllib.request,urllib.error
from urllib.parse import urlencode
from pathlib import Path
from datetime import datetime,timezone
import xml.etree.ElementTree as ET
from benchmarks.whole_drive import fixture,prepared,reference_requests,run
from benchmarks.import_restriction_compare import PIN,port,request,decode_response
from engine.routing import RouteNotFound

def ways(names):
    result=[]
    for name in names:
        value=int(name.split(':')[1])
        if not result or result[-1]!=value:result.append(value)
    return result

def gpx(samples):
    root=ET.Element('gpx',version='1.1',creator='original-synthetic-whole-drive',xmlns='http://www.topografix.com/GPX/1/1')
    track=ET.SubElement(root,'trk');ET.SubElement(track,'name').text='original synthetic replay'
    segment=ET.SubElement(track,'trkseg')
    for s in samples:
        point=ET.SubElement(segment,'trkpt',lat=str(s['lat']),lon=str(s['lon']))
        ET.SubElement(point,'time').text=datetime.fromtimestamp(s['t'],timezone.utc).isoformat().replace('+00:00','Z')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def post(p,body):
    url=f'http://127.0.0.1:{p}/match?'+urlencode({'profile':'car','details':'osm_way_id','instructions':'true','points_encoded':'false','gps_accuracy':'3'})
    req=urllib.request.Request(url,data=body,headers={'Content-Type':'application/gpx+xml','Accept':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=10) as response:return json.load(response)
    except urllib.error.HTTPError as e:return json.loads(e.read())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--jar',type=Path,required=True)
    parser.add_argument('--reuse-routes',action='store_true',help='Reuse exact same-map captured route responses; execute fresh full-trace matches only')
    a=parser.parse_args()
    if hashlib.sha512(a.jar.read_bytes()).hexdigest()!=PIN:raise ValueError('Unverified reference executable')
    out=Path('results/whole_drive/reference').resolve();out.mkdir(parents=True,exist_ok=True)
    raw=fixture();p=prepared(raw)
    observations=json.loads(Path('results/whole_drive/drivemate.json').read_text())
    if observations['dataset_sha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('Drive simulation dataset mismatch')
    osm=out/'synthetic_map.osm';osm.write_bytes(raw);http,admin=port(),port()
    config=out/'config.yml'
    config.write_text(f'''graphhopper:
  datareader.file: "{osm}"
  graph.location: "{out/'cache'}"
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
    routes=[];matches=[]
    if a.reuse_routes:
        previous=json.loads((out/'comparison.json').read_text())
        if previous['dataset_sha256']!=hashlib.sha256(raw).hexdigest() or previous['runtime_sha512']!=PIN:
            raise ValueError('Captured routes have a different dataset/runtime')
        (out/'initial_accepted_sample_subset_comparison.json').write_text(json.dumps(previous,indent=2))
        routes=previous['routes']
    with (out/'server.log').open('w') as log:
        proc=subprocess.Popen(['java','-Xmx256m','-jar',str(a.jar.resolve()),'server',str(config)],stdout=log,stderr=subprocess.STDOUT)
        try:
            info=None;deadline=time.monotonic()+30
            while proc.poll() is None and time.monotonic()<deadline:
                try:info=request(http,'/info');break
                except (OSError,ValueError):time.sleep(.2)
            if not info or info.get('version')!='11.1':raise RuntimeError('Reference unavailable or version mismatch')
            (out/'info.json').write_text(json.dumps(info,indent=2))
            for case in (() if a.reuse_routes else reference_requests()):
                start,end=case['nodes']
                try:route=p.route('osm:'+str(start),'osm:'+str(end));ours=ways(route.edge_ids)
                except RouteNotFound:route=None;ours=None
                params=[('point',','.join(map(str,p.coordinates['osm:'+str(n)]))) for n in (start,end)]
                params+=[('profile','car'),('details','osm_way_id'),('instructions','true'),('points_encoded','false')]
                response=request(http,'/route?'+urlencode(params));(out/(case['id']+'.json')).write_text(json.dumps(response,indent=2))
                other,rejected=decode_response(response)
                instructions=response.get('paths',[{}])[0].get('instructions',[]) if response.get('paths') else []
                signs=[i['sign'] for i in instructions if i.get('sign') in (-3,-2,-1,1,2,3)]
                exits=[i.get('exit_number') for i in instructions if i.get('sign')==6]
                expected=case['ways'];drivepass=ours==expected;ghpass=(rejected if expected is None else other==expected)
                driveexit=p.roundabouts(route)[0].exit_number if route and case.get('exit_number') else None
                if case.get('exit_number'):drivepass&=driveexit==case['exit_number'];ghpass&=exits==[case['exit_number']]
                if 'directions' in case:ghpass&=signs==case['directions']
                routes.append({'case':case['id'],'expected_ways':expected,'drivemate_ways':ours,'graphhopper_ways':other,
                               'drivemate_status':'pass' if drivepass else 'fail','graphhopper_status':'pass' if ghpass else 'fail',
                               'graphhopper_turn_signs':signs,'graphhopper_exit_numbers':exits,'drivemate_exit_number':driveexit,
                               'scope':'Full node-to-node route semantics; replan has no historical incoming-road parameter'})
            selected=('urban_clean','legal_wrong_turn_reroute','via_way_ban_detour','ring_exit_4')
            for ident in selected:
                row=next(r for r in observations['cases'] if r['case']==ident)
                if any(s['injected_fault'] for s in row['synthetic_samples']):raise ValueError('This comparison protocol requires a clean full raw trace')
                body=gpx(row['synthetic_samples']);(out/(ident+'_track.xml')).write_bytes(body)
                response=post(http,body);(out/(ident+'_match.json')).write_text(json.dumps(response,indent=2))
                other,_=decode_response(response)
                expected=ways(s['road'] for s in row['synthetic_samples'])
                matches.append({'case':ident,'expected_observed_ways':expected,'graphhopper_matched_ways':other,
                                'drivemate_online_status':row['status'],'graphhopper_batch_status':'pass' if other==expected else 'fail',
                                'sample_count':len(row['synthetic_samples']),'track_sha256':hashlib.sha256(body).hexdigest(),
                                'scope':'Same complete raw clean synthetic trace including acquisition fixes: live candidate vs offline batch reference; temporal/controller ranking not applicable'})
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
    result={'reference':'GraphHopper 11.1','runtime_sha512':PIN,'dataset_sha256':hashlib.sha256(raw).hexdigest(),
            'fresh_execution':True,'routes':routes,'batch_matches':matches,
            'route_response_provenance':'Preserved same-map actual execution earlier in this task' if a.reuse_routes else 'Fresh requests in this process',
            'batch_input_protocol':'Complete raw clean traces, including acquisition fixes; heading/per-fix accuracy use differs between live and batch interfaces',
            'whole_controller_comparison':'Not applicable: no external live GPS/voice controller was executed',
            'ranking':'Only per-case semantic comparison; no general winner, latency, lane or audio ranking'}
    (out/'comparison.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'route_cases':len(routes),'drivemate_passed':sum(r['drivemate_status']=='pass' for r in routes),
                      'graphhopper_passed':sum(r['graphhopper_status']=='pass' for r in routes),
                      'batch_match_cases':len(matches),'graphhopper_matches_passed':sum(r['graphhopper_batch_status']=='pass' for r in matches)}))
if __name__=='__main__':main()
