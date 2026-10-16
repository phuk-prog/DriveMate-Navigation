"""Category 1 applicability review; safety policy is not road-law correctness.

Consumes fresh same-run Valhalla candidates, including filtered edges. Spatial
samples never establish missing-edge or exhaustive turn-pair correctness.
"""
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from benchmarks.map001_graph_fact_audit import ROOT, digest, tags, isolated
from benchmarks.map001_direction_contract import audit_way, MODES, CONTEXT, direction_access
from benchmarks.map001_v3 import FROZEN_V2_IDS
from map_data import import_osm_xml, Provenance


def access_basis(t):
    # Only ordinary-car hierarchy; unrelated bus/bicycle permissions do not count.
    relevant = {k:v for k,v in t.items() if k.split(':')[0] in MODES}
    if any(k.endswith(':conditional') for k in relevant):
        return 'CONDITIONAL_UNSUPPORTED', relevant
    for mode in MODES:
        if mode in t and t[mode] in CONTEXT:
            return ('AUTHORIZATION_REQUIRED' if t[mode] == 'private'
                    else 'JOURNEY_PURPOSE_REQUIRED'), relevant
        if mode in t:
            return 'EXPLICIT_MODE_PERMISSION', relevant
    if t.get('highway') in ('service','track'):
        return 'UNSPECIFIED_SERVICE_PERMISSION', relevant
    return 'OTHER_SOURCE_OR_BARRIER_UNCERTAINTY', relevant


def review_way(way, nodes):
    original = audit_way(way, nodes)
    if original['verdict'] != 'NOT_JUDGED':
        return None
    basis, relevant = access_basis(tags(way))
    imported = import_osm_xml(isolated(way,nodes),provenance=Provenance(
        'Manchester','frozen v3','access applicability review',
        'OpenStreetMap contributors; ODbL'))
    states = Counter(e.access for e in imported.graph.edges.values())
    safety = ('SAFE_WITHHELD' if states and not states['allowed']
              else 'NOT_JUDGED')
    return {'source_way':way.get('id'), 'name':tags(way).get('name'),
            'highway':tags(way).get('highway'), 'source_access_tags':relevant,
            'basis':basis, 'dmn_original_verdict':'NOT_JUDGED',
            'dmn_edge_access_counts':dict(states),
            'dmn_no_permission_safety_policy':safety,
            'road_legality_verdict':'NOT_JUDGED',
            'evidence_needed':('explicit public motorcar access or verified access rule'
                if basis=='UNSPECIFIED_SERVICE_PERMISSION' else
                'trip purpose / destination entitlement / owner authorization'),
            'policy_scope':'no asserted authorization or qualifying journey purpose'}


def decode_shape(encoded):
    """Decode Valhalla JSON polyline6; bounded malformed input fails explicitly."""
    if not isinstance(encoded,str) or len(encoded)>20000:
        raise ValueError('Missing/oversized shape')
    values=[]; total=[0,0]; position=0
    while position<len(encoded):
        for axis in (0,1):
            v=shift=0
            while True:
                if position>=len(encoded) or shift>35: raise ValueError('Malformed polyline')
                part=ord(encoded[position])-63; position+=1
                if not 0<=part<=63: raise ValueError('Invalid polyline character')
                v|=(part&31)<<shift; shift+=5
                if part<32: break
            total[axis]+= ~(v>>1) if v&1 else v>>1
        values.append((total[0]/1e6,total[1]/1e6))
    if len(values)<2: raise ValueError('Incomplete shape')
    return values


def osm_orientation(candidate, way, nodes):
    """forward is relative to EdgeInfo storage, not inherently OSM node order."""
    item=candidate.get('edge',{}); info=candidate.get('edge_info',{})
    forward=item.get('forward')
    if type(forward) is not bool: return None
    try: shape=decode_shape(info.get('shape'))
    except (ValueError,TypeError): return None
    refs=[n.get('ref') for n in way.findall('nd')]
    coords=[(float(nodes[n].get('lat')),float(nodes[n].get('lon'))) for n in refs]
    def positions(point):
        return [i for i,c in enumerate(coords) if max(abs(c[j]-point[j]) for j in (0,1))<=0.000002]
    a,b=positions(shape[0]),positions(shape[-1])
    # Closed/repeated geometry or ambiguous coordinate identity stays unknown.
    if len(a)!=1 or len(b)!=1 or a[0]==b[0]: return None
    return forward == (a[0]<b[0])


