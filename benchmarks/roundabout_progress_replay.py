"""Trusted-road controller replay against preserved entry-context reference outputs.

Does not run GraphHopper or simulate its journey controller. Reuses verified raw
instruction evidence on an unchanged original fixture; no GPS/physics/app claim.
"""
import hashlib,json
from pathlib import Path
from benchmarks.roundabout_reference import fixture
from map_data.osm_xml import import_osm_xml,Provenance
from engine.reconciled import prepare_navigation

def main():
    raw,_=fixture();reference=json.loads(Path('results/roundabout_reference/comparison.json').read_text())
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=reference['dataset_sha256']:raise ValueError('Historical reference fixture mismatch')
    m=import_osm_xml(raw,provenance=Provenance('synthetic','v1','original fixture','OpenStreetMap contributors'))
    p=prepare_navigation(m.graph,m.coordinates);rows=[]
    for expected,end in enumerate((2,4,6,7),1):
        historical=reference['cases'][expected-1]
        if historical['graphhopper_exits']!=[expected] or historical['graphhopper_status']!='pass':raise ValueError('Unverified historical reference instruction')
        j=p.journey(f'w:{200+end}:0:f',800000);t=1;checks=[]
        s=j.start(p.position('w:10:0:f',500000),t)
        checks.append({'road':'entry','fraction':500000,'exit_number':j.roundabouts()[0].exit_number})
        for i in range(end):
            for q in (0,250000,750000,1000000):
                t+=1;road=f'w:100:{i}:f';s=j.observe(p.position(road,q),t)
                info=j.roundabouts()
                checks.append({'road':road,'fraction':q,'exit_number':info[0].exit_number if info else None})
        t+=1;j.observe(p.position(f'w:{200+end}:0:f',250000),t)
        clear=j.roundabouts()==()
        t+=1;arrived=j.observe(p.position(f'w:{200+end}:0:f',900000),t)
        passed=all(c['exit_number']==expected for c in checks) and clear and arrived.status=='arrived'
        rows.append({'test_id':'entry_exit_'+str(expected),'status':'pass' if passed else 'fail',
          'expected_original_exit':expected,'preserved_graphhopper_entry_exit':historical['graphhopper_exits'][0],
          'check_count':len(checks),'observations':checks,'cleared_after_exit':clear,'arrival':arrived.status,
          'reference_classification':'Preserved actual GraphHopper entry instruction, no new engine execution',
          'first_place':'No live competitor ranking established'})
    result={'scope':'Four deterministic trusted-road journey replays; source fixture unchanged; historical reference only',
       'dataset_sha256':digest,'cases':rows,'number_checks':sum(r['check_count'] for r in rows)}
    Path('results/roundabout_progress_replay.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'journeys':len(rows),'number_checks':result['number_checks'],'statuses':[r['status'] for r in rows]}))
    if any(r['status']!='pass' for r in rows):raise SystemExit(1)
if __name__=='__main__':main()
