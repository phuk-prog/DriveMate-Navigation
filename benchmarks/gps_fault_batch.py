"""GPS-002: frozen synthetic streaming quality, ambiguity and recovery checks.

A batch snap/match API cannot stand in for a stream's reception clock, reset or
trusted-history state. Unsupported interfaces never receive fabricated verdicts.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher
from map_data import Provenance, import_osm_xml

ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'benchmarks/fixtures/synthetic-gps-002.xml'
ORACLE=ROOT/'benchmarks/fixtures/synthetic-gps-002.json'


def load_cases():
    return json.loads(ORACLE.read_text())['cases']


def run_dmn():
    data=import_osm_xml(MAP.read_bytes(),provenance=Provenance(
        'synthetic GPS-002','synthetic-v1','hand-declared analytical controls',
        'Synthetic OSM format; no OpenStreetMap contributor road data used'))
    cases=[]
    for case in load_cases():
        matcher=TemporalRoadMatcher(DirectedRoadMatcher(data.graph,data.coordinates))
        steps=[]
        for index,event in enumerate(case['events']):
            if event.get('action')=='reset':
                matcher.reset()
                checks={'anchor_cleared':matcher.anchor_edge_id is None,
                        'history_cleared':matcher.previous_valid_fix is None}
                steps.append({'event':index,'action':'reset','checks':checks,
                              'passed':all(checks.values())})
                continue
            previous=matcher.previous_valid_fix
            result=matcher.update(GPSFix(*event['fix']),now_ms=event.get('now_ms'))
            checks={'expected_status':result.status==event['expected_status'],
                    'no_road_claim_when_withheld':result.status=='MATCHED' or result.edge_id is None}
            if event.get('expected_way') is not None:
                checks['expected_directed_way']=(result.edge_id is not None and
                    result.edge_id.split(':')[1]==str(event['expected_way']) and
                    result.edge_id.endswith(':f'))
            if event.get('preserve_trusted_fix'):
                checks['trusted_fix_unchanged']=matcher.previous_valid_fix==previous
            steps.append({'event':index,'expected_status':event['expected_status'],
                          'actual_status':result.status,'reason':result.reason,
                          'checks':checks,'passed':all(checks.values())})
        cases.append({'case_id':case['id'],'category':case['category'],
                      'outcome':'PASS' if all(s['passed'] for s in steps) else 'FAIL',
                      'events':steps})
    return {'test_id':'GPS-002','classification':'synthetic analytical streaming safety contract',
            'system':'DMN','version':'repository TemporalRoadMatcher / default limits',
            'execution':'actual_local_python','map_sha256':sha256(MAP.read_bytes()).hexdigest(),
            'oracle_sha256':sha256(ORACLE.read_bytes()).hexdigest(),'cases':cases,
            'independent_real_road_truth':False,'physical_tunnel_or_GNSS_measurements':0}


def coverage(report):
    if report.get('system')!='DMN' or report.get('execution')!='actual_local_python':
        raise ValueError('No eligible executed DMN stream report')
    if (report.get('test_id')!='GPS-002' or report.get('map_sha256')!=sha256(MAP.read_bytes()).hexdigest()
            or report.get('oracle_sha256')!=sha256(ORACLE.read_bytes()).hexdigest()
            or [c['case_id'] for c in report['cases']]!=[c['id'] for c in load_cases()]):
        raise ValueError('Report does not match frozen cohort')
    roster=['DMN']+[r['name'] for r in json.loads((ROOT/'config/dmn-engine-first-programme.json').read_text())['reference_families']]
    rows=[]
    unsupported={
        'OSRM':'Integrated Match API is batch geometry; no equivalent reception-clock, reset and trusted-stream-history contract.',
        'Valhalla':'Integrated trace_attributes API is batch geometry; no equivalent reception-clock, reset and trusted-stream-history contract.',
        'GraphHopper':'Integrated map-matching API is batch geometry; no equivalent reception-clock, reset and trusted-stream-history contract.',
        'openrouteservice':'Integrated pointwise snap API has no streaming quality/reset/history contract.',
        'BRouter':'Integrated routing API does not consume a GPS observation stream.'}
    gaps={'OsmAnd':'Executable app/native GPS lifecycle replay harness not implemented.',
          'Organic Maps':'Executable app/native GPS lifecycle replay harness not implemented.',
          'Waze':'No permitted automated GPS lifecycle replay interface established.'}
    for name in roster:
        if name=='DMN':
            cases=report['cases'];passed=sum(c['outcome']=='PASS' for c in cases)
            if any(c['outcome'] not in ('PASS','FAIL') for c in cases):
                raise ValueError('Incomplete judged cohort cannot receive a score')
            rows.append({'system':name,'rank':1,'passed':passed,'failed':len(cases)-passed,
                         'unsupported':0,'not_run':0,'score_out_of_ten':round(10*passed/len(cases),3),
                         'cases':cases})
        else:
            outcome='UNSUPPORTED' if name in unsupported else 'NOT_RUN'
            reason=unsupported.get(name,gaps.get(name,'No configured permitted access and equivalent GPS lifecycle interface.'))
            rows.append({'system':name,'rank':None,'passed':0,'failed':0,
                         'unsupported':len(load_cases()) if outcome=='UNSUPPORTED' else 0,
                         'not_run':len(load_cases()) if outcome=='NOT_RUN' else 0,
                         'score_out_of_ten':None,
                         'cases':[{'case_id':c['id'],'outcome':outcome,'reason':reason} for c in load_cases()]})
    return {'test_id':'GPS-002','formula':'10 * fully passing cases / 16 frozen cases; ties share rank',
            'ranking_scope':'Only DMN has a judged stream contract here; no competitor quality comparison is possible.',
            'rows':rows}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if not a.output.resolve().is_relative_to((ROOT/'results').resolve()):
        raise ValueError('Write ephemeral report under results only')
    report=run_dmn(); result={'report':report,'coverage':coverage(report)}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if any(c['outcome']!='PASS' for c in report['cases']):
        raise SystemExit('GPS-002 failed; retain report and diagnose before tuning')

if __name__=='__main__':main()
