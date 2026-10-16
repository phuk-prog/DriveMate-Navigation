"""GPS-003: actual real-map matcher replay; only GPS observations simulated.

Map-generated labels are supplied-map agreement, NOT independent road/GNSS truth.
Raw XML selection and signal manifest are frozen before any matcher runs.
"""
import argparse
from hashlib import sha256
import json
from math import cos,radians
import os
import platform
from pathlib import Path
from time import perf_counter_ns
import xml.etree.ElementTree as ET
from benchmarks.itinero_public_probe import EXPECTED_XML_HASH,SOURCE
from benchmarks.public_temporal_gps import _bearing,_point
from gps.fix_quality import GPSFix
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher
from map_data import import_osm_xml,Provenance
from map_data.osm_xml import _haversine

ROOT=Path(__file__).resolve().parents[1]
CATEGORIES=('clear','noisy_2m','weak_60m','stale','future','duplicate','speed_100mps','gap_31s')


def judge(expectation,status,edge_id,expected_edge,history_preserved):
    checks=dict(no_road_claim_when_withheld=status=='MATCHED' or edge_id is None,
                no_wrong_generating_edge=status!='MATCHED' or edge_id==expected_edge)
    if expectation=='MATCH':checks['required_clear_output']=status=='MATCHED' and edge_id==expected_edge
    elif expectation=='REJECT':
        checks['rejected']=status=='REJECTED';checks['history_preserved']=history_preserved
    elif expectation=='WITHHOLD':checks['withheld']=status!='MATCHED' and edge_id is None
    elif expectation!='SAFE':raise ValueError('Unknown expectation')
    return dict(passed=all(checks.values()),checks=checks)


def freeze(raw):
    if sha256(raw).hexdigest()!=EXPECTED_XML_HASH:raise ValueError('Pinned map changed')
    root=ET.fromstring(raw)
    nodes={n.get('id'):(float(n.get('lat')),float(n.get('lon'))) for n in root.findall('node')}
    segments=[]
    for w in sorted(root.findall('way'),key=lambda w:int(w.get('id'))):
        tags={t.get('k'):t.get('v') for t in w.findall('tag')}
        if tags.get('highway') not in ('residential','unclassified','tertiary'):continue
        if any(k.endswith('conditional') for k in tags):continue
        if any(tags.get(k) not in (None,'yes','designated','permissive') for k in ('access','vehicle','motor_vehicle','motorcar')):continue
        direction=tags.get('oneway','').lower()
        if direction not in ('','no','0','false','yes','1','true','-1','reverse'):continue
        refs=[n.get('ref') for n in w.findall('nd')]
        for i,(a,b) in enumerate(zip(refs,refs[1:])):
            if a not in nodes or b not in nodes:continue
            length=_haversine(nodes[a],nodes[b])
            if not 20<=length<=250:continue
            reverse=direction in ('-1','reverse')
            src,dst=(b,a) if reverse else (a,b)
            segments.append(dict(id=f'GPS-003-B{len(segments)+1}',way_id=w.get('id'),segment=i,name=tags.get('name'),raw_tags=tags,
                                 expected_edge=f"w:{w.get('id')}:{i}:{'r' if reverse else 'f'}",start=nodes[src],end=nodes[dst],length_m=length))
            if len(segments)==3:break
        if len(segments)==3:break
    if len(segments)!=3:raise ValueError('Required raw-map segments unavailable; no substitutes')
    cases=[]
    for segment in segments:
        for category in CATEGORIES:
            events=[]
            for index,ratio in enumerate((.3,.4,.5)):
                t=1000+2000*index;now=t;accuracy=3.;speed=10.;lat,lon=_point(segment['start'],segment['end'],ratio);expectation='MATCH'
                if index==1:
                    if category=='noisy_2m':lon+=2/(111195*cos(radians(lat)));accuracy=5.;expectation='SAFE'
                    elif category=='weak_60m':accuracy=60.;expectation='WITHHOLD'
                    elif category=='stale':t=2000;now=13001;expectation='REJECT'
                    elif category=='future':t=9000;now=3000;expectation='REJECT'
                    elif category=='duplicate':t=1000;now=3000;expectation='REJECT'
                    elif category=='speed_100mps':speed=100.;expectation='REJECT'
                if category=='stale' and index==2:t=now=15000
                if category=='gap_31s' and index>=1:t=now=32000+2000*(index-1)
                events.append(dict(fix=[t,lat,lon,accuracy,speed,_bearing(segment['start'],segment['end'])],now_ms=now,expectation=expectation))
            cases.append(dict(id=segment['id']+'-'+category,base_segment=segment['id'],category=category,expected_edge=segment['expected_edge'],events=events))
    return dict(test_id='GPS-003',classification='real licensed public map; simulated GPS; map-derived identity and analytical fault oracles',
                source_url=SOURCE,map_sha256=EXPECTED_XML_HASH,attribution='OpenStreetMap contributors; ODbL',
                selection='first three raw-XML eligible segments numerically by way/segment, length20..250m; before importer/matcher',
                independent_real_road_truth=False,segments=segments,cases=cases,
                analytical_expectations='clear/recovery must match generating directed segment; noisy may withhold but never claim other segment; weak must withhold; stale/future/duplicate/impossible speed must reject and preserve last accepted fix',
                gap_scope='31s source-clock gap, no intermediate updates; reacquisition only, not proof of guidance suppression during silence',
                clocks='deterministic monotonic millisecond source/receipt clocks; accelerated, not wall-clock soak')


