"""RESOURCE-001 bounded actual Python searches, not native-engine/phone claims."""
import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
from time import get_clock_info,perf_counter,perf_counter_ns
import tracemalloc
from benchmarks.synthetic_grid import grid
from engine import shortest_route
from engine.astar import astar_route,prepare_astar

ROOT=Path(__file__).resolve().parents[1]
ORACLE=ROOT/'benchmarks/fixtures/synthetic-resource-001.json'


def fixture():return json.loads(ORACLE.read_text())


def percentile95(samples):
    if not samples or any(type(v) is not int or v<0 for v in samples):raise ValueError('Nonnegative integer samples required')
    return sorted(samples)[math.ceil(.95*len(samples))-1]


def check_route(graph,case,route):
    vertex=case['source'];valid=True
    for ident in route.edge_ids:
        e=graph.edges.get(ident)
        if e is None or e.source!=vertex or e.access!='allowed':valid=False;break
        vertex=e.target
    checks=dict(connected_allowed_path=valid and vertex==case['destination'],manhattan_edge_count=len(route.edge_ids)==case['expected_edges'],analytical_length=abs(route.length_m-case['expected_length_m'])<1e-7,analytical_time=abs(route.estimated_seconds-case['expected_seconds'])<1e-7)
    if not all(checks.values()):raise AssertionError('Analytical route contract failed: '+case['id']+' '+str(checks))
    return checks


