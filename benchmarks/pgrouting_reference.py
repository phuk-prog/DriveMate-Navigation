"""Run actual pgRouting/Boost.Dijkstra in a disposable local PostgreSQL Docker container.

The authored graph and restrictions are translated to explicit directed edge
states by the same shared fixture contract as RoutingKit; pgRouting independently
searches these states. It is NOT testing native OSM importing or roundabout/GPS
guidance. All SQL is generated solely from fixed synthetic numeric test data.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
from benchmarks.whole_drive import fixture,prepared,reference_requests
from benchmarks.routingkit_reference import compile_query
from benchmarks.whole_drive_reference import ways

CONTAINER='dm-pgrouting-reference'

def sql_for_query(p,start,end):
    n,sink_source,sink,arcs,labels=compile_query(p,start,end)
    values=', '.join(f'({i+1},{u+1},{v+1},{float(cost)})' for i,(u,v,cost) in enumerate(arcs))
    statements=[
       'DROP TABLE IF EXISTS dm_reference_edges;',
       'CREATE TEMP TABLE dm_reference_edges(id bigint, source bigint, target bigint, cost float8, reverse_cost float8 DEFAULT -1);',
       f'INSERT INTO dm_reference_edges(id,source,target,cost) VALUES {values};' if arcs else '',
       f"SELECT edge FROM pgr_dijkstra('SELECT id,source,target,cost,reverse_cost FROM dm_reference_edges', {sink_source+1}, {sink+1}, true) WHERE edge>0 ORDER BY seq;",
    ]
    return '\n'.join(s for s in statements if s),labels

def execute(p,start,end):
    sql,labels=sql_for_query(p,start,end)
    proc=subprocess.run(['docker','exec','-i',CONTAINER,'psql','-v','ON_ERROR_STOP=1',
                        '-U','postgres','-d','postgres','-qAt','-c',sql],
                        text=True,capture_output=True,timeout=40,check=True)
    vals=[int(s.strip()) for s in proc.stdout.splitlines() if s.strip()]
    if not vals:return None
    if any(not 1<=v<=len(labels) for v in vals):raise ValueError('Invalid pgRouting arc number')
    chosen=[labels[v-1] for v in vals if labels[v-1] is not None]
    return ways(chosen)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--image',required=True)
    args=parser.parse_args()
    probe=subprocess.run(['docker','exec',CONTAINER,'psql','-U','postgres','-d','postgres',
                          '-At','-c','CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS pgrouting; SELECT pgr_version();'],
                         text=True,capture_output=True,check=True,timeout=30)
    version=probe.stdout.strip().splitlines()[-1]
    image_id=subprocess.run(['docker','inspect','-f','{{.Image}}',CONTAINER],text=True,
                            capture_output=True,check=True).stdout.strip()
    p=prepared();raw=fixture()
    result=[]
    for item in reference_requests():
        a,b=item['nodes'];expected=item['ways']
        try:
            other=execute(p,'osm:'+str(a),'osm:'+str(b))
            status='pass' if other==expected else 'fail';reason=None if status=='pass' else 'non_equivalent_route'
        except (subprocess.SubprocessError,ValueError,TimeoutError) as exc:
            other=None;status='unknown';reason=str(exc)
        result.append({'case':item['id'],'expected_ways':expected,'actual_ways':other,
                       'status':status,'issue':reason})
    evidence={'engine':'pgrouting','version':version,'container_tag':args.image,'image_id':image_id,
              'fresh_execution':True,'dataset_sha256':hashlib.sha256(raw).hexdigest(),
              'scope':'Actual pgRouting Dijkstra on explicit directed edge-state data from shared fixture. Does not validate pgRouting native OSM importer, independent turn restrictions, GPS or roundabout exit instructions.',
              'cases':result}
    out=Path('results/pgrouting');out.mkdir(parents=True,exist_ok=True)
    (out/'comparison.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'engine':'pgRouting','passed':sum(x['status']=='pass' for x in result),
        'failed':sum(x['status']=='fail' for x in result),
        'unknown':sum(x['status']=='unknown' for x in result),'cases':len(result)}))
    if any(x['status']=='unknown' for x in result):raise SystemExit(2)

if __name__=='__main__':main()
