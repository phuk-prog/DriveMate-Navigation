"""Evidence-only ordinary-motorcar oracle; never called by the runtime engine.

Prospective contract: mode specificity before directional refinement within a
mode. Unimplemented one-way exceptions, conditions and contextual permissions
are unjudged. Historical MAP-001 reports remain unchanged; runtime corrections are owner-approved.
"""
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from benchmarks.map001_graph_fact_audit import ROOT, digest, tags, isolated
from benchmarks.map001_v2 import barrier, merge, related
from benchmarks.map001_v3 import FROZEN_V2_IDS
from map_data import import_osm_xml, Provenance, OSMImportError

MODES = ('motorcar', 'motor_vehicle', 'vehicle', 'access')
OPEN = {'yes', 'designated', 'permissive'}
CONTEXT = {'private', 'destination', 'delivery', 'customers', 'permit', 'agricultural', 'forestry'}
ONEWAY = {'': ('f','r'), 'no': ('f','r'), '0': ('f','r'), 'false': ('f','r'),
          'yes': ('f',), '1': ('f',), 'true': ('f',), '-1': ('r',), 'reverse': ('r',)}


def direction_access(t, forward):
    if any(k.endswith(':conditional') for k in t):
        return 'unknown'
    # Recognize unsupported car-relevant exceptions rather than mis-score them.
    if any(k in t for k in ('oneway:motorcar','oneway:motor_vehicle','oneway:vehicle')):
        return 'unknown'
    o = t.get('oneway', '').lower()
    if not o and t.get('junction') in ('roundabout', 'circular'):
        o = 'yes'
    if o not in ONEWAY:
        return 'unknown'
    if ('f' if forward else 'r') not in ONEWAY[o]:
        return 'prohibited'
    suffix = ':forward' if forward else ':backward'
    for mode in MODES:
        for key in (mode + suffix, mode):
            if key in t:
                value = t[key]
                return ('allowed' if value in OPEN else 'prohibited' if value == 'no'
                        else 'contextual' if value in CONTEXT else 'unknown')
    return 'unknown' if t.get('highway') in ('service','track') else 'allowed'


def edge_expectation(way, nodes):
    """Complete segment orientation/access evidence, or explicit unsupported reason."""
    t = tags(way)
    refs = [n.get('ref') for n in way.findall('nd')]
    if any(n not in nodes for n in refs):
        return None, 'INCOMPLETE_SOURCE'
    if len(refs) < 2:
        return None, 'INCOMPLETE_GEOMETRY'
    if any(k.endswith(':conditional') for n in refs for k in tags(nodes[n])):
        return None, 'UNKNOWN_NODE_CONDITIONAL'
    if any(direction_access(t, f) == 'unknown' for f in (True, False)):
        return None, 'UNSUPPORTED_ACCESS_OR_ONEWAY'
    o = t.get('oneway','').lower()
    if not o and t.get('junction') in ('roundabout','circular'):
        o = 'yes'
    result = {}
    for i,(a,b) in enumerate(zip(refs,refs[1:])):
        for d in ONEWAY[o]:
            start,end = (a,b) if d=='f' else (b,a)
            state = direction_access(t,d=='f')
            barriers = [barrier(tags(nodes[n])) for n in (a,b)]
            # Contextual permissions and barriers require a profile, not a bool.
            if state == 'contextual' or any(any(v in CONTEXT for v in tags(nodes[n]).values()) for n in (a,b)):
                state = 'contextual'
            else:
                state = merge(state,*barriers)
            result[f"w:{way.get('id')}:{i}:{d}"] = (f'osm:{start}',f'osm:{end}',state)
    return result,None


def edge_differences(expected, observed):
    return {'missing_edges':sorted(expected.keys()-observed.keys()),
            'extra_edges':sorted(observed.keys()-expected.keys()),
            'wrong_edges':[{'edge':k,'expected':expected[k],'observed':observed[k]}
                           for k in sorted(expected.keys() & observed.keys())
                           if expected[k] != observed[k]]}


def relation_contract(relation, ways, nodes):
    t=tags(relation)
    row={'relation':relation.get('id'),'source_tags':t,
         'source_members':[dict(m.attrib) for m in relation.findall('member')]}
    if any(k.endswith(':conditional') for k in t):
        return {**row,'verdict':'UNKNOWN_CONDITIONAL'}
    exceptions=set(t.get('except','').replace(',',';').split(';'))
    exceptions={v.strip() for v in exceptions}
    if exceptions & {'motorcar','motor_vehicle','vehicle'}:
        return {**row,'verdict':'EXEMPT_ORDINARY_MOTORCAR'}
    rule=next((t[k] for k in ('restriction:motorcar','restriction:motor_vehicle','restriction') if k in t),'')
    members=relation.findall('member')
    fr=[m.get('ref') for m in members if m.get('type')=='way' and m.get('role')=='from']
    to=[m.get('ref') for m in members if m.get('type')=='way' and m.get('role')=='to']
    via=[m.get('ref') for m in members if m.get('type')=='node' and m.get('role')=='via']
    if not (len(fr)==len(to)==len(via)==1 and len(members)==3 and rule.startswith(('no_','only_'))):
        return {**row,'verdict':'UNSUPPORTED_RELATION'}
    if any(w not in ways for w in fr+to) or via[0] not in nodes:
        return {**row,'verdict':'INCOMPLETE_SOURCE'}
    edges={}
    for wid in set(fr+to):
        part,issue=edge_expectation(ways[wid],nodes)
        if issue:return {**row,'verdict':issue}
        edges.update(part)
    incoming={k:v for k,v in edges.items() if k.split(':')[1]==fr[0] and v[1]=='osm:'+via[0]}
    leaving={k:v for k,v in edges.items() if k.split(':')[1]==to[0] and v[0]=='osm:'+via[0]}
    uncertain=any(v[2] in ('unknown','contextual') for v in list(incoming.values())+list(leaving.values()))
    available_in=[k for k,v in incoming.items() if v[2]=='allowed']
    available_out=[k for k,v in leaving.items() if v[2]=='allowed']
    return {**row,'rule':rule,'incoming':incoming,'departing':leaving,
            'verdict': 'UNKNOWN_ACCESS_CONTEXT' if uncertain else
            'NO_AVAILABLE_MOTORCAR_MOVEMENT' if not available_in or not available_out else
            'REPRESENTABLE_MOTORCAR_MOVEMENT',
            'stale_or_legally_invalid_proven':False}


