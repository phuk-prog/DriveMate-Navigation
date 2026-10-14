"""Actual RoutingKit CH executions on the shared synthetic DriveMate fixture.

The RoutingKit C++ library is compiled separately at a pinned SHA. Its CH
search answers an independently authored transition graph (with supplied
one-way and forbidden-turn evidence); this is a *routing algorithm* benchmark,
NOT an independent OSM importer, roundabout guidance or live GPS benchmark.
"""
from collections import deque
from decimal import Decimal,ROUND_CEILING
import argparse,hashlib,json,subprocess
from pathlib import Path
from benchmarks.whole_drive import fixture,prepared,reference_requests
from benchmarks.whole_drive_reference import ways

def weighted_cost(e):
    return int((Decimal(str(e.estimated_seconds))*1000).to_integral_value(rounding=ROUND_CEILING))+1

def legal(through,next_name,rules):
    path=through+(next_name,)
    for kind,roads in rules:
        if kind=='no' and len(path)>=len(roads) and path[-len(roads):]==roads:return False
        if kind=='only':
            # The obligation begins on entering the from-road. Waiting for
            # the complete via sequence incorrectly permits early escape.
            for prefix in range(1,len(roads)):
                if len(through)>=prefix and through[-prefix:]==roads[:prefix] and next_name!=roads[prefix]:
                    return False
    return True

def compile_query(p,start,end):
    """Explicit edge-state transition graph; no DriveMate route search results read."""
    rules=tuple((r.kind,tuple(p.edge_names[i] for i in r.edges)) for r in p.graph.rules
                if 'car' in r.vehicles)
    # Store enough previous roads to preserve via-way and only-turn restrictions.
    keep=max((len(roads)-1 for _,roads in rules),default=1)
    out={}
    for e in p.source_edges.values():
        if e.access!='prohibited':out.setdefault(e.source,[]).append(e)
    nodes={('source',):0};arcs=[];labels=[];queue=deque()
    def node(key):
        if key not in nodes:
            if len(nodes)>10000:raise ValueError('Query graph too complex for fixture')
            nodes[key]=len(nodes);queue.append(key)
        return nodes[key]
    # All paths start from one given intersection; do not substitute a
    # shortest-path output from the reference DriveMate router.
    for e in out.get(start,()):
        hist=(e.edge_id,)[-keep:]
        ix=node((e.edge_id,hist))
        arcs.append((0,ix,weighted_cost(e)));labels.append(e.edge_id)
    while queue:
        state=queue.popleft()
        old_name,hist=state
        if p.source_edges[old_name].target==end:continue
        for nxt in out.get(p.source_edges[old_name].target,()):
            if not legal(hist,nxt.edge_id,rules):continue
            upcoming=(hist+(nxt.edge_id,))[-keep:]
            ix=node((nxt.edge_id,upcoming))
            arcs.append((nodes[state],ix,weighted_cost(nxt)))
            labels.append(nxt.edge_id)
    sink=len(nodes)
    for state,i in list(nodes.items()):
        if state==('source',):continue
        if p.source_edges[state[0]].target==end:
            arcs.append((i,sink,1));labels.append(None)
    return len(nodes)+1,0,sink,arcs,labels

def execute(binary,p,start,end):
    n,source,target,arcs,labels=compile_query(p,start,end)
    input_text=(f"{n} {len(arcs)} {source} {target}\n"+
                ''.join(f"{u} {v} {w}\n" for u,v,w in arcs))
    proc=subprocess.run([str(binary)],input=input_text,text=True,capture_output=True,
                        timeout=25,check=True)
    words=proc.stdout.strip().split()
    if words==['UNREACHABLE']:return None
    if not words or words[0]!='PATH':raise ValueError('Invalid RoutingKit output')
    indices=list(map(int,words[1:]))
    if any(i<0 or i>=len(labels) for i in indices):raise ValueError('Bad RoutingKit arc ID')
    selected=[labels[i] for i in indices if labels[i] is not None]
    return ways(selected)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--revision',required=True)
    args=parser.parse_args()
    if not args.binary.is_file():raise ValueError('RoutingKit executable absent')
    raw=fixture();p=prepared(raw)
    output=Path('results/routingkit');output.mkdir(parents=True,exist_ok=True)
    cases=[]
    for c in reference_requests():
        name=c['id'];expected=c['ways']
        try:
            result=execute(args.binary,p,'osm:'+str(c['nodes'][0]),'osm:'+str(c['nodes'][1]))
            status='pass' if result==expected else 'fail'
            issue=None if status=='pass' else 'different_route_or_legal_restriction'
        except (OSError,ValueError,subprocess.SubprocessError) as exc:
            result=None;status='unknown';issue=str(exc)
        cases.append({'case':name,'expected_ways':expected,'actual_ways':result,
                      'status':status,'issue':issue})
    report={'engine':'routingkit','version':args.revision,'fresh_execution':True,
        'dataset_sha256':hashlib.sha256(raw).hexdigest(),'cases':cases,
        'scope':'RoutingKit CH algorithm only; roads/access/rules supplied from common imported DriveMate graph; no independent turn-rule decoding, roundabout-number or live GPS comparisons',
        'backend_family':'RoutingKit ContractionHierarchy (C++ BSD-2-Clause)',
        'score_out_of_10':round(10*sum(r['status']=='pass' for r in cases)/len(cases),2)
          if all(r['status']!='unknown' for r in cases) else None}
    (output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'engine':'RoutingKit CH','passed':sum(r['status']=='pass' for r in cases),
        'failed':sum(r['status']=='fail' for r in cases),
        'unknown':sum(r['status']=='unknown' for r in cases),'cases':len(cases)}))
    if any(r['status']=='unknown' for r in cases):raise SystemExit(2)
    # A confirmed routing failure is evidence and should not be masked as an
    # infrastructure failure: publish it to the scorecard and highlight it.
if __name__=='__main__':main()
