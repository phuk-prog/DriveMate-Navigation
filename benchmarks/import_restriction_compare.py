"""Real GraphHopper comparison of newly imported multi-segment restrictions.
Original synthetic fixtures only; semantic correctness, no speed ranking.
"""
import hashlib,json,socket,subprocess,time,urllib.request,urllib.parse,urllib.error
from pathlib import Path
from engine.reconciled import prepare_navigation
from engine.routing import RouteNotFound
from map_data.osm_xml import import_osm_xml,Provenance
PIN='fdc732882ada0c7464e8a25b5d0fe88c1467df5b0f918e6db20cbbac9753c8699b7266365dd52731a7b76db50c309e90d3e6ac0421af368778f85e966865825a'
def fixture(rule):
    pts={1:(0,0),2:(0,.01),3:(0,.02),4:(0,.03),5:(0,.04),6:(.02,.01),7:(.01,.02)}
    nodes=''.join(f'<node id="{i}" lat="{a}" lon="{b}" version="1"/>' for i,(a,b) in pts.items())
    ways=''
    for i,refs in [(10,(1,2)),(20,(2,3,4)),(30,(4,5)),(40,(2,6,4)),(50,(3,7))]:
        ways+=f'<way id="{i}" version="1">'+''.join(f'<nd ref="{n}"/>' for n in refs)+f'<tag k="highway" v="residential"/><tag k="oneway" v="yes"/><tag k="maxspeed" v="30"/><tag k="name" v="{i}"/></way>'
    members='<member type="way" ref="10" role="from"/><member type="way" ref="20" role="via"/><member type="way" ref="30" role="to"/>'
    return ('<osm version="0.6">'+nodes+ways+'<relation id="100" version="1">'+members+f'<tag k="type" v="restriction"/><tag k="restriction" v="{rule}"/></relation></osm>').encode(),pts

def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def request(p,path):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{p}{path}',timeout=5) as r:return json.load(r)
    except urllib.error.HTTPError as e:return json.loads(e.read())
def decode_response(response):
    other=None
    if response.get('paths'):
        other=[]
        for _,_,w in response['paths'][0]['details']['osm_way_id']:
            if not other or other[-1]!=w:other.append(w)
    hints=response.get('hints',[])
    rejected=isinstance(hints,list) and any(isinstance(h,dict) and 'ConnectionNotFound' in h.get('details','') for h in hints)
    return other,rejected

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--jar',type=Path,required=True);a=parser.parse_args()
    if hashlib.sha512(a.jar.read_bytes()).hexdigest()!=PIN:raise ValueError('Unverified engine executable')
    root=Path('results/import_competitor').resolve();root.mkdir(parents=True,exist_ok=True);rows=[]
    for kind in ('no','only'):
        folder=root/kind;folder.mkdir(exist_ok=True)
        raw,pts=fixture(kind+'_straight_on');osm=folder/'original.osm';osm.write_bytes(raw)
        imported=import_osm_xml(raw,provenance=Provenance('synthetic','v2','original synthetic XML','OpenStreetMap contributors'))
        drive=prepare_navigation(imported.graph,imported.coordinates)
        p,q=port(),port();config=folder/'config.yml'
        config.write_text(f'''graphhopper:
  datareader.file: "{osm}"
  graph.location: "{folder/'cache'}"
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
        with (folder/'server.log').open('w') as log:
            proc=subprocess.Popen(['java','-Xmx256m','-jar',str(a.jar.resolve()),'server',str(config)],stdout=log,stderr=subprocess.STDOUT)
            try:
                ready=False;deadline=time.monotonic()+30
                while proc.poll() is None and time.monotonic()<deadline:
                    try:info=request(p,'/info');ready=True;break
                    except (OSError,ValueError):time.sleep(.2)
                if not ready:raise RuntimeError('GraphHopper unavailable; inspect local server log')
                if info.get('version')!='11.1':raise ValueError('Engine version mismatch')
                for name,start,end,expected in [
                    ('whole_multi_segment_turn',1,5,[10,40,30] if kind=='no' else [10,20,30]),
                    ('unrelated_arrival',2,5,[20,30]),
                    ('early_exit',1,7,[10,20,50] if kind=='no' else None)]:
                    observed=[]
                    for backend in ('research','portable'):
                        try:r=drive.route('osm:'+str(start),'osm:'+str(end),backend=backend);roads=[]
                        except RouteNotFound:r=None;roads=None
                        if r:
                            for edge in r.edge_ids:
                                way=int(edge.split(':')[1])
                                if not roads or roads[-1]!=way:roads.append(way)
                        observed.append(roads)
                    params=[('point',','.join(map(str,pts[n]))) for n in (start,end)]+[('profile','car'),('points_encoded','false'),('details','osm_way_id')]
                    response=request(p,'/route?'+urllib.parse.urlencode(params))
                    (folder/(name+'.json')).write_text(json.dumps(response,indent=2))
                    other,rejected=decode_response(response)
                    ghpass=other==expected and (expected is not None or rejected)
                    dmpass=all(v==expected for v in observed)
                    rows.append(dict(test_id=kind+'_'+name,expected=expected,drivemate=observed,graphhopper=other,
                       drivemate_status='pass' if dmpass else 'fail',graphhopper_status='pass' if ghpass else 'fail',
                       first_place='tied correctness' if dmpass and ghpass else 'undetermined',repeats=1,
                       dataset_sha256=hashlib.sha256(raw).hexdigest()))
            finally:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
    result=dict(reference='GraphHopper 11.1',reference_sha512=PIN,scenarios=rows,
        scope='Fresh actual engine execution on original synthetic data; road-sequence semantics only. Profiles/costs differ; no latency rankings. Conditional reference comparison remains untested.')
    (root/'comparison.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    if any(r['drivemate_status']!='pass' or r['graphhopper_status']!='pass' for r in rows):raise SystemExit(1)
if __name__=='__main__':main()