def conditional_withheld(way,graph):
    from map_data.osm_xml import _conditional_restrictions
    closes=_conditional_restrictions(tags(way))
    edges=[e for k,e in graph.edges.items() if k.split(':')[1]==way.get('id')]
    exposed=[e.edge_id for e in edges if e.access=='allowed' and closes['forward' if e.edge_id.endswith(':f') else 'backward']]
    if exposed:
        return {'verdict':'FAIL','reason':'CONDITIONAL_RESTRICTION_ROUTABLE','edges':exposed}
    return {'verdict':'SAFE_WITHHELD','reason':'CONDITIONAL_WITHHELD_PER_DIRECTION'}


def audit_way(way,nodes):
    expected,issue=edge_expectation(way,nodes)
    row={'source_way':way.get('id'),'source_tags':tags(way)}
    try:
        graph=import_osm_xml(isolated(way,nodes),provenance=Provenance(
            'Manchester','archived v3','direction contract','OpenStreetMap contributors; ODbL')).graph
    except (OSMImportError,KeyError) as exc:
        conditional=any(k.endswith(':conditional') for k in tags(way)) or issue=='UNKNOWN_NODE_CONDITIONAL'
        return {**row,'verdict':'SAFE_WITHHELD' if conditional else 'NOT_JUDGED','reason':str(exc)[:160]}
    if any(k.endswith(':conditional') for k in tags(way)) or issue=='UNKNOWN_NODE_CONDITIONAL':
        # Contract v2 (TURN-001 importer): conditionals are withheld per direction,
        # not by rejecting the extract. Safe only if no possibly-closed edge is routable.
        return {**row,**conditional_withheld(way,graph)}
    if issue:return {**row,'verdict':'NOT_JUDGED','reason':issue}
    if any(v[2] in ('contextual','unknown') for v in expected.values()):
        return {**row,'verdict':'NOT_JUDGED','reason':'CONTEXT_OR_BARRIER_POLICY'}
    actual={k:(e.source,e.target,e.access) for k,e in graph.edges.items()}
    diff=edge_differences(expected,actual)
    return {**row,'verdict':'FAIL' if any(diff.values()) else 'PASS',
            'scope':'ISOLATED_WAY_DIRECTION_ACCESS_NOT_TURN_LEGALITY',
            'checks':len(expected),'differences':diff}


def main():
    manifest=json.loads((ROOT/'map001-v3-manifest.json').read_text())
    raw=(ROOT/'map001-manchester.osm').read_bytes()
    expected=next(x['source_sha256'] for x in manifest['areas'] if x['area']=='manchester')
    if digest(raw)!=expected:raise ValueError('Frozen Manchester hash mismatch')
    root=ET.fromstring(raw)
    ways={w.get('id'):w for w in root.findall('way')}
    nodes={n.get('id'):n for n in root.findall('node')}
    cases=[audit_way(ways[wid],nodes) for wid in FROZEN_V2_IDS['manchester']]
    rels={r.get('id'):r for wid in ('155729945','246124643') for r in related(wid,root.findall('relation'))}
    report={'trial':'MAP-001-DIRECTION-CONTRACT-1','source_sha256':expected,
            'oracle_sha256':digest(Path(__file__).read_bytes()),
            'truth':'PROVISIONAL_OSM_SOURCE_NOT_ROAD_LAW',
            'runtime_changed':digest(Path('map_data/osm_xml.py').read_bytes()) !=
                '927e84b8226f23249c18de40a9e78998b2e6fa2d113f59cf3c121b53e43bac16',
            'importer_sha256':digest(Path('map_data/osm_xml.py').read_bytes()),
            'cases':cases,'counts':dict(Counter(x['verdict'] for x in cases)),
            'edge_checks':sum(x.get('checks',0) for x in cases),
            'relations':[relation_contract(r,ways,nodes) for r in rels.values()],
            'turn_pair_rank':None,'valhalla_complete_edge_and_turn_contract':'UNSUPPORTED'}
    (ROOT/'map001-direction-contract.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('cases','relations')},indent=2))
    # An evidence-gathering job may succeed while documenting known DMN failures.
    # Acceptance is explicit in counts; no assertion makes the known defect pass.

if __name__=='__main__':main()
