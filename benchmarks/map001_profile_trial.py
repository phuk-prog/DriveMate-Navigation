"""Real frozen-way profile execution; isolated access test, not route quality.

Valhalla auto is unchanged. Per-way private authorization and explicitly
unqualified through-purpose are not expressible via this request contract.
Those comparisons stay unsupported even when a route happens to be returned.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter_ns
from urllib.error import HTTPError
from urllib.request import Request
import xml.etree.ElementTree as ET
from benchmarks.map001_graph_fact_audit import ROOT, digest, isolated, tags
from benchmarks.map001_access_review import decode_shape
from benchmarks.valhalla_live_reference import _OPENER, ROUTE_URL
from engine import shortest_route, RouteNotFound
from map_data import JourneyAccessContext, Provenance, import_osm_xml

CONTEXT_WAYS=('4816180','4857542','553071025','553071026','553071028','4721486','8777654','27255314')
BINARY_WAYS=('155729945','115559329','548694371','35277147')
IDS=CONTEXT_WAYS+BINARY_WAYS
DIR=ROOT/'map001-profiles'
PROV=Provenance('Manchester','archived v3','isolated real-way profile test',
                'OpenStreetMap contributors; ODbL')


def prepare():
    raw=(ROOT/'map001-manchester.osm').read_bytes()
    m=json.loads((ROOT/'map001-v3-manifest.json').read_text())
    expected=next(x['source_sha256'] for x in m['areas'] if x['area']=='manchester')
    if digest(raw)!=expected:raise ValueError('Frozen Manchester source mismatch')
    root=ET.fromstring(raw);ways={x.get('id'):x for x in root.findall('way')};nodes={x.get('id'):x for x in root.findall('node')}
    DIR.mkdir(exist_ok=True,parents=True);cases=[]
    for wid in IDS:
        way=ways[wid];case_raw=isolated(way,nodes)
        (DIR/(wid+'.osm')).write_bytes(case_raw)
        refs=[n.get('ref') for n in way.findall('nd')]
        if refs[0]==refs[-1]:raise ValueError('Profile endpoints must differ')
        if wid in BINARY_WAYS and wid!='35277147' and tags(way).get('vehicle:backward')!='no':
            raise ValueError('Frozen hard-direction control changed')
        if wid=='35277147' and tags(way).get('oneway','') not in ('','no','0','false'):
            raise ValueError('Public two-way control changed')
        cases.append({'way':wid,'input_sha256':digest(case_raw),'source_access':tags(way),
                      'from_node':'osm:'+refs[0],'to_node':'osm:'+refs[-1]})
    manifest={'trial':'MAP-001-PROFILE-1','source_sha256':expected,'cases':cases,
              'attribution':'OpenStreetMap contributors; ODbL',
              'scope':'ISOLATED_WAY_ACCESS_NOT_NETWORK_ROUTE_QUALITY_OR_UK_LEGALITY'}
    (DIR/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def profiles(wid,t):
    if wid in BINARY_WAYS:
        return [('ORDINARY_FORWARD',True,'allowed',True),
                ('ORDINARY_REVERSE',False,'prohibited' if wid!='35277147' else 'allowed',True)]
    value=t.get('motorcar',t.get('motor_vehicle',t.get('vehicle',t.get('access'))))
    return [('ORDINARY_NO_ASSERTED_PURPOSE',True,'unknown',False),
            ('QUALIFYING_DESTINATION',True,'allowed' if value=='destination' else 'unknown',value=='destination'),
            ('EXPLICIT_PRIVATE_PERMISSION',True,'allowed' if value=='private' else 'unknown',False)]


def request_body(start,end):
    return {'locations':[{'lat':p[0],'lon':p[1],'minimum_reachability':0,'radius':10}
                         for p in (start,end)],
            'costing':'auto','costing_options':{'auto':{
                'ignore_access':False,'ignore_restrictions':False,'ignore_oneways':False}},
            'directions_options':{'units':'kilometers'}}


def observe_valhalla(payload):
    body=json.dumps(payload,separators=(',',':')).encode()
    if len(body)>2000:raise ValueError('Profile request too large')
    req=Request(ROUTE_URL,data=body,headers={'Content-Type':'application/json'},method='POST')
    began=perf_counter_ns();status=200
    try:
        with _OPENER.open(req,timeout=15) as r:raw=r.read(200001)
    except HTTPError as e:
        status=e.code;raw=e.read(200001)
    elapsed=(perf_counter_ns()-began)/1e6
    if len(raw)>200000:raise ValueError('Profile response too large')
    data=json.loads(raw)
    if not isinstance(data,dict):raise ValueError('Profile response schema')
    if status!=200:
        result='NO_ROUTE' if data.get('error_code') in {171,442} else 'NOT_JUDGED_HTTP_ERROR'
        return {'request':payload,'http_status':status,'result':result,'response':data,
                'http_request_ms':elapsed}
    trip=data.get('trip',{});legs=trip.get('legs',[])
    shape=legs[0].get('shape') if len(legs)==1 else None
    try:points=decode_shape(shape)
    except (ValueError,TypeError):points=[]
    wanted=[(x['lat'],x['lon']) for x in payload['locations']]
    aligned=bool(points and all(max(abs(p[k]-q[k]) for k in (0,1))<=0.00003
                               for p,q in zip((points[0],points[-1]),wanted)))
    nonzero=trip.get('summary',{}).get('length',0)>0 and points and points[0]!=points[-1]
    return {'request':payload,'http_status':status,
            'result':'ROUTE' if aligned and nonzero else 'NOT_JUDGED_ENDPOINT_CORRELATION',
            'endpoint_alignment_verified':aligned,'response':data,'http_request_ms':elapsed}


def probe(wid):
    manifest=json.loads((DIR/'manifest.json').read_text())
    spec=next(x for x in manifest['cases'] if x['way']==wid)
    raw=(DIR/(wid+'.osm')).read_bytes()
    if digest(raw)!=spec['input_sha256']:raise ValueError('Profile input changed')
    base=import_osm_xml(raw,provenance=PROV);s=spec['from_node'];d=spec['to_node']
    observations={};rows=[]
    for name,forward,expected,equivalent in profiles(wid,spec['source_access']):
        start,end=(s,d) if forward else (d,s)
        if name=='QUALIFYING_DESTINATION':
            ctx=JourneyAccessContext(digest(raw),destination_node=end,destination_way_ids=frozenset({wid}))
        elif name=='EXPLICIT_PRIVATE_PERMISSION':
            ctx=JourneyAccessContext(digest(raw),authorized_way_ids=frozenset({wid}))
        else:ctx=None
        began=perf_counter_ns();m=import_osm_xml(raw,provenance=PROV,access_context=ctx)
        ids=[e for e in m.graph.edges.values() if e.edge_id.endswith(':f' if forward else ':r')]
        states={e.access for e in ids}
        observed=next(iter(states)) if len(states)==1 else 'unknown'
        try:
            route=shortest_route(m.graph,start,end);dmn_route=bool(route.edge_ids)
        except RouteNotFound:dmn_route=False
        elapsed=(perf_counter_ns()-began)/1e6
        key='forward' if forward else 'reverse'
        if key not in observations:
            observations[key]=observe_valhalla(request_body(base.coordinates[start],base.coordinates[end]))
        val=observations[key]
        policy='PASS' if observed==expected and dmn_route==(expected=='allowed') else 'FAIL'
        counterpart=('UNSUPPORTED_PROFILE_MAPPING' if not equivalent else
                     'NOT_JUDGED' if val['result'].startswith('NOT_JUDGED') else
                     'PASS' if (val['result']=='ROUTE')==(expected=='allowed') else 'FAIL')
        rows.append({'source_way':wid,'profile':name,'direction':key,'expected_access':expected,
                     'dmn_access':observed,'dmn_route_available':dmn_route,'dmn_policy_verdict':policy,
                     'dmn_import_and_route_ms':elapsed,'valhalla_verdict':counterpart,
                     'valhalla_observation':key,'equivalent_profile':equivalent,
                     'permission_or_purpose_assertion':'HYPOTHETICAL_TEST_INPUT_NOT_REAL_ENTITLEMENT',
                     'road_legality':'NOT_INDEPENDENTLY_JUDGED'})
    report={'way':wid,'source_sha256':manifest['source_sha256'],
            'same_engine_input_xml_sha256':digest(raw),'cases':rows,
            'valhalla_fresh_observations':observations,
            'measurement_scopes_not_speed_comparable':True}
    (DIR/(wid+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'way':wid,'dmn':dict(Counter(x['dmn_policy_verdict'] for x in rows)),
                      'valhalla':dict(Counter(x['valhalla_verdict'] for x in rows))}),flush=True)


def score():
    manifest=json.loads((DIR/'manifest.json').read_text());rows=[]
    for wid in IDS:
        r=json.loads((DIR/(wid+'.json')).read_text())
        spec=next(x for x in manifest['cases'] if x['way']==wid)
        if (r['way']!=wid or r['source_sha256']!=manifest['source_sha256'] or
                r['same_engine_input_xml_sha256']!=spec['input_sha256']):
            raise ValueError('Profile source/cohort mismatch')
        expected_profiles=[x[0] for x in profiles(wid,spec['source_access'])]
        if ([x['profile'] for x in r['cases']]!=expected_profiles or
                any(x['source_way']!=wid for x in r['cases'])):
            raise ValueError('Profile cases changed or duplicated')
        rows.extend(r['cases'])
    if len(rows)!=32:raise ValueError('Incomplete profile cohort')
    common=[x for x in rows if x['equivalent_profile'] and x['valhalla_verdict'] in {'PASS','FAIL'}]
    rank=[{'engine':e,'pass':sum(x[k]=='PASS' for x in common),
           'fail':sum(x[k]=='FAIL' for x in common),'total':len(common)}
          for e,k in [('DMN ★','dmn_policy_verdict'),('Valhalla 3.9.1','valhalla_verdict')]]
    report={'trial':'MAP-001-PROFILE-1','source_sha256':manifest['source_sha256'],
            'case_total':len(rows),'way_total':len(IDS),'cases':rows,
            'dmn_policy_counts':dict(Counter(x['dmn_policy_verdict'] for x in rows)),
            'dmn_access_counts':dict(Counter(x['dmn_access'] for x in rows)),
            'valhalla_counts':dict(Counter(x['valhalla_verdict'] for x in rows)),
            'complete_expected_equivalent_profile_cohort':10,
            'actually_comparable_profile_checks':len(common),
            'partial_profile_ranking':sorted(rank,key=lambda x:-x['pass']),
            'full_profile_ranking':None,'runtime_changed':False,
            'truth':'FROZEN_SOURCE_AND_HYPOTHETICAL_CONTEXT_NOT_VERIFIED_UK_LEGALITY'}
    (DIR/'scorecard.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
    if report['dmn_policy_counts'].get('FAIL'):raise SystemExit('DMN profile conformance failure')


def main():
    p=argparse.ArgumentParser();p.add_argument('operation',choices=('prepare','probe','score'));p.add_argument('--way',choices=IDS)
    a=p.parse_args()
    if a.operation=='prepare':prepare()
    elif a.operation=='probe':
        if not a.way:p.error('--way required')
        probe(a.way)
    else:score()

if __name__=='__main__':main()
