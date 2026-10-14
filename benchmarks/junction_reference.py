"""Actual junction-direction comparison; lane outputs are not assumed comparable."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
from urllib.parse import urlencode
from engine.reconciled import prepare_navigation
from map_data.osm_xml import import_osm_xml,Provenance
from benchmarks.import_restriction_compare import PIN,port,request,decode_response

def fixture():
    pts={1:(0,-.01),2:(0,0),3:(.01,0),4:(0,.01),5:(-.01,0)}
    nodes=''.join(f'<node id="{i}" lat="{a}" lon="{b}" version="1"/>' for i,(a,b) in pts.items())
    ways=''
    for ident,frm,to in [(10,1,2),(11,2,3),(12,2,4),(13,2,5)]:
        ways+=f'<way id="{ident}" version="1"><nd ref="{frm}"/><nd ref="{to}"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/><tag k="name" v="synthetic-{ident}"/>'
        if ident==10:ways+='<tag k="lanes" v="3"/><tag k="turn:lanes" v="left|through|right"/>'
        ways+='</way>'
    return ('<osm version="0.6" generator="original-synthetic-junction">'+nodes+ways+'</osm>').encode(),pts

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--jar',type=Path,required=True);args=ap.parse_args()
    if hashlib.sha512(args.jar.read_bytes()).hexdigest()!=PIN:raise ValueError('Unverified reference executable')
    out=Path('results/junction_reference').resolve();out.mkdir(parents=True,exist_ok=True)
    raw,pts=fixture();osm=out/'original.osm';osm.write_bytes(raw)
    m=import_osm_xml(raw,provenance=Provenance('synthetic crossroads','v1','original fixture','OpenStreetMap contributors'))
    drive=prepare_navigation(m.graph,m.coordinates);p,q=port(),port();config=out/'config.yml'
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
      port: {p}
      bind_host: 127.0.0.1
  admin_connectors:
    - type: http
      port: {q}
      bind_host: 127.0.0.1
  request_log:
    appenders: []
''')
    rows=[]
    with (out/'server.log').open('w') as log:
        proc=subprocess.Popen(['java','-Xmx256m','-jar',str(args.jar.resolve()),'server',str(config)],stdout=log,stderr=subprocess.STDOUT)
        try:
            ready=False;deadline=time.monotonic()+30
            while proc.poll() is None and time.monotonic()<deadline:
                try:info=request(p,'/info');ready=True;break
                except (OSError,ValueError):time.sleep(.2)
            if not ready:raise RuntimeError('Reference setup unavailable; inspect log')
            if info.get('version')!='11.1':raise ValueError('Reference version mismatch')
            for node,way,label,expected_sign,lane in [(3,11,'left',-2,1),(4,12,'through',0,2),(5,13,'right',2,3)]:
                route=drive.route('osm:1','osm:'+str(node));guide=drive.junctions(route)[0]
                params=[('point',','.join(map(str,pts[i]))) for i in (1,node)]+[('profile','car'),('points_encoded','false'),('instructions','true'),('details','osm_way_id')]
                response=request(p,'/route?'+urlencode(params));(out/(label+'.json')).write_text(json.dumps(response,indent=2))
                roads,_=decode_response(response)
                ins=response.get('paths',[{}])[0].get('instructions',[])
                signs=[i.get('sign') for i in ins if i.get('sign') in (-3,-2,-1,1,2,3)]
                ghpass=roads==[10,way] and signs==([] if expected_sign==0 else [expected_sign])
                dmpass=guide.manoeuvre==label and guide.candidate_lanes==(lane,)
                lane_fields=sorted({k for i in ins for k in i if 'lane' in k})
                rows.append(dict(test_id='junction_'+label,expected_direction=label,drivemate_direction=guide.manoeuvre,
                    drivemate_lanes=guide.candidate_lanes,graphhopper_signs=signs,graphhopper_roads=roads,
                    drivemate_status='pass' if dmpass else 'fail',graphhopper_direction_status='pass' if ghpass else 'fail',
                    first_place_direction='tied correctness' if ghpass and dmpass else 'undetermined',
                    observed_reference_lane_fields=lane_fields,lane_comparison='not applicable: verified lane assignment unavailable in this adapter',repeats=1))
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
    report=dict(reference='GraphHopper 11.1',jar_sha512=PIN,dataset_sha256=hashlib.sha256(raw).hexdigest(),cases=rows,
        scope='Actual three-direction synthetic comparison; no lane superiority, latency, Android or real-road ranking')
    (out/'comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if any(r['drivemate_status']!='pass' or r['graphhopper_direction_status']!='pass' for r in rows):raise SystemExit(1)
if __name__=='__main__':main()
