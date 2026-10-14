"""Paired same-host configured-service timings; excludes native algorithm claims."""
import json
import math
import subprocess
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from statistics import median
from threading import Thread
import time
from urllib.parse import parse_qs,urlparse,urlencode
from urllib.request import urlopen
from benchmarks.expanded_comparison import gh_route,shape_roads,route_shape,endpoint_check
from benchmarks.whole_drive_reference import ways
from benchmarks.route_quality_fixture import judge_route


def validated_geometry(data,case,raw):
    path,decoded=shape_roads(data,route_shape('graphhopper',raw))
    endpoint=endpoint_check('graphhopper',raw,data,case)
    if decoded!='pass' or not endpoint or not endpoint['within_2m']:
        raise ValueError('Timed route failed independent geometry/endpoint checks')
    return path,endpoint


def paired(data,p,http):
    cases=[c for c in data['quality_cases'] if c['id'].split('/')[-1] in ('alternatives0','replan0')]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            try:
                q=parse_qs(urlparse(self.path).query)
                r=p.route('osm:'+q['from'][0],'osm:'+q['to'][0])
                body=json.dumps({'ways':ways(r.edge_ids)}).encode();status=200
            except Exception:
                body=b'{"error":"research route unavailable"}';status=500
            self.send_response(status);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    samples=[];errors=[]
    try:
        for repeat in range(-3,10):
            for c in cases:
                for engine in (('drivemate','graphhopper') if repeat%2 else ('graphhopper','drivemate')):
                    try:
                        start=time.perf_counter_ns()
                        if engine=='drivemate':
                            with urlopen(f'http://127.0.0.1:{server.server_port}/route?'+urlencode({'from':c['start'],'to':c['end']}),timeout=30) as r:
                                path=json.load(r)['ways'];no_route=False
                        else:raw,path,no_route,_=gh_route(http,data,c,instructions=False)
                        ms=(time.perf_counter_ns()-start)/1e6
                        endpoint=None
                        if engine=='graphhopper':
                            path,endpoint=validated_geometry(data,c,raw)
                        legal=judge_route(data,c,path,no_route)['status']=='pass'
                        if not legal:raise ValueError('Incorrect route cannot earn timing evidence')
                        if repeat>=0:samples.append({'engine':engine,'case':c['id'],'repeat':repeat,
                                                    'milliseconds':ms,'actual_ways':path,'endpoint_check':endpoint})
                    except (OSError,ValueError,KeyError,IndexError,TypeError,AttributeError) as exc:
                        errors.append({'engine':engine,'case':c['id'],'repeat':repeat,'issue':str(exc)[:180]})
    finally:server.shutdown();server.server_close();thread.join(timeout=2)
    summary={}
    for engine in ('drivemate','graphhopper'):
        values=sorted(r['milliseconds'] for r in samples if r['engine']==engine)
        if values:summary[engine]={'requests':len(values),'median_ms':median(values),
                                  'p95_ms':values[math.ceil(.95*len(values))-1],'max_ms':max(values)}
    return {'dataset_sha256':data['dataset_sha256'],
            'commit_sha':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'cases':[c['id'] for c in cases],
            'repeats':10,'warmup_repeats':3,'samples':samples,'errors':errors,'summary':summary,
            'scope':'Paired alternating warm HTTP configured services on one host',
            'limits':['DriveMate subprocess-backed ALT vs GraphHopper with CH/LM disabled',
                      'Different costing, serialization and response sizes',
                      'Ten repeats per request; no independent host replication',
                      'Not mobile efficiency, native kernel speed or cross-engine global ranking']}
