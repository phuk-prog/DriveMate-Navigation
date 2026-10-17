"""OFFLINE-001 synthetic map integrity/activation, actual parsing and routing."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
from engine import RouteNotFound
from map_data.offline import OfflineMapStore,PackageValidationError,NoActiveMap,CoverageUnavailable

ROOT=Path(__file__).resolve().parents[1]
ORACLE=ROOT/'benchmarks/fixtures/synthetic-offline-001.json'


def inputs():
    f=json.loads(ORACLE.read_text());maps={k:(ORACLE.parent/p).read_bytes() for k,p in f['map_files'].items()}
    def manifest(raw,name):
        return dict(schema_version=1,format='dmn-osm-xml-v1',byte_length=len(raw),sha256=sha256(raw).hexdigest(),required_nodes=f['required_nodes'][:],provenance=dict(region='invented OFFLINE-001 '+name,snapshot='synthetic-v1',source='analytical fixture',attribution='Synthetic OSM format; no OpenStreetMap contributor road data used'))
    variants={k:(v,manifest(v,k)) for k,v in maps.items()}
    for name in ('checksum','truncated','length','schema-version','format','provenance','missing-anchor'):
        raw,m=deepcopy(variants['A'])
        if name=='checksum':m['sha256']='0'*64
        elif name=='truncated':raw=raw[:-30]
        elif name=='length':m['byte_length']+=1
        elif name=='schema-version':m['schema_version']=2
        elif name=='format':m['format']='unknown'
        elif name=='provenance':m['provenance'].pop('attribution')
        elif name=='missing-anchor':m['required_nodes']=['osm:1','osm:9999']
        variants[name]=(raw,m)
    for name,raw in [('malformed',b'<osm><way'),('conditional',maps['A'].replace(b'<tag k="highway"',b'<tag k="access:conditional" v="no @ (Mo)"/><tag k="highway"',1)),('oversize',b'x'*(f['max_payload_bytes']+1))]:
        variants[name]=(raw,manifest(raw,name))
    return f,maps,variants


def network_state():
    try:
        current=os.readlink('/proc/self/ns/net');initial=os.readlink('/proc/1/ns/net')
        defaults=[line for line in Path('/proc/net/route').read_text().splitlines()[1:] if line.split()[1]=='00000000']
        ipv6=[line for line in Path('/proc/net/ipv6_route').read_text().splitlines() if line.split()[0]=='0'*32 and line.split()[1]=='00' and line.split()[-1]!='lo']
        return dict(namespace=current,initial_namespace=initial,separate_namespace=current!=initial,ipv4_default_routes=len(defaults),ipv6_nonloopback_default_routes=len(ipv6),isolated=current!=initial and not defaults and not ipv6)
    except (OSError,IndexError):return dict(isolated=False,reason='Linux namespace/route evidence unavailable')


def run_dmn():
    f,maps,variants=inputs();rows=[];requests=calculations=0
    hashes={k:sha256(v).hexdigest() for k,v in maps.items()}
    def label(digest):return next((k for k,v in hashes.items() if v==digest),'UNKNOWN') if digest else 'NONE'
    for c in f['cases']:
        # frozen OFFLINE-001 contract: the original strict package rule (conditional tags refused)
        store=OfflineMapStore(max_payload_bytes=f['max_payload_bytes'],allow_conditional=False);events=[]
        for i,e in enumerate(c['events']):
            checks={};row=dict(event=i,action=e['action'])
            if e['action']=='activate':
                raw,m=deepcopy(variants[e['variant']])
                try:store.activate(raw,m);status='ACTIVE';reason=None
                except PackageValidationError as exc:status='REJECTED';reason=str(exc)
                active=label(store.info.sha256 if store.info else None)
                checks.update(expected_status=status==e['expect_status'],expected_active_map=active==e['expect_active'])
                row.update(actual_status=status,expected_status=e['expect_status'],actual_active=active,rejection_reason=reason)
            elif e['action']=='route':
                requests+=1
                try:
                    r=store.route(e['source'],e['target']);calculations+=1;status='ROUTE'
                    checks['exact_declared_edges']=list(r.route.edge_ids)==e.get('expect_edges')
                    checks['route_bound_to_active_snapshot']=r.package_sha256==store.info.sha256
                    row.update(returned_edges=r.route.edge_ids,package_sha256=r.package_sha256,length_m=r.route.length_m)
                except NoActiveMap:status='NO_ACTIVE'
                except CoverageUnavailable:status='NO_COVERAGE'
                except RouteNotFound:status='NO_ROUTE';calculations+=1
                checks['expected_status']=status==e['expect_status']
                row.update(actual_status=status,expected_status=e['expect_status'])
            else:raise ValueError('Unknown action')
            row.update(checks=checks,passed=all(checks.values()));events.append(row)
        rows.append(dict(case_id=c['id'],outcome='PASS' if all(e['passed'] for e in events) else 'FAIL',events=events))
    return dict(test_id='OFFLINE-001',system='DMN',version='repository research OfflineMapStore/import_osm_xml/shortest_route',execution='actual_local_python_import_and_routes',classification='synthetic analytical package conformance; not real road truth or Android/native readiness',configuration=dict(max_payload_bytes=f['max_payload_bytes'],manifest_schema=1,format='dmn-osm-xml-v1',trusted_manifest_required=True,persistent_disk_install=False),map_sha256=hashes,oracle_sha256=sha256(ORACLE.read_bytes()).hexdigest(),component_sha256=sha256((ROOT/'map_data/offline.py').read_bytes()).hexdigest(),harness_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),input_variant_sha256={k:dict(payload=sha256(v[0]).hexdigest(),manifest=sha256(json.dumps(v[1],sort_keys=True,separators=(',',':')).encode()).hexdigest()) for k,v in variants.items()},run_sha=os.environ.get('GITHUB_HEAD_SHA') or os.environ.get('GITHUB_SHA'),network=network_state(),actual_map_store_route_calls=requests,actual_core_route_calculations=calculations,external_engine_executions=0,android_device_tests=0,cases=rows)


def coverage(report):
    f,maps,_=inputs();ids=[c['id'] for c in f['cases']]
    if (report['test_id']!='OFFLINE-001' or report['system']!='DMN' or report['execution']!='actual_local_python_import_and_routes'
            or report['oracle_sha256']!=sha256(ORACLE.read_bytes()).hexdigest() or report['map_sha256']!={k:sha256(v).hexdigest() for k,v in maps.items()}
            or [c['case_id'] for c in report['cases']]!=ids or any(c['outcome'] not in ('PASS','FAIL') for c in report['cases'])):raise ValueError('Incomplete or nonmatching cohort')
    roster=['DMN']+[x['name'] for x in json.loads((ROOT/'config/dmn-engine-first-programme.json').read_text())['reference_families']]
    rows=[]
    for name in roster:
        if name=='DMN':
            passed=sum(c['outcome']=='PASS' for c in report['cases'])
            isolated=report.get('network',{}).get('isolated') is True
            rows.append(dict(system=name,rank=1 if isolated else None,score_out_of_ten=10*passed/len(ids) if isolated else None,passed=passed,failed=len(ids)-passed,score_reason='Required Linux network isolation demonstrated' if isolated else 'Unranked: required isolated execution not demonstrated',cases=report['cases']));continue
        unsupported=name in ('OSRM','Valhalla','GraphHopper','openrouteservice','BRouter')
        reason=('Integrated static directions endpoint does not expose DMN package schema, transactional map activation or exact node-ID coverage errors' if unsupported else 'Executable native/app package lifecycle harness not implemented' if name in ('OsmAnd','Organic Maps') else 'No established permitted automated offline replay interface' if name=='Waze' else 'No configured permitted access and equivalent offline package harness; paid calls unauthorized')
        rows.append(dict(system=name,rank=None,score_out_of_ten=None,passed=0,failed=0,cases=[dict(case_id=i,outcome='UNSUPPORTED' if unsupported else 'NOT_RUN',reason=reason) for i in ids]))
    return dict(test_id='OFFLINE-001',formula='10 * passes / 18; unavailable/incomplete cohorts unranked',scope='DMN package conformance only; not a comparative offline-engine ranking',rows=rows)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--require-isolated-network',action='store_true');a=p.parse_args()
    if not a.output.resolve().is_relative_to((ROOT/'results').resolve()):raise ValueError('Output outside results')
    r=run_dmn();result=dict(report=r,coverage=coverage(r))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if a.require_isolated_network and not r['network']['isolated']:raise SystemExit('Required actual network isolation unavailable; not passed')
    if any(c['outcome']!='PASS' for c in r['cases']):raise SystemExit('OFFLINE-001 failed; preserve evidence')

if __name__=='__main__':main()
