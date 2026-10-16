"""REROUTE-001 analytical lifecycle replay with actual DMN core route calculations.

Clock delivery and on-route/reliability assessments are synthetic declarations;
no phone service, real GNSS, network cancellation or competitor is simulated as
an executed engine. Frozen acceptance is separate from controller implementation.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from engine import shortest_route,RouteNotFound
from engine.rerouting_controller import ReroutingController,RerouteRequest
from map_data import Provenance,import_osm_xml

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'benchmarks/fixtures/synthetic-reroute-001.json'
MAP=ROOT/'benchmarks/fixtures/synthetic-route-002.xml'
ADDITIONAL=ROOT/'benchmarks/fixtures/synthetic-reroute-001-additional.json'
EXPECTED_EDGES={'initial':('w:40:0:f','w:50:0:f'),
                'detour':('w:95:0:f','w:100:0:f','w:50:0:f'),
                'replacement':('w:20:0:f',)}


def load_fixture(path=FIXTURE):return json.loads(path.read_text())


def run_dmn(fixture_path=FIXTURE):
    fixture=load_fixture(fixture_path)
    data=import_osm_xml(MAP.read_bytes(),provenance=Provenance(
        'synthetic REROUTE-001','synthetic-v1','frozen analytical controller replay',
        'Synthetic OSM format; no OpenStreetMap contributor road data used'))
    cases=[];total_calculations=0
    for case in fixture['cases']:
        calculations=0
        def plan(name):
            nonlocal calculations
            calculations+=1
            source='osm:2' if name=='replacement' else 'osm:4'
            blocked={'initial':[],'replacement':[],'detour':['w:40:0:f'],
                     'unreachable':['w:40:0:f','w:95:0:f']}[name]
            try:route=shortest_route(data.graph,source,'osm:3',blocked_edges=blocked)
            except RouteNotFound:
                if name!='unreachable':raise AssertionError('Required analytical planner route missing')
                return None
            if name=='unreachable' or route.edge_ids!=EXPECTED_EDGES[name]:
                raise AssertionError('Core route disagrees with independently declared analytical path')
            return route
        def route_name(route):
            if route is None:return 'NONE'
            return next((name for name,edges in EXPECTED_EDGES.items() if route.edge_ids==edges),'UNRECOGNISED')
        controller=ReroutingController(**fixture['parameters'])
        controller.begin(plan('initial'),now_ms=0)
        tokens={};steps=[]
        for index,event in enumerate(case['events']):
            action=event['action'];checks={};step={'event':index,'action':action}
            if action=='observe':
                token=controller.observe(timestamp_ms=event['timestamp_ms'],now_ms=event['now_ms'],
                                         reliable=event['reliable'],on_route=event['on_route'])
                expected=event.get('expect_request')
                checks['expected_request_creation']=(token is not None)==(expected is not None)
                if token is not None:
                    checks['request_id_unique']=all(t.request_id!=token.request_id for t in tokens.values())
                    if expected is not None:tokens[expected]=token
                    step['request_id']=token.request_id
                step['expected_request_alias']=expected
            elif action=='complete':
                token=tokens.get(event['token'],RerouteRequest(999999,0,0,0))
                accepted=controller.complete(token,plan(event['planner']),now_ms=event['now_ms'])
                checks['expected_install_decision']=accepted==event['expect_accepted']
                step['actual_accepted']=accepted
            elif action=='begin':controller.begin(plan(event['planner']),now_ms=event['now_ms'])
            elif action=='stop':controller.stop(now_ms=event['now_ms'])
            else:raise ValueError('Unknown frozen action')
            if 'expect_route' in event:
                checks['expected_installed_route']=route_name(controller.installed_route)==event['expect_route']
                step['actual_route']=route_name(controller.installed_route)
            step['checks']=checks;step['passed']=all(checks.values());steps.append(step)
        total_calculations+=calculations
        cases.append({'case_id':case['id'],'outcome':'PASS' if all(s['passed'] for s in steps) else 'FAIL',
                      'actual_core_route_calculations':calculations,'events':steps})
    return {'test_id':fixture.get('test_id','REROUTE-001'),'system':'DMN','version':'repository isolated ReroutingController and shortest_route',
            'execution':'actual_local_python_with_declared_synthetic_delivery',
            'classification':'synthetic analytical lifecycle conformance only','configuration':fixture['parameters'],
            'map_sha256':sha256(MAP.read_bytes()).hexdigest(),'oracle_sha256':sha256(fixture_path.read_bytes()).hexdigest(),
            'controller_sha256':sha256((ROOT/'engine/rerouting_controller.py').read_bytes()).hexdigest(),
            'harness_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
            'actual_core_route_calculations':total_calculations,'cases':cases,
            'real_GNSS_measurements':0,'android_device_tests':0,'external_engine_executions':0,
            'physical_computation_cancellation_implemented':False}


def coverage(report):
    cases=load_fixture()['cases'];ids=[c['id'] for c in cases]
    if (report.get('test_id')!='REROUTE-001' or report.get('system')!='DMN'
            or report.get('execution')!='actual_local_python_with_declared_synthetic_delivery'
            or report.get('map_sha256')!=sha256(MAP.read_bytes()).hexdigest()
            or report.get('oracle_sha256')!=sha256(FIXTURE.read_bytes()).hexdigest()
            or [c['case_id'] for c in report['cases']]!=ids
            or any(c['outcome'] not in ('PASS','FAIL') for c in report['cases'])):
        raise ValueError('Incomplete or nonmatching executed controller cohort')
    roster=['DMN']+[r['name'] for r in json.loads((ROOT/'config/dmn-engine-first-programme.json').read_text())['reference_families']]
    rows=[]
    for name in roster:
        if name=='DMN':
            passed=sum(c['outcome']=='PASS' for c in report['cases'])
            rows.append({'system':name,'rank':1,'score_out_of_ten':10*passed/len(ids),
                         'passed':passed,'failed':len(ids)-passed,'unsupported':0,'not_run':0,'cases':report['cases']})
            continue
        unsupported=name in ('OSRM','Valhalla','GraphHopper','openrouteservice','BRouter')
        reason=('Integrated coordinate-routing/batch endpoint does not expose equivalent off-route evidence, cooldown, session or callback installation state.' if unsupported else
                'Executable app/native lifecycle harness not implemented' if name in ('OsmAnd','Organic Maps') else
                'No established permitted automated lifecycle replay interface' if name=='Waze' else
                'No configured permitted access and equivalent lifecycle harness')
        status='UNSUPPORTED' if unsupported else 'NOT_RUN'
        rows.append({'system':name,'rank':None,'score_out_of_ten':None,'passed':0,'failed':0,
                     'unsupported':len(ids) if unsupported else 0,'not_run':0 if unsupported else len(ids),
                     'cases':[{'case_id':cid,'outcome':status,'reason':reason} for cid in ids]})
    return {'test_id':'REROUTE-001','formula':'10 * passed / sixteen frozen cases; unavailable cohorts unranked',
            'scope':'Only DMN has an executed lifecycle cohort; no competitor quality ranking is supported.','rows':rows}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if not a.output.resolve().is_relative_to((ROOT/'results').resolve()):raise ValueError('Write ephemeral evidence under results only')
    report=run_dmn();additional=run_dmn(ADDITIONAL);result={'report':report,'additional_report':additional,'coverage':coverage(report)}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if any(c['outcome']!='PASS' for r in (report,additional) for c in r['cases']):raise SystemExit('REROUTE-001 failed; retain evidence and diagnose')

if __name__=='__main__':main()
