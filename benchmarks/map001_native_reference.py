"""Read-only native Valhalla graph comparison, frozen Manchester source.

Compares ordinary-car access on source-identical directed segments. Turn masks
are exposed as structural evidence, not a complete AutoCost legality evaluator.
"""
from collections import Counter
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from benchmarks.map001_graph_fact_audit import ROOT, digest, tags
from benchmarks.map001_direction_contract import audit_way, edge_expectation
from benchmarks.map001_v3 import FROZEN_V2_IDS


def read_native(path):
    raw=Path(path).read_bytes()
    if len(raw)>20_000_000: raise ValueError('Native output exceeds bound')
    rows=[json.loads(x) for x in raw.splitlines() if x.strip()]
    if not rows or rows[-1].get('kind')!='complete': raise ValueError('Native enumeration incomplete')
    edges=rows[:-1]; footer=rows[-1]
    if len(edges)!=footer['directed_edges'] or any(x.get('kind')!='edge' for x in edges):
        raise ValueError('Native enumeration count/schema mismatch')
    if len({x['graph_id'] for x in edges})!=len(edges): raise ValueError('Duplicate native edge')
    return edges,footer,digest(raw)


def align_edge(edge, way, nodes):
    """Expand one native edge into source segments only on monotonic geometry."""
    refs=[n.get('ref') for n in way.findall('nd')]
    coords=[(float(nodes[n].get('lat')),float(nodes[n].get('lon'))) for n in refs]
    shape=edge.get('shape',[])
    if len(shape)<2 or type(edge.get('car_access')) is not bool: return None
    indices=[]
    for point in shape:
        matches=[i for i,c in enumerate(coords) if max(abs(point[k]-c[k]) for k in (0,1))<=0.000002]
        if len(matches)!=1:return None
        indices.append(matches[0])
    if indices[0]==indices[-1]:return None
    forward=indices[0]<indices[-1]
    # No skips/backtracking: do not attribute a native shortcut to all OSM legs.
    if any(b-a != (1 if forward else -1) for a,b in zip(indices,indices[1:])):return None
    return [f'w:{way.get("id")}:{min(a,b)}:{"f" if forward else "r"}'
            for a,b in zip(indices,indices[1:])]


def compare_way(way,nodes,edges):
    wid=way.get('id'); expected,issue=edge_expectation(way,nodes)
    dmn=audit_way(way,nodes)
    result={'source_way':wid,'dmn_verdict':dmn['verdict'],'dmn_details':dmn,
            'scope':'DIRECTED_SOURCE_SEGMENT_CAR_ACCESS_ONLY'}
    if issue or any(x[2] in ('contextual','unknown') for x in (expected or {}).values()):
        return {**result,'valhalla_verdict':'NOT_JUDGED','reason':issue or 'CONTEXTUAL_PERMISSION',
                'equivalent_scored_cohort':False}
    observed={}; unsupported=[]
    for edge in edges:
        if str(edge['way_id'])!=wid: continue
        mapped=align_edge(edge,way,nodes)
        if mapped is None:
            unsupported.append(edge['graph_id']);continue
        for eid in mapped:
            observed.setdefault(eid,[]).append({'car_access':edge['car_access'],'graph_id':edge['graph_id']})
    wrong=[];missing=[];conflicting=[]
    for eid,(_,_,state) in expected.items():
        values={x['car_access'] for x in observed.get(eid,[])}
        if not values:missing.append(eid)
        elif len(values)!=1:conflicting.append(eid)
        elif values!={state=='allowed'}:wrong.append({'edge':eid,'expected':state,'observations':observed[eid]})
    # Additional native directions can exist with car_access=false on one-way ways.
    extra_allowed=[eid for eid,rows in observed.items() if eid not in expected and any(x['car_access'] for x in rows)]
    verdict=('FAIL' if wrong or extra_allowed else 'UNSUPPORTED' if missing or unsupported or conflicting else 'PASS')
    return {**result,'valhalla_verdict':verdict,'expected_checks':len(expected),
            'missing_segment_observations':missing,'unmapped_native_edges':unsupported,
            'conflicting_observations':conflicting,'wrong_access':wrong,
            'extra_car_allowed_directions':extra_allowed,'observed':observed,
            'equivalent_scored_cohort':not(missing or unsupported or conflicting)}