def graph_digest(g,points):
    content=dict(coordinates=sorted(points.items()),edges=[vars(g.edges[k]) for k in sorted(g.edges)])
    return sha256(json.dumps(content,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def worker(size,configuration,phase):
    f=fixture()
    if size not in f['sizes'] or configuration not in f['configurations'] or phase not in ('timing','memory'):raise ValueError('Unfrozen worker settings')
    memory=phase=='memory'
    if memory:tracemalloc.start()
    t=perf_counter_ns();g,points,_,_=grid(size);graph_ns=perf_counter_ns()-t
    prepared=None;prepare_ns=0
    if configuration=='A*-prepared':
        t=perf_counter_ns();prepared=prepare_astar(g,points);prepare_ns=perf_counter_ns()-t
    setup_peak=tracemalloc.get_traced_memory()[1] if memory else None
    # Hash serialization and oracle checks are outside timed search samples.
    if memory:tracemalloc.stop()
    digest=graph_digest(g,points);rows=[];calls=0
    for case in (c for c in f['cases'] if c['size']==size):
        def search():
            nonlocal calls
            calls+=1
            if configuration=='Dijkstra':return shortest_route(g,case['source'],case['destination'])
            r=astar_route(g,case['source'],case['destination'],**({'prepared':prepared} if prepared else {'coordinates':points}))
            if not r.geographic_heuristic_used:raise AssertionError('Expected admissible fabricated geometry')
            return r.route
        if memory:
            tracemalloc.start();before=tracemalloc.get_traced_memory()[0]
            route=search();peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
            checks=check_route(g,case,route)
            rows.append(dict(case_id=case['id'],outcome='PASS',checks=checks,query_incremental_python_peak_bytes=max(0,peak-before)))
        else:
            for _ in range(f['warmup_repetitions']):check_route(g,case,search())
            samples=[]
            for _ in range(f['timed_repetitions']):
                t=perf_counter_ns();route=search();samples.append(perf_counter_ns()-t)
                check_route(g,case,route)
            rows.append(dict(case_id=case['id'],outcome='PASS',checks=check_route(g,case,route),samples_ns=samples,median_ns=statistics.median(samples),p95_ns=percentile95(samples)))
    return dict(size=size,configuration=configuration,phase=phase,graph_sha256=digest,vertices=len(g.vertices),edges=len(g.edges),graph_build_ns=graph_ns if not memory else None,prepare_ns=prepare_ns if not memory else None,setup_python_peak_bytes=setup_peak,process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,peak_rss_scope='fresh Linux worker lifetime, including interpreter/setup/all requests; not per-request RSS',actual_search_calls=calls,cases=rows)


def coverage(workers):
    f=fixture();expected={(s,c,p) for s in f['sizes'] for c in f['configurations'] for p in ('timing','memory')}
    keys=[(w['size'],w['configuration'],w['phase']) for w in workers]
    if len(keys)!=len(set(keys)) or set(keys)!=expected:raise ValueError('Missing/duplicate resource workers')
    for w in workers:
        ids=[c['id'] for c in f['cases'] if c['size']==w['size']]
        if [c['case_id'] for c in w['cases']]!=ids or any(c['outcome']!='PASS' for c in w['cases']):raise ValueError('Incomplete correctness cohort')
    for size in f['sizes']:
        if len({w['graph_sha256'] for w in workers if w['size']==size})!=1:raise ValueError('Nonmatching graph variants')
    names=['DMN']+[x['name'] for x in json.loads((ROOT/'config/dmn-engine-first-programme.json').read_text())['reference_families']]
    rows=[]
    for name in names:
        reason=('No identical weighted-RoadGraph resource adapter; existing OSM HTTP runs are a different cost/workload/transport and are not substituted' if name in ('OSRM','Valhalla','GraphHopper','openrouteservice','BRouter') else 'No executable native/app resource replay harness' if name in ('OsmAnd','Organic Maps') else 'No established permitted automated resource replay interface' if name=='Waze' else 'No configured permitted same-workload access; paid calls unauthorized')
        rows.append(dict(system=name,rank=None,score_out_of_ten=None,reason='Resource values informational; no performance quality threshold or cross-family ranking' if name=='DMN' else reason,cases=[dict(case_id=c['id'],outcome='PASS' if name=='DMN' else 'NOT_RUN',reason='All three DMN configurations checked against analytical route oracle in both phases' if name=='DMN' else reason) for c in f['cases']]))
    return rows


def run():
    if sys.platform!='linux':raise ValueError('Linux required for KiB RSS semantics')
    f=fixture();deadline=perf_counter()+f['total_timeout_s'];workers=[]
    # Config order rotates by graph size; all workers execute sequentially.
    for i,size in enumerate(f['sizes']):
        configs=f['configurations'][i:]+f['configurations'][:i]
        for configuration in configs:
            for phase in ('timing','memory'):
                remaining=deadline-perf_counter()
                if remaining<=0:raise TimeoutError('Bounded resource deadline expired')
                result=subprocess.run([sys.executable,'-m','benchmarks.resource_trial','--worker',str(size),configuration,phase],cwd=ROOT,capture_output=True,text=True,timeout=min(f['worker_timeout_s'],remaining),check=True)
                w=json.loads(result.stdout)
                if (w['size'],w['configuration'],w['phase'])!=(size,configuration,phase):raise ValueError('Worker identity mismatch')
                workers.append(w)
    return dict(test_id='RESOURCE-001',system='DMN',classification=f['classification'],run_sha=os.environ.get('GITHUB_HEAD_SHA') or os.environ.get('GITHUB_SHA'),oracle_sha256=sha256(ORACLE.read_bytes()).hexdigest(),source_sha256={p:sha256((ROOT/p).read_bytes()).hexdigest() for p in ('benchmarks/resource_trial.py','benchmarks/synthetic_grid.py','engine/routing.py','engine/astar.py')},environment=dict(python=sys.version,system=platform.system(),release=platform.release(),machine=platform.machine(),logical_cpus=os.cpu_count(),clock='perf_counter_ns',clock_resolution_s=get_clock_info('perf_counter').resolution),actual_search_calls=sum(w['actual_search_calls'] for w in workers),external_engine_executions=0,android_device_tests=0,workers=workers,coverage=coverage(workers),interpretation='Timing requests are untraced; memory uses different fresh workers. RSS includes interpreter/setup and is not Python allocation peak. No battery/thermal/device or native-family ranking.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',nargs=3);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.worker:
        print(json.dumps(worker(int(a.worker[0]),a.worker[1],a.worker[2])));return
    if a.output is None or not a.output.resolve().is_relative_to((ROOT/'results').resolve()):raise ValueError('Output under results required')
    r=run();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))

if __name__=='__main__':main()
