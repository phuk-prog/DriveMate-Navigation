"""ARRIVAL-001 analytical replay. Actual DMN routes, synthetic observation state."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from engine import shortest_route
from engine.arrival_controller import ArrivalController
from map_data import Provenance,import_osm_xml

ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'benchmarks/fixtures/synthetic-junction-001.xml'
ORACLE=ROOT/'benchmarks/fixtures/synthetic-arrival-001.json'


def run_dmn(fixture_path=ORACLE):
    fixture=json.loads(fixture_path.read_text())
    data=import_osm_xml(MAP.read_bytes(),provenance=Provenance('synthetic ARRIVAL-001','synthetic-v1','analytical fixture','Synthetic OSM format; no OpenStreetMap contributor road data used'))
    rows=[];calculations=0
    for case in fixture['cases']:
        controller=ArrivalController(**fixture['parameters'])
        def begin(name,now):
            nonlocal calculations
            dest=fixture['destinations'][name]
            route=shortest_route(data.graph,'osm:1','osm:'+str(dest['node']))
            expected=('w:101:0:f','w:102:0:f' if name=='north' else 'w:103:0:f')
            if route.edge_ids!=expected:raise AssertionError('Unexpected analytical route')
            calculations+=1
            return controller.begin(dest['position'],route_length_m=route.length_m,now_ms=now)
        token=begin('north',0);events=[];arrivals=0
        for i,e in enumerate(case['events']):
            checks={};row=dict(event=i,action=e['action'])
            if e['action']=='observe':
                fields={k:e[k] for k in ('timestamp_ms','now_ms','position','accuracy_m','reliable','on_route','remaining_m')}
                status=controller.observe(context_revision=token,**fields)
                if status=='ARRIVED':arrivals+=1
                checks['expected_status']=status==e['expect_status']
                row.update(expected_status=e['expect_status'],actual_status=status)
            elif e['action']=='stop':controller.stop(now_ms=e['now_ms'])
            elif e['action']=='begin':token=begin(e['destination'],e['now_ms']);arrivals=0
            else:raise ValueError('Unknown action')
            if 'expect_arrived' in e:checks['arrival_state']=controller.arrived==e['expect_arrived']
            checks['at_most_one_arrival_in_context']=arrivals<=1
            if e['action']=='observe':checks['arrival_latch_matches_status']=controller.arrived==(status in ('ARRIVED','ALREADY_ARRIVED'))
            row.update(checks=checks,passed=all(checks.values()),actual_arrived=controller.arrived,context_revision=controller.revision)
            events.append(row)
        rows.append(dict(case_id=case['id'],outcome='PASS' if all(e['passed'] for e in events) else 'FAIL',events=events))
    return dict(test_id=fixture['test_id'],system='DMN',version='repository isolated ArrivalController and shortest_route',execution='actual_local_python_with_declared_synthetic_assessments',classification='synthetic analytical only; no surveyed real-road truth',configuration=fixture['parameters'],map_sha256=sha256(MAP.read_bytes()).hexdigest(),oracle_sha256=sha256(fixture_path.read_bytes()).hexdigest(),controller_sha256=sha256((ROOT/'engine/arrival_controller.py').read_bytes()).hexdigest(),harness_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),run_sha=os.environ.get('GITHUB_HEAD_SHA') or os.environ.get('GITHUB_SHA'),actual_core_route_calculations=calculations,real_GNSS_measurements=0,android_device_tests=0,external_engine_executions=0,cases=rows)


def coverage(report):
    ids=[c['id'] for c in json.loads(ORACLE.read_text())['cases']]
    if (report['test_id']!='ARRIVAL-001' or report['system']!='DMN' or report['execution']!='actual_local_python_with_declared_synthetic_assessments'
            or report['map_sha256']!=sha256(MAP.read_bytes()).hexdigest() or report['oracle_sha256']!=sha256(ORACLE.read_bytes()).hexdigest()
            or [c['case_id'] for c in report['cases']]!=ids or any(c['outcome'] not in ('PASS','FAIL') for c in report['cases'])):
        raise ValueError('Nonmatching or incomplete executed cohort')
    roster=['DMN']+[r['name'] for r in json.loads((ROOT/'config/dmn-engine-first-programme.json').read_text())['reference_families']]
    rows=[]
    for name in roster:
        if name=='DMN':
            passed=sum(c['outcome']=='PASS' for c in report['cases'])
            rows.append(dict(system=name,rank=1,score_out_of_ten=10*passed/len(ids),passed=passed,failed=len(ids)-passed,cases=report['cases']))
            continue
        unsupported=name in ('OSRM','Valhalla','GraphHopper','openrouteservice','BRouter')
        status='UNSUPPORTED' if unsupported else 'NOT_RUN'
        reason=('Current static route/directions endpoint cannot express fresh fixes, live route progress, session tokens or corroborated arrival state' if unsupported else
                'No executable app/native live arrival replay harness implemented' if name in ('OsmAnd','Organic Maps') else
                'No established permitted automated live arrival replay interface' if name=='Waze' else
                'No configured permitted access and equivalent live arrival harness; no paid calls authorized')
        rows.append(dict(system=name,rank=None,score_out_of_ten=None,passed=0,failed=0,cases=[dict(case_id=i,outcome=status,reason=reason) for i in ids]))
    return dict(test_id='ARRIVAL-001',formula='10 * passed / 20; incomplete/unavailable cohorts unranked',scope='DMN-only arrival conformance; no comparative quality ranking',rows=rows)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if not a.output.resolve().is_relative_to((ROOT/'results').resolve()):raise ValueError('Output outside results')
    r=run_dmn();result=dict(report=r,coverage=coverage(r))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if any(c['outcome']!='PASS' for c in r['cases']):raise SystemExit('ARRIVAL-001 failed; preserve evidence')

if __name__=='__main__':main()
