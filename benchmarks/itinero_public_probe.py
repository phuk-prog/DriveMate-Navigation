"""REF-006 real public-map executable probe; synthetic endpoints, no personal GPS.

Route output/endpoint contract only. No independent road legality or GPS-signal
quality verdict is inferred. Selected cases never depend on Itinero output.
"""
import argparse
from hashlib import sha256
import json
from math import isfinite
import os
from pathlib import Path
from benchmarks.public_uk_probe import _scenarios
from map_data import Provenance,import_osm_xml
from map_data.osm_xml import _haversine
ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://download.geofabrik.de/europe/united-kingdom/england/greater-manchester-260901.osm.pbf'
EXPECTED_XML_HASH='b3a883ae9b7c85072d24afeee7a1079aea00c22264516a0e1e71d49221ad27d5'
EXPECTED_ARCHIVE_HASH='b7188b22501b878fddba6e06a90bb44ce6c2d721333e0ca57e10a1a82b568807'
ITINERO_SOURCE='b8a004a831d353565572c7ba41b5a40c29d79360'


def judge(case,row):
    if row['id']!=case['id']:raise ValueError('Case alignment mismatch')
    if row['status']!='OUTPUT':return dict(case_id=case['id'],outcome='UNRESOLVED',reason=row['reason'])
    points=row['points']
    if not isinstance(points,list) or not 2<=len(points)<=20000 or any(not isinstance(p,list) or len(p)!=2 or any(type(v) not in (int,float) or not isfinite(v) for v in p) or not -90<=p[0]<=90 or not -180<=p[1]<=180 for p in points):
        return dict(case_id=case['id'],outcome='UNRESOLVED',reason='Invalid or incomplete returned geometry')
    start=_haversine(case['start'],points[0]);end=_haversine(case['end'],points[-1])
    checks=dict(start_within_5m=start<=5,end_within_5m=end<=5,nonzero_geometry=any(_haversine(a,b)>.01 for a,b in zip(points,points[1:])))
    return dict(case_id=case['id'],outcome='PASS' if all(checks.values()) else 'FAIL',scope='route output/endpoint contract only',checks=checks,start_error_m=start,end_error_m=end,returned_vertices=len(points),independent_legality='UNRESOLVED',gps_quality_tests_executed=0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');a=p.parse_args()
    if a.prepare:
        archive=json.loads((ROOT/'results/ref006-source-hashes.json').read_text())
        if archive['archive_sha256']!=EXPECTED_ARCHIVE_HASH:raise ValueError('Pinned real source archive differs; do not substitute')
        raw=(ROOT/'results/ref006-map.osm').read_bytes()
        if sha256(raw).hexdigest()!=EXPECTED_XML_HASH:raise ValueError('Real XML subset differs from pinned prior map; preserve failure, do not substitute data')
        data=import_osm_xml(raw,provenance=Provenance('public Greater Manchester test bbox','Geofabrik260901',SOURCE,'OpenStreetMap contributors; ODbL; public road data, no personal traces'))
        pairs=_scenarios(data.graph,limit=3)[:3]
        if len(pairs)!=3:raise ValueError('Required three frozen-selection cases unavailable; do not substitute cases')
        cases=[dict(id=f'REF-006-{i:03d}',start=data.coordinates[s],end=data.coordinates[t]) for i,(s,t) in enumerate(pairs,1)]
        r=dict(classification='real public map; synthetic selected GPS endpoints, not personal traces',source_url=SOURCE,source_archive_sha256=json.loads((ROOT/'results/ref006-source-hashes.json').read_text())['archive_sha256'],expected_xml_sha256=EXPECTED_XML_HASH,map_xml_sha256=sha256(raw).hexdigest(),map_pbf_sha256=sha256((ROOT/'results/ref006-map.osm.pbf').read_bytes()).hexdigest(),selection='existing _scenarios; first3, before Itinero execution; no failed case discarded',case_expectation='actual complete finite route; both exact endpoints within5m; no legal/GNSS-truth claim',cases=cases)
        (ROOT/'results/ref006-requests.json').write_text(json.dumps(r,indent=2)+'\n');return
    requests=json.loads((ROOT/'results/ref006-requests.json').read_text());actual=json.loads((ROOT/'results/ref006-itinero-output.json').read_text())
    if len(actual['cases'])!=len(requests['cases']):raise ValueError('Incomplete actual case cohort')
    r=dict(test_id='REF-006',system='Itinero',classification='real-map actual route/endpoint probe, not independently judged GPS/navigation quality',run_sha=os.environ.get('GITHUB_HEAD_SHA'),version=dict(source_sha=ITINERO_SOURCE,source_package_version='1.6.0-pre037',assembly=actual['assembly_version'],profile=actual['profile']),execution='actual_dotnet_source_build_and_route_calculation',request_manifest=requests,request_manifest_sha256=sha256((ROOT/'results/ref006-requests.json').read_bytes()).hexdigest(),cases=[judge(c,r) for c,r in zip(requests['cases'],actual['cases'])],real_GNSS_measurements=0,simulated_signal_quality_cases=0,independent_legality_cases=0,score_out_of_ten=None,rank=None)
    (ROOT/'results/ref006-itinero-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))

if __name__=='__main__':main()
