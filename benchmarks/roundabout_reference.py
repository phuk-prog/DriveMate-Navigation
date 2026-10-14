"""Actual GraphHopper exit-instruction comparison on an original synthetic ring."""
import argparse,hashlib,json,math,subprocess,time
from pathlib import Path
from engine.reconciled import prepare_navigation
from map_data.osm_xml import import_osm_xml,Provenance
from benchmarks.import_restriction_compare import PIN,port,request,decode_response

def fixture():
    pts={i+1:(-.001*math.sin(i*math.pi/4),.001*math.cos(i*math.pi/4)) for i in range(8)}
    pts[10]=(0,.005)
    for i in (2,4,6,7):pts[20+i]=tuple(v*4 for v in pts[i+1])
    nodes=''.join(f'<node id="{n}" lat="{lat:.8f}" lon="{lon:.8f}" version="1"/>' for n,(lat,lon) in pts.items())
    def way(ident,refs,roundabout=False):
        return f'<way id="{ident}" version="1">'+''.join(f'<nd ref="{n}"/>' for n in refs)+'<tag k="highway" v="residential"/><tag k="oneway" v="yes"/><tag k="maxspeed" v="30"/>'+('<tag k="junction" v="roundabout"/>' if roundabout else '')+f'<tag k="name" v="synthetic-{ident}"/></way>'
    roads=way(10,(10,1))+way(100,tuple(range(1,9))+(1,),True)
    for i in (2,4,6,7):roads+=way(200+i,(i+1,20+i))
    return ('<osm version="0.6" generator="original-synthetic-test">'+nodes+roads+'</osm>').encode(),pts

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--jar',type=Path,required=True);args=ap.parse_args()
    if hashlib.sha512(args.jar.read_bytes()).hexdigest()!=PIN:raise ValueError('Unverified reference executable')
    out=Path('results/roundabout_reference').resolve();out.mkdir(parents=True,exist_ok=True)
    raw,pts=fixture();osm=out/'original.osm';osm.write_bytes(raw)
    m=import_osm_xml(raw,provenance=Provenance('synthetic ring','v1','original fixture','OpenStreetMap contributors'))
    drive=prepare_navigation(m.graph,m.coordinates)
    p,q=port(),port();config=out/'config.yml'
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
    records=[]
    with (out/'server.log').open('w') as log:
        process=subprocess.Popen(['java','-Xmx256m','-jar',str(args.jar.resolve()),'server',str(config)],stdout=log,stderr=subprocess.STDOUT)
        try:
            ready=False;deadline=time.monotonic()+30
            while process.poll() is None and time.monotonic()<deadline:
                try:info=request(p,'/info');ready=True;break
                except (OSError,ValueError):time.sleep(.2)
            if not ready:raise RuntimeError('Reference unavailable; inspect setup log')
            if info.get('version')!='11.1':raise ValueError('Reference version mismatch')
            for expected,exit_node in enumerate((2,4,6,7),1):
                route=drive.route('osm:10','osm:'+str(20+exit_node))
                ours=drive.roundabouts(route)
                params=[('point',','.join(map(str,pts[n]))) for n in (10,20+exit_node)]
                params+=[('profile','car'),('points_encoded','false'),('instructions','true'),('details','osm_way_id')]
                response=request(p,'/route?'+__import__('urllib.parse',fromlist=['urlencode']).urlencode(params))
                (out/f'exit_{expected}.json').write_text(json.dumps(response,indent=2))
                ways,_=decode_response(response)
                instructions=response.get('paths',[{}])[0].get('instructions',[])
                other=[v.get('exit_number') for v in instructions if v.get('sign')==6]
                dmpass=len(ours)==1 and ours[0].exit_number==expected
                ghpass=other==[expected] and ways==[10,100,200+exit_node]
                records.append(dict(test_id='synthetic_exit_'+str(expected),expected_exit=expected,
                    drivemate_exit=ours[0].exit_number if len(ours)==1 else None,graphhopper_exits=other,
                    graphhopper_roads=ways,drivemate_status='pass' if dmpass else 'fail',
                    graphhopper_status='pass' if ghpass else 'fail',
                    first_place='tied correctness' if dmpass and ghpass else 'undetermined',repeat_count=1))
        finally:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
    report=dict(reference='GraphHopper 11.1',jar_sha512=PIN,dataset_sha256=hashlib.sha256(raw).hexdigest(),
       scope='Actual exit-number instructions on original synthetic data. No latency, lane, real-road or whole-app ranking.',cases=records)
    (out/'comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if any(r['drivemate_status']!='pass' or r['graphhopper_status']!='pass' for r in records):raise SystemExit(1)
if __name__=='__main__':main()
