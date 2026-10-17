"""REF-007 actual Routino CLI on frozen public-map endpoints, no personal GPS.

This is an executable routing/endpoint probe, not independent road-law truth or
GPS quality validation. External CLI failures are unresolved, never mocked passes.
"""
import argparse
from hashlib import sha256
import json
from math import isfinite
import os
from pathlib import Path
import shutil
import subprocess
from time import perf_counter_ns
import xml.etree.ElementTree as ET
from benchmarks.itinero_public_probe import EXPECTED_ARCHIVE_HASH, EXPECTED_XML_HASH, judge

ROOT=Path(__file__).resolve().parents[1]
REQUEST_HASH='b4348997ca109fb873c265179f1edb7d4aa0772bad26b5198ad207deea02f87d'


def parse_gpx(raw):
    root=ET.fromstring(raw)
    segments=[x for x in root.iter() if x.tag.split('}')[-1]=='trkseg']
    if len(segments)!=1:
        raise ValueError('Exactly one continuous GPX track segment required')
    points=[]
    for el in segments[0]:
        if el.tag.split('}')[-1]!='trkpt':continue
        lat,lon=float(el.attrib['lat']),float(el.attrib['lon'])
        if not isfinite(lat) or not isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180:
            raise ValueError('Invalid GPX coordinate')
        points.append([lat,lon])
    if not 2<=len(points)<=20000:
        raise ValueError('Incomplete or excessive returned route')
    return points


def binary(name):
    result=shutil.which('routino-'+name) or shutil.which(name)
    if not result:raise RuntimeError('Routino executable unavailable: '+name)
    return str(Path(result).resolve())


def execute(command, cwd, timeout):
    begin=perf_counter_ns()
    r=subprocess.run(command,cwd=cwd,text=True,capture_output=True,timeout=timeout)
    elapsed=perf_counter_ns()-begin
    return dict(command=command,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,wall_ns=elapsed)


def main():
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');a=p.parse_args()
    area=ROOT/'results';area.mkdir(exist_ok=True)
    frozen=json.loads((ROOT/'references/ref006-itinero-confirmation-20261016.json').read_text())['report']['request_manifest']
    request_bytes=(json.dumps(frozen,indent=2)+'\n').encode()
    if sha256(request_bytes).hexdigest()!=REQUEST_HASH:raise ValueError('Frozen request bytes changed')
    if sha256((area/'ref007-source.osm.pbf').read_bytes()).hexdigest()!=EXPECTED_ARCHIVE_HASH:raise ValueError('Pinned source archive mismatch')
    if sha256((area/'ref007-map.osm').read_bytes()).hexdigest()!=EXPECTED_XML_HASH:raise ValueError('Pinned XML mismatch')
    if sha256((area/'ref007-map.osm.pbf').read_bytes()).hexdigest()!=frozen['map_pbf_sha256']:raise ValueError('Pinned PBF subset mismatch')
    request_path=area/'ref007-requests.json'
    if a.prepare:
        request_path.write_bytes(request_bytes);print(request_bytes.decode());return
    if request_path.read_bytes()!=request_bytes:raise ValueError('Requests changed after freeze')
    router=binary('router');splitter=binary('planetsplitter')
    metadata=json.loads((area/'ref007-package-metadata.json').read_text())
    configs={x:str(Path('/usr/share/routino')/x) for x in ('profiles.xml','tagging.xml','translations.xml')}
    for path in configs.values():
        if not Path(path).is_file():raise RuntimeError('Packaged configuration unavailable: '+path)
    hashes={str(p):sha256(Path(p).read_bytes()).hexdigest() for p in [router,splitter,*configs.values()]}
    db=area/'ref007-db';db.mkdir(exist_ok=True)
    prep=execute([splitter,'--dir='+str(db),'--tagging='+configs['tagging.xml'],str(area/'ref007-map.osm')],db,180)
    (area/'ref007-preparation.json').write_text(json.dumps(prep,indent=2)+'\n')
    print(json.dumps({'ref007_preparation':prep},indent=2))
    if prep['returncode']!=0:raise RuntimeError('Actual Routino import failed; retain evidence')
    rows=[];raw_outputs=[]
    for c in frozen['cases']:
        work=area/('ref007-'+c['id']);work.mkdir(exist_ok=True)
        command=[router,'--dir='+str(db),'--profiles='+configs['profiles.xml'],'--translations='+configs['translations.xml'],
                 '--transport=motorcar','--quickest','--output-gpx-track',
                 '--lat1='+str(c['start'][0]),'--lon1='+str(c['start'][1]),
                 '--lat2='+str(c['end'][0]),'--lon2='+str(c['end'][1])]
        try:
            output=execute(command,work,60)
            files=sorted(work.glob('*track.gpx'))
            output['gpx_files']=[f.name for f in files]
            if output['returncode']!=0 or len(files)!=1:
                actual=dict(id=c['id'],status='UNRESOLVED',reason='CLI failure or missing unique GPX output')
            else:
                raw=files[0].read_bytes();output['gpx_sha256']=sha256(raw).hexdigest();output['gpx_utf8_hex']=raw.hex()
                actual=dict(id=c['id'],status='OUTPUT',points=parse_gpx(raw))
        except (ValueError,ET.ParseError,KeyError,subprocess.TimeoutExpired) as exc:
            output=dict(command=command,error=type(exc).__name__+': '+str(exc));actual=dict(id=c['id'],status='UNRESOLVED',reason=output['error'])
        raw_outputs.append(dict(case_id=c['id'],**output))
        rows.append(judge(c,actual))
    report=dict(test_id='REF-007',system='Routino',run_sha=os.environ.get('GITHUB_HEAD_SHA'),
                classification='actual real-map route/endpoint output probe; no independent road-law/GPS-quality verdict',
                execution='actual_packaged_cli_import_and_route_calculation',version=metadata,
                configuration=dict(transport='motorcar',objective='quickest',configuration_and_executable_sha256=hashes),
                request_manifest=frozen,request_manifest_sha256=REQUEST_HASH,cases=rows,
                preparation=prep,raw_outputs=raw_outputs,actual_route_calculations=len(rows),
                passed=sum(x['outcome']=='PASS' for x in rows),total=len(rows),
                score_out_of_ten=None,rank=None,independent_legality_cases=0,gps_quality_cases=0)
    (area/'ref007-routino-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if any(x['outcome']!='PASS' for x in rows):
        raise SystemExit('Nonpassing actual reference observations retained; do not discard cases')

if __name__=='__main__':main()
