"""Frozen-source contextual policy controls, not verified authorization/road law.

Competitor profile equivalence for permission scenarios is not established.
Do not mix these controls into the common binary access ranking.
"""
from collections import Counter
import json
import xml.etree.ElementTree as ET
from benchmarks.map001_graph_fact_audit import ROOT, digest, isolated, tags
from benchmarks.map001_v3 import FROZEN_V2_IDS
from benchmarks.map001_access_review import review_way, access_basis
from map_data import JourneyAccessContext, Provenance, import_osm_xml

P=Provenance('Manchester','frozen v3','contextual access policy controls',
             'OpenStreetMap contributors; ODbL')


def context_cases(way,nodes):
    raw=isolated(way,nodes);source_hash=digest(raw);wid=way.get('id')
    basis,_=access_basis(tags(way))
    default=import_osm_xml(raw,provenance=P)
    states=Counter(e.access for e in default.graph.edges.values())
    rows=[{'source_way':wid,'profile':'NO_PERMISSION_OR_PURPOSE_ASSERTED',
           'import_input_sha256':source_hash,'counts':dict(states),
           'policy_check':'PASS' if states and set(states)=={'unknown'} else 'FAIL',
           'road_legality_verdict':'NOT_JUDGED','valhalla_profile_verdict':'UNSUPPORTED'}]
    if basis=='JOURNEY_PURPOSE_REQUIRED':
        target='osm:'+way.findall('nd')[-1].get('ref')
        ctx=JourneyAccessContext(source_hash,destination_node=target,
                                 destination_way_ids=frozenset({wid}))
        expected='allowed';profile='DECLARED_QUALIFYING_DESTINATION_ON_THIS_WAY'
    else:
        ctx=JourneyAccessContext(source_hash,authorized_way_ids=frozenset({wid}))
        expected='allowed' if basis=='AUTHORIZATION_REQUIRED' else 'unknown'
        profile='DECLARED_WAY_PERMISSION' if expected=='allowed' else 'PERMISSION_DOES_NOT_INVENT_MISSING_SOURCE_ACCESS'
    view=import_osm_xml(raw,provenance=P,access_context=ctx)
    granted=Counter(e.access for e in view.graph.edges.values())
    rows.append({'source_way':wid,'profile':profile,'import_input_sha256':source_hash,
                 'counts':dict(granted),'policy_check':'PASS' if granted and set(granted)=={expected} else 'FAIL',
                 'context_evidence':'HYPOTHETICAL_ASSERTION_NOT_PROOF_OF_REAL_PERMISSION',
                 'road_legality_verdict':'NOT_JUDGED','valhalla_profile_verdict':'UNSUPPORTED',
                 'base_map_unchanged':all(e.access=='unknown' for e in default.graph.edges.values())})
    return rows


def main():
    raw=(ROOT/'map001-manchester.osm').read_bytes()
    manifest=json.loads((ROOT/'map001-v3-manifest.json').read_text())
    expected=next(x['source_sha256'] for x in manifest['areas'] if x['area']=='manchester')
    if digest(raw)!=expected:raise ValueError('Frozen Manchester bytes changed')
    root=ET.fromstring(raw);ways={x.get('id'):x for x in root.findall('way')};nodes={x.get('id'):x for x in root.findall('node')}
    rows=[]
    for wid in FROZEN_V2_IDS['manchester']:
        if review_way(ways[wid],nodes) is not None: rows.extend(context_cases(ways[wid],nodes))
    totals=Counter(x['policy_check'] for x in rows)
    report={'trial':'MAP-001-CONTEXTUAL-ACCESS-1','source_sha256':expected,
            'importer_sha256':digest(__import__('pathlib').Path('map_data/osm_xml.py').read_bytes()),
            'scope':'POLICY_CONTROLS_ON_FROZEN_WAYS_NOT_UK_LEGALITY_PROOF',
            'permission_assertions_are_hypothetical':True,'cases':rows,'policy_counts':dict(totals),
            'scenario_total':len(rows),'way_total':len({x['source_way'] for x in rows}),
            'valhalla_permission_profile_equivalence':'UNSUPPORTED_NOT_SCORED_AS_FAILURE',
            'ranking':None}
    (ROOT/'map001-contextual-access.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('trial','policy_counts','scenario_total','way_total')},indent=2))
    if totals['FAIL'] or len(rows)!=16:raise SystemExit('Contextual policy contract failed')

if __name__=='__main__':main()