def pair_observations(edges, ways, nodes, relations):
    # Source relation identity and native mask mechanics only; no route-policy
    # assumptions about generic U-turn pruning, time or destination entitlement.
    rows=[]
    bystart={}
    for e in edges:bystart.setdefault(e['start_node'],[]).append(e)
    for rel in relations:
        if rel.get('id') not in {'7844440','7844441','7844443','7876327'}:continue
        members=rel.findall('member')
        fr=next(m.get('ref') for m in members if m.get('role')=='from')
        to=next(m.get('ref') for m in members if m.get('role')=='to')
        via=next(m.get('ref') for m in members if m.get('role')=='via')
        point=(float(nodes[via].get('lat')),float(nodes[via].get('lon')))
        pairs=[]
        for a in edges:
            if str(a['way_id'])!=fr or not a.get('shape'):continue
            if max(abs(a['shape'][-1][k]-point[k]) for k in (0,1))>0.000002:continue
            for b in bystart.get(a['end_node'],[]):
                if str(b['way_id'])!=to:continue
                mask=a['restriction_mask']; index=b['local_index']
                pairs.append({'arrival_graph_id':a['graph_id'],'departure_graph_id':b['graph_id'],
                    'via_graph_node':a['end_node'],'arrival_car_access':a['car_access'],
                    'departure_car_access':b['car_access'],'arrival_mask':mask,
                    'departure_local_index':index,
                    'explicit_mask_prohibits':bool(mask & (1<<index)) if 0<=index<8 else None,
                    'complex_or_access_context':bool(a['complex'] or b['complex'] or
                        a['start_restriction'] or a['end_restriction'] or
                        b['start_restriction'] or b['end_restriction'] or
                        a['access_restriction'] or b['access_restriction']),
                    'full_turn_legality':'UNSUPPORTED_AUTOCOST_CONTEXT_NOT_EVALUATED'})
        rows.append({'source_relation':rel.get('id'),'source_rule':tags(rel).get('restriction'),
                     'source_via_node':via,'native_pairs':pairs,'pairs_total':len(pairs)})
    return rows


def main():
    raw=(ROOT/'map001-manchester.osm').read_bytes()
    manifest=json.loads((ROOT/'map001-v3-manifest.json').read_text())
    expected=next(x['source_sha256'] for x in manifest['areas'] if x['area']=='manchester')
    if digest(raw)!=expected:raise ValueError('Frozen source hash mismatch')
    root=ET.fromstring(raw);ways={x.get('id'):x for x in root.findall('way')};nodes={x.get('id'):x for x in root.findall('node')}
    edges,footer,output_hash=read_native(ROOT/'map001-valhalla-native.jsonl')
    cases=[compare_way(ways[wid],nodes,edges) for wid in FROZEN_V2_IDS['manchester']]
    common=[x for x in cases if x['equivalent_scored_cohort']]
    rank=sorted([{'engine':engine,'passed':sum(x[key]=='PASS' for x in common),
                  'failed':sum(x[key]=='FAIL' for x in common),'total':len(common)}
                 for engine,key in [('DMN ★','dmn_verdict'),('Valhalla 3.9.1','valhalla_verdict')]],
                 key=lambda x:(-x['passed'],x['failed'])) if common else []
    report={'trial':'MAP-001-NATIVE-DIRECTED-ACCESS-1','source_sha256':expected,
            'native_output_sha256':output_hash,'native_enumeration':footer,
            'engine_versions':{'Valhalla':'3.9.1','DMN_importer_sha256':digest(Path('map_data/osm_xml.py').read_bytes())},
            'truth':'PROVISIONAL_OSM_SOURCE_NOT_ROAD_LAW','runtime_changed':False,
            'dmn_counts':dict(Counter(x['dmn_verdict'] for x in cases)),
            'valhalla_counts':dict(Counter(x['valhalla_verdict'] for x in cases)),
            'common_binary_way_cohort':len(common),'common_segment_checks':sum(x['expected_checks'] for x in common),
            'partial_access_only_ranking':rank,'full_category_ranking':None,'cases':cases,
            'turn_mask_observations':pair_observations(edges,ways,nodes,root.findall('relation'))}
    (ROOT/'map001-native-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('trial','native_enumeration','dmn_counts','valhalla_counts',
        'common_binary_way_cohort','common_segment_checks','partial_access_only_ranking')},indent=2))

if __name__=='__main__': main()
