"""Honest execution coverage: missing references are pending, never scored."""
import csv,json,shutil,importlib.util
from pathlib import Path

TARGETS=('routing','known_legality','reroute_path','gps_path_matching','gps_loss_recovery','roundabout_numbers','lane_assignment','instruction_timing')
SYSTEMS=(
 ('Valhalla','https://valhalla.github.io/valhalla/','No local service/container or Python binding and no imported equivalent tiles'),
 ('OSRM MLD','https://project-osrm.org/docs/v26.6.1/http','No local OSRM executable/container and no preprocessed identical map'),
 ('GraphHopper','https://github.com/graphhopper/graphhopper',''),
 ('OsmAnd','https://osmand.net/docs/technical/build-osmand/','No configured app/device replay harness or equivalent generated map pack'),
 ('Organic Maps','https://github.com/organicmaps/organicmaps','No configured app/device replay harness or equivalent generated map pack'),
 ('BRouter','https://github.com/abrensch/brouter','No local BRouter runtime, motorcar profile or equivalent RD5 dataset'),
 ('HERE','https://docs.here.com/here-sdk/docs/android-navigation','No supplied authorised SDK adapter/credentials, device replay harness or verified identical-map parity'),
 ('Mapbox','https://docs.mapbox.com/android/navigation/guides/','No supplied authorised SDK adapter/credentials, device replay harness or verified identical-map parity'),
 ('TomTom','https://docs.tomtom.com/navigation/android/guides/advanced/simulation-location-provider','No supplied authorised SDK adapter/credentials, device replay harness or verified identical-map parity'),
 ('openrouteservice','https://giscience.github.io/openrouteservice/','Provisional tenth target: no local runtime/container or equivalent imported dataset')
)

def build():
    report=json.loads(Path('results/whole_drive/reference/comparison.json').read_text())
    rows=[]
    for name,url,blocker in SYSTEMS:
        scopes={t:'pending execution' for t in TARGETS}
        if name=='GraphHopper':
            scopes.update(routing='fresh: 9 route cases',known_legality='fresh static restriction/one-way cases',
                          reroute_path='fresh stateless replan; live historical reroute N/A',
                          gps_path_matching='fresh: 4 clean batch paths; live parity N/A',
                          roundabout_numbers='fresh: 4 exit numbers',gps_loss_recovery='not compared: batch matcher is not a live controller',
                          lane_assignment='not compared: lane assignment adapter unavailable',instruction_timing='not compared: live/audio scheduler unavailable')
        rows.append({'system':name,'execution':'fresh actual reference' if name=='GraphHopper' else 'not executed',
                     'version':'11.1' if name=='GraphHopper' else None,'targets':scopes,'blocker':blocker,
                     'official_source':url,'score':None,'provisional_target':name=='openrouteservice'})
    excluded=[r for r in rows if r['execution']!='fresh actual reference']
    executed=[r for r in rows if r['execution']=='fresh actual reference']
    result={'external_targets':len(rows),'executed_external_systems':len(executed),'unexecuted_external_systems':len(excluded),
            'tenth_provenance':'Saved registry named nine external systems; openrouteservice added provisionally, not asserted to be the original tenth',
            'dataset_sha256':report['dataset_sha256'],'systems':executed,
            'excluded_unexecuted_systems':[{'name':r['system'],'reason':r['blocker']} for r in excluded],
            'runtime_inventory':{n:shutil.which(n) for n in ('java','docker','podman','osrm-routed','valhalla_service','brouter','adb','mvn','gradle')},
            'valhalla_python_binding':importlib.util.find_spec('valhalla') is not None,
            'policy':'No unexecuted system is failed or ranked. Different datasets/costs/interfaces and offline vs live matching cannot be turned into a fair speed or whole-app ranking.'}
    out=Path('results/whole_drive');(out/'ten_system_matrix.json').write_text(json.dumps(result,indent=2))
    with (out/'ten_system_matrix.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['system','execution','version',*TARGETS,'blocker','official_source'])
        for r in executed:writer.writerow([r['system'],r['execution'],r['version'],*[r['targets'][t] for t in TARGETS],r['blocker'],r['official_source']])
    return result
if __name__=='__main__':
    result=build();print(json.dumps({'external_targets':result['external_targets'],'fresh_external_executions':1,'pending_external_executions':9}))
