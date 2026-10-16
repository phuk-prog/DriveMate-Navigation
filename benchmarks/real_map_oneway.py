"""REAL-ONEWAY-001: public-map direction contract, NOT independently proven law.

Only pinned public road data; no personal traces. Synthetic endpoints are exact
map nodes. Selection is frozen from raw XML before importing or routing.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from time import perf_counter_ns
import xml.etree.ElementTree as ET
from benchmarks.itinero_public_probe import EXPECTED_XML_HASH, SOURCE
from engine import shortest_route, RouteNotFound
from map_data import import_osm_xml, Provenance

ROOT = Path(__file__).resolve().parents[1]


def judge(*, positive, allowed_present, forbidden_present, route_ids, forbidden_ids, no_route):
    checks = dict(allowed_import_present=allowed_present,
                  forbidden_import_absent=not forbidden_present,
                  route_has_no_forbidden_direction=not (set(route_ids) & forbidden_ids),
                  positive_route_available=not positive or (not no_route and bool(route_ids)))
    return dict(outcome='PASS' if all(checks.values()) else 'FAIL', checks=checks,
                real_world_legality='UNRESOLVED')


def prepare(raw):
    if sha256(raw).hexdigest() != EXPECTED_XML_HASH:
        raise ValueError('Pinned XML mismatch; do not substitute or discard cases')
    root = ET.fromstring(raw)
    nodes = {n.get('id'): [float(n.get('lat')), float(n.get('lon'))] for n in root.findall('node')}
    cases = []
    for way in sorted(root.findall('way'), key=lambda w: int(w.get('id'))):
        tags = {t.get('k'): t.get('v') for t in way.findall('tag')}
        direction = tags.get('oneway', '').lower()
        implicit = not direction and tags.get('junction') in ('roundabout', 'circular')
        if direction not in ('yes', '1', 'true', '-1', 'reverse') and not implicit:
            continue
        if tags.get('highway') not in ('residential', 'unclassified', 'tertiary', 'secondary', 'primary', 'trunk', 'motorway', 'living_street', 'motorway_link', 'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link'):
            continue
        # Explicit ordinary motorcar permission only; do not infer exceptions.
        if any(k.endswith('conditional') for k in tags):
            continue
        if any(tags.get(k) not in (None, 'yes', 'designated', 'permissive') for k in ('access', 'vehicle', 'motor_vehicle', 'motorcar')):
            continue
        refs = [n.get('ref') for n in way.findall('nd')]
        for i, (a, b) in enumerate(zip(refs, refs[1:])):
            if a not in nodes or b not in nodes or a == b or nodes[a] == nodes[b]:
                continue
            reverse = direction in ('-1', 'reverse')
            src, dst = (b, a) if reverse else (a, b)
            allowed = f"w:{way.get('id')}:{i}:{'r' if reverse else 'f'}"
            forbidden = f"w:{way.get('id')}:{i}:{'f' if reverse else 'r'}"
            cases.append(dict(id=f'REAL-ONEWAY-001-{len(cases)+1:03d}', way_id=way.get('id'), segment=i,
                              name=tags.get('name'), tags=tags, source=f'osm:{src}', destination=f'osm:{dst}',
                              source_coordinates=nodes[src], destination_coordinates=nodes[dst],
                              allowed_edge=allowed, forbidden_edge=forbidden))
            break
        if len(cases) == 6:
            break
    return dict(test_id='REAL-ONEWAY-001', classification='real public map; synthetic exact-node endpoints, no personal traces',
                source_url=SOURCE, map_sha256=EXPECTED_XML_HASH, attribution='OpenStreetMap contributors; ODbL',
                selection='first six eligible ways numerically; first nondegenerate segment; raw XML before importer/router',
                expectation='allowed edge present; forbidden edge absent; both route directions never use any forbidden selected edge; allowed direction returns route',
                reverse_no_route_scope='direction safety only; does not prove absence of a legal alternative',
                independent_road_law='UNRESOLVED: authority source not acquired',
                required_distinct_ways=6, selected_distinct_ways=len(cases), selection_complete=len(cases)==6, cases=cases)


def main():
    p=argparse.ArgumentParser(); p.add_argument('--prepare', action='store_true'); a=p.parse_args()
    raw=(ROOT/'results/real-oneway-map.osm').read_bytes()
    manifest=ROOT/'results/real-oneway-cases.json'
    if a.prepare:
        manifest.write_text(json.dumps(prepare(raw), indent=2)+'\n')
        print(manifest.read_text()); return
    frozen=json.loads(manifest.read_text())
    if frozen != prepare(raw):
        raise ValueError('Frozen cases changed')
    data=import_osm_xml(raw, provenance=Provenance('public Manchester bbox', 'Geofabrik260901', SOURCE, 'OpenStreetMap contributors; ODbL'))
    forbidden={c['forbidden_edge'] for c in frozen['cases']}
    rows=[]
    for c in frozen['cases']:
        for positive in (True, False):
            s,t=(c['source'],c['destination']) if positive else (c['destination'],c['source'])
            start=perf_counter_ns()
            try:
                route=shortest_route(data.graph,s,t); ids=list(route.edge_ids); no_route=False
            except RouteNotFound:
                ids=[]; no_route=True
            elapsed=perf_counter_ns()-start
            verdict=judge(positive=positive, allowed_present=c['allowed_edge'] in data.graph.edges,
                          forbidden_present=c['forbidden_edge'] in data.graph.edges,
                          route_ids=ids, forbidden_ids=forbidden, no_route=no_route)
            rows.append(dict(case_id=c['id']+('-allowed' if positive else '-reverse'), source=s, destination=t,
                             route_edge_ids=ids, no_route=no_route, calculation_ns=elapsed, **verdict))
    report=dict(test_id='REAL-ONEWAY-001', system='DMN', run_sha=os.environ.get('GITHUB_HEAD_SHA'),
                execution='actual_local_python_import_and_shortest_route' if rows else 'actual_local_python_import_only_no_routing',
                actual_route_calculations=len(rows), version='repository run_sha',
                manifest=frozen, oracle_sha256=sha256(manifest.read_bytes()).hexdigest(), cases=rows,
                passed=sum(r['outcome']=='PASS' for r in rows), total=len(rows),
                required_observations=12, cohort_complete=frozen['selection_complete'],
                trial_outcome='JUDGED' if frozen['selection_complete'] else 'INCOMPLETE_CASE_INVENTORY',
                external_engines_executed=0, comparative_rank=None, score_out_of_ten=None,
                independent_road_law='UNRESOLVED', gps_quality_cases=0,
                limitations=['map-tag contract only', 'no independent legality or optimality proof', 'no comparative performance ranking', 'only selected directions checked', 'not Android execution'])
    (ROOT/'results/real-oneway-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['cohort_complete']:
        raise SystemExit('Incomplete frozen case inventory; diagnostic rows are not a completed trial')
    if report['passed'] != report['total']:
        raise SystemExit('Direction contract failed; retain all cases')

if __name__=='__main__': main()
