"""Measured category scores, never invented ratings for unexecuted systems.

HTTP microbenchmark on the same tiny authored map, persistent loaded services,
same client, same order with alternated request priority. Cost models still differ;
this measures configured service responsiveness, not Android/world-map performance.
"""
import argparse,json,hashlib,math,subprocess,time,threading,csv,urllib.request
from urllib.parse import urlencode,urlparse,parse_qs
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from statistics import median
from benchmarks.whole_drive import fixture,prepared,reference_requests
from benchmarks.whole_drive_reference import ways
from benchmarks.import_restriction_compare import PIN,port,request,decode_response
from benchmarks.ten_system_matrix import SYSTEMS
from engine.routing import RouteNotFound

CATEGORIES=(('routing_legality',20),('speed_rerouting',15),('gps_matching',15),('gps_recovery',10),
            ('junction_roundabout',10),('lane_guidance',10),('instruction_timing',10),('offline_efficiency',10))

def correctness_score(passed,total):
    if type(total) is not int or type(passed) is not int or total<1 or not 0<=passed<=total:raise ValueError('Valid nonempty test counts required')
    return round(10*passed/total,2)

def speed_scores(measurements):
    if not measurements or any(not isinstance(x,(int,float)) or isinstance(x,bool) or not math.isfinite(x) or x<=0 for x in measurements.values()):raise ValueError('Positive finite latency measurements required')
    best=min(measurements.values())
    return {name:round(10*best/value,2) for name,value in measurements.items()}

def overall(scores):
    if any(scores.get(key) is None for key,_ in CATEGORIES):return None
    if any(not isinstance(scores[key],(int,float)) or isinstance(scores[key],bool) or not 0<=scores[key]<=10 for key,_ in CATEGORIES):raise ValueError('Invalid category score')
    return round(sum(scores[key]*weight for key,weight in CATEGORIES)/100,2)

def quantile95(values):return sorted(values)[max(0,math.ceil(.95*len(values))-1)]