def candidate_review(wid, located, way, nodes):
    rows=[]
    for bucket in ('edges','filtered_edges'):
        for c in located.get(bucket,[]) or []:
            if not isinstance(c,dict): continue
            info=c.get('edge_info',{}); item=c.get('edge',{})
            if str(info.get('way_id',c.get('way_id')))!=wid: continue
            car=item.get('access',{}).get('car')
            orient=osm_orientation(c,way,nodes)
            expected=direction_access(tags(way),orient) if type(orient) is bool else 'unknown'
            verdict=('UNSUPPORTED_ORIENTATION_OR_SCHEMA' if type(orient) is not bool or type(car) is not bool
                     else 'CONTEXT_NOT_BINARY' if expected=='contextual'
                     else 'HARD_DIRECTION_CONTRADICTION_CANDIDATE' if expected=='prohibited' and car
                     else 'HARD_DENIAL_OBSERVED' if expected=='prohibited' and not car
                     else 'SOURCE_ACCESS_VISIBLE' if expected=='allowed' and car
                     else 'UNKNOWN_OR_OTHER_RESTRICTION')
            rows.append({'bucket':bucket,'graph_id':c.get('edge_id',{}).get('value'),
                         'end_node_id':item.get('end_node',{}).get('value'),
                         'stored_shape_forward':item.get('forward'),
                         'osm_forward_verified':orient,
                         'source_direction_expected':expected,'verdict':verdict,
                         'car_access':car,'destination_only':item.get('destination_only'),
                         'not_thru':item.get('not_thru'),
                         'simple_turn_mask':item.get('restrictions'),
                         'local_edge_index':item.get('local_edge_index')})
    return {'source_way':wid,'candidates':rows,
            'missing_edges_verdict':'UNSUPPORTED_SPATIAL_SAMPLE',
            'turn_pairs_verdict':'UNSUPPORTED_MISSING_MASK_AND_LOCAL_INDEX'}


def main():
    raw=(ROOT/'map001-manchester.osm').read_bytes()
    manifest=json.loads((ROOT/'map001-v3-manifest.json').read_text())
    expected=next(x['source_sha256'] for x in manifest['areas'] if x['area']=='manchester')
    if digest(raw)!=expected: raise ValueError('Frozen source mismatch')
    root=ET.fromstring(raw); ways={w.get('id'):w for w in root.findall('way')}
    nodes={n.get('id'):n for n in root.findall('node')}
    ids=FROZEN_V2_IDS['manchester']
    cohort=[r for wid in ids if (r:=review_way(ways[wid],nodes)) is not None]
    fresh_path=ROOT/'map001-valhalla-fresh-candidates.json'
    fresh=json.loads(fresh_path.read_text())
    if fresh['source_sha256']!=expected or fresh['way_ids']!=ids:
        raise ValueError('Valhalla input/cohort mismatch')
    if len(fresh['responses'])!=len(ids): raise ValueError('Incomplete Valhalla responses')
    valhalla=[candidate_review(wid,row,ways[wid],nodes) for wid,row in zip(ids,fresh['responses'])]
    observations=[c for row in valhalla for c in row['candidates']]
    report={'trial':'MAP-001-ACCESS-APPLICABILITY-1','source_sha256':expected,
            'truth':'PROVISIONAL_OSM_SOURCE_NOT_ROAD_LAW',
            'fresh_valhalla_response_sha256':digest(fresh_path.read_bytes()),
            'runtime_changed_in_this_stage':False,
            'unjudged_case_count':len(cohort),
            'basis_counts':dict(Counter(x['basis'] for x in cohort)),
            'dmn_no_permission_policy_counts':dict(Counter(x['dmn_no_permission_safety_policy'] for x in cohort)),
            'cases':cohort,'valhalla':valhalla,
            'valhalla_counts':{'candidate_observations':len(observations),
                'filtered_observations':sum(x['bucket']=='filtered_edges' for x in observations),
                'osm_direction_verified':sum(type(x['osm_forward_verified']) is bool for x in observations),
                'simple_masks_available':sum(x['simple_turn_mask'] is not None for x in observations),
                'verdicts':dict(Counter(x['verdict'] for x in observations)),
                'stored_forward_differs_from_osm':sum(type(x['osm_forward_verified']) is bool and
                    x['osm_forward_verified'] != x['stored_shape_forward'] for x in observations)},
            'full_category_ranking':None,'legality_counts_unchanged':True}
    (ROOT/'map001-access-applicability.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('trial','unjudged_case_count','basis_counts',
                      'dmn_no_permission_policy_counts','valhalla_counts')},indent=2))

if __name__=='__main__': main()