def main():
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');a=p.parse_args()
    area=ROOT/'results';raw=(area/'gps003-map.osm').read_bytes();path=area/'gps003-cases.json'
    frozen=freeze(raw)
    if a.prepare:
        path.write_text(json.dumps(frozen,indent=2)+'\n');print(path.read_text());return
    if json.loads(path.read_text())!=frozen:raise ValueError('Frozen cases changed')
    data=import_osm_xml(raw,provenance=Provenance('public Manchester GPS-003','Geofabrik260901',SOURCE,'OpenStreetMap contributors; ODbL'))
    rows=[];counts=dict(correct=0,confident_wrong=0,withheld=0,rejected=0)
    for case in frozen['cases']:
        matcher=TemporalRoadMatcher(DirectedRoadMatcher(data.graph,data.coordinates));steps=[]
        for index,event in enumerate(case['events']):
            previous=matcher.previous_valid_fix;begin=perf_counter_ns()
            result=matcher.update(GPSFix(*event['fix']),now_ms=event['now_ms']);elapsed=perf_counter_ns()-begin
            judged=judge(event['expectation'],result.status,result.edge_id,case['expected_edge'],matcher.previous_valid_fix==previous)
            if result.status=='MATCHED':counts['correct' if result.edge_id==case['expected_edge'] else 'confident_wrong']+=1
            else:counts['withheld']+=1
            counts['rejected']+=int(result.status=='REJECTED')
            steps.append(dict(event=index,expected=event['expectation'],actual_status=result.status,actual_edge=result.edge_id,reason=result.reason,candidates=result.candidate_count,calculation_ns=elapsed,**judged))
        rows.append(dict(case_id=case['id'],category=case['category'],outcome='PASS' if all(s['passed'] for s in steps) else 'FAIL',events=steps))
    report=dict(test_id='GPS-003',system='DMN',run_sha=os.environ.get('GITHUB_HEAD_SHA'),execution='actual_local_python',
                version='repository TemporalRoadMatcher/DirectedRoadMatcher default limits',manifest=frozen,
                environment=dict(python=platform.python_version(),system=platform.system(),machine=platform.machine(),clock='perf_counter_ns',clock_resolution_s=__import__('time').get_clock_info('perf_counter').resolution),
                source_sha256={name:sha256((ROOT/name).read_bytes()).hexdigest() for name in ('benchmarks/real_map_gps_recovery.py','gps/fix_quality.py','gps/matcher.py','gps/temporal_matcher.py','map_data/osm_xml.py')},
                map_sha256=EXPECTED_XML_HASH,oracle_sha256=sha256(path.read_bytes()).hexdigest(),
                cases=rows,counts=counts,passed=sum(r['outcome']=='PASS' for r in rows),total=len(rows),events=sum(len(r['events']) for r in rows),
                external_engines_executed=0,rank=None,score_out_of_ten=None,independent_real_road_truth=False,
                real_GNSS_measurements=0,integrated_navigation_or_emulator=False)
    (area/'gps003-DMN.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    if report['passed']!=report['total']:raise SystemExit('GPS-003 failed; retain and diagnose without changing cases')

if __name__=='__main__':main()