def benchmark(jar,repeats=30):
    if type(repeats) is not int or not 10<=repeats<=100:raise ValueError('Repeat count 10..100 required')
    if hashlib.sha512(jar.read_bytes()).hexdigest()!=PIN:raise ValueError('Unverified reference executable')
    out=Path('results/category_scores').resolve();out.mkdir(parents=True,exist_ok=True)
    p=prepared();http,admin=port(),port();raw=fixture();osm=out/'synthetic_map.osm';osm.write_bytes(raw)
    config=out/'config.yml';cache=Path('results/whole_drive/reference/cache').resolve()
    config.write_text(f'''graphhopper:
  datareader.file: "{osm}"
  graph.location: "{cache}"
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
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            q=parse_qs(urlparse(self.path).query)
            try:
                start,end=int(q['from'][0]),int(q['to'][0])
                try:r=p.route('osm:'+str(start),'osm:'+str(end));names=ways(r.edge_ids)
                except RouteNotFound:names=None
                body=json.dumps({'ways':names}).encode();status=200
            except (KeyError,ValueError):body=b'{"error":"invalid synthetic endpoint"}';status=400
            self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    candidate=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=candidate.serve_forever,daemon=True);thread.start()
    selected=reference_requests()[:4];samples={name:[] for name in ('DriveMate','GraphHopper')};rows=[]
    try:
        with (out/'server.log').open('w') as log:
            proc=subprocess.Popen(['java','-Xmx256m','-jar',str(jar.resolve()),'server',str(config)],stdout=log,stderr=subprocess.STDOUT)
            try:
                info=None;deadline=time.monotonic()+30
                while proc.poll() is None and time.monotonic()<deadline:
                    try:info=request(http,'/info');break
                    except (OSError,ValueError):time.sleep(.2)
                if not info or info.get('version')!='11.1':raise RuntimeError('Reference service unavailable/version mismatch')
                def query(name,case):
                    a,b=case['nodes']
                    if name=='DriveMate':
                        with urllib.request.urlopen(f'http://127.0.0.1:{candidate.server_port}/route?'+urlencode({'from':a,'to':b}),timeout=5) as r:return json.load(r)['ways']
                    params=[('point',','.join(map(str,p.coordinates['osm:'+str(n)]))) for n in (a,b)]
                    params+=[('profile','car'),('details','osm_way_id'),('instructions','false'),('points_encoded','false')]
                    return decode_response(request(http,'/route?'+urlencode(params)))[0]
                # Warm the JVM, indexes and transition caches before recording.
                for _ in range(5):
                    for case in selected:
                        for name in samples:
                            if query(name,case)!=case['ways']:raise ValueError('Semantic parity check failed before timing')
                for iteration in range(repeats):
                    for case in selected:
                        order=tuple(samples) if iteration%2==0 else tuple(reversed(samples))
                        for name in order:
                            started=time.perf_counter_ns();answer=query(name,case);elapsed=(time.perf_counter_ns()-started)/1e6
                            if answer!=case['ways']:raise ValueError('Incorrect route cannot earn a speed score')
                            samples[name].append(elapsed);rows.append({'system':name,'case':case['id'],'repeat':iteration,'milliseconds':elapsed})
            finally:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
    finally:candidate.shutdown();candidate.server_close();thread.join(timeout=2)
    result={'scope':'Warm local HTTP configured-service microbenchmark on one tiny synthetic map; not native algorithm/Android/whole-world speed',
            'dataset_sha256':hashlib.sha256(raw).hexdigest(),'runtime_sha512':PIN,'repeats':repeats,'requests_per_system':len(selected)*repeats,
            'known_differences':['DriveMate prepared research ALT service vs GraphHopper server with CH/LM disabled','Vehicle speed/cost/turn-cost models differ','GraphHopper serializes its own API shape; DriveMate serializes a minimal ways response','Both share client transport/host/dataset; wrappers, caches and runtime overhead still differ'],
            'summary':{name:{'median_ms':median(v),'p95_ms':quantile95(v),'max_ms':max(v)} for name,v in samples.items()},'samples':rows}
    (out/'warm_http_latency.json').write_text(json.dumps(result,indent=2))
    return result

def build_scorecard(latency):
    reference=json.loads(Path('results/whole_drive/reference/comparison.json').read_text())
    speed=speed_scores({n:v['p95_ms'] for n,v in latency['summary'].items()});systems=[]
    for name in ('DriveMate','GraphHopper'):
        scores={key:None for key,_ in CATEGORIES};evidence={}
        if name in ('DriveMate','GraphHopper'):
            field='drivemate_status' if name=='DriveMate' else 'graphhopper_status'
            scores['routing_legality']=correctness_score(sum(r[field]=='pass' for r in reference['routes']),len(reference['routes']))
            ring=[r for r in reference['routes'] if r['case'].startswith('ring_exit')]
            scores['junction_roundabout']=correctness_score(sum(r[field]=='pass' for r in ring),len(ring))
            evidence['junction_roundabout']='Four simple roundabout ordinals only; broader junction/motorway quality unscored'
            matchfield='drivemate_online_status' if name=='DriveMate' else 'graphhopper_batch_status'
            scores['gps_matching']=correctness_score(sum(r[matchfield]=='pass' for r in reference['batch_matches']),len(reference['batch_matches']))
            evidence['gps_matching']='Four clean path outcomes; live vs batch interfaces differ, so no live robustness ranking'
            scores['speed_rerouting']=speed[name];evidence['speed_rerouting']='Relative warm HTTP p95 among these two configurations; separate from general engine/mobile speed'
        # Candidate-only checks cannot produce a fair inter-system rank in recovery,
        # lanes, timing or offline resource categories. Keep them explicitly blank.
        systems.append({'system':name,'scores':scores,'overall':overall(scores),'evidence':evidence,
                        'status':'scoped measured subset' if name in ('DriveMate','GraphHopper') else 'unexecuted: no score'})
    result={'scale':10,'categories':[{'category':key,'proposed_weight_percent':weight} for key,weight in CATEGORIES],
            'correctness_formula':'10 * passed / executed applicable cases; scores only describe this fixture coverage',
            'speed_formula':'10 * best tested p95 / system p95; relative configured-service score, not a universal speed scale',
            'overall_policy':'No overall score/rank unless all eight categories have comparable evidence; missing is not zero',
            'systems':systems,'speed_ranking_only':sorted([{'system':n,'score':v,'p95_ms':latency['summary'][n]['p95_ms']} for n,v in speed.items()],key=lambda x:x['p95_ms']),
            'global_ranking':None,'candidate_only_evidence':'381 regression methods; 16 drives; 1536 recovery and 2304 timing streams passed, but rival equivalent results are absent',
            'provisioning_attempts':'No Docker/Podman/adb/cmake/Maven/Gradle or missing routing engines; direct PyPI and GitHub-release download probes timed out; commercial SDK/device harnesses not supplied'}
    out=Path('results/category_scores');(out/'scorecard.json').write_text(json.dumps(result,indent=2))
    with (out/'scorecard.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['system',*[key for key,_ in CATEGORIES],'overall','status'])
        for r in systems:writer.writerow([r['system'],*[r['scores'][key] for key,_ in CATEGORIES],r['overall'],r['status']])
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--jar',type=Path,required=True);ap.add_argument('--repeats',type=int,default=30);a=ap.parse_args()
    measured=benchmark(a.jar,a.repeats);scorecard=build_scorecard(measured)
    print(json.dumps({'measured_http':measured['summary'],'speed_ranking_only':scorecard['speed_ranking_only'],'global_ranking':None}))
if __name__=='__main__':main()
