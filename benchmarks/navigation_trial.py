"""GPS-001: closed-world synthetic correctness, never a real-road accuracy rank."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path

from benchmarks.osrm_match_reference import local_match_url, request_local_osrm_match
from benchmarks.valhalla_match_reference import trace_body, local_valhalla_trace
from benchmarks.graphhopper_match_reference import (
    research_gpx, request_local_graphhopper_match, flattened_matched_points)
from benchmarks.match_geometry_truth import closest_point_on_road
from gps.fix_quality import GPSFix, _distance_m
from gps.matcher import DirectedRoadMatcher
from gps.temporal_matcher import TemporalRoadMatcher
from map_data import Provenance, import_osm_xml

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'benchmarks/fixtures/synthetic-gps-001.xml'
ORACLE = ROOT / 'benchmarks/fixtures/synthetic-gps-001.json'
VERSIONS = {'DMN': 'repository temporal matcher', 'OSRM': '5.27.1',
            'Valhalla': '3.9.1', 'GraphHopper': '11.1 / Java 25'}
BLOCKERS = {
    'OsmAnd': 'No executable GPS-replay adapter integrated; app behaviour is not a batch matching API.',
    'Organic Maps': 'No executable GPS-replay adapter integrated; app behaviour is not a batch matching API.',
    'BRouter': 'Routing reference has no integrated observation-matching interface for GPS-001.',
    'openrouteservice': 'No integrated supported GPS-matching adapter for GPS-001.',
    'HERE': 'No configured permitted credentials or synthetic-map GPS adapter; paid access not authorised.',
    'Mapbox': 'No configured permitted credentials or synthetic-map GPS adapter; paid access not authorised.',
    'TomTom': 'No configured permitted credentials or synthetic-map GPS adapter; paid access not authorised.',
    'Google Maps': 'No configured permitted credentials or synthetic-map GPS adapter; paid access not authorised.',
    'Waze': 'No permitted automated replay interface; no scraping or automated consumer-app collection.',
}


def load_cases():
    return json.loads(ORACLE.read_text())['cases']


def judge(case, points):
    if len(points) != 4:
        points = [None] * 4  # Never align a partial response by guessing indices.
    complete = all(p is not None for p in points)
    errors = []
    for actual, truth in zip(points, case['truth']):
        if actual is None:
            errors.append(None)
            continue
        if len(actual) != 2 or any(type(x) not in (int, float) or not isfinite(x) for x in actual):
            raise ValueError('Invalid matched position')
        if abs(actual[0]) > 90 or abs(actual[1]) > 180:
            raise ValueError('Matched position outside Earth bounds')
        errors.append(_distance_m(GPSFix(0, *actual, 0), GPSFix(0, *truth, 0)))
    sign = 1 if case['direction'] == 'east' else -1
    checks = {
        'complete_four_observations': complete,
        'positions_within_5m': complete and all(e <= 5 for e in errors),
        'forward_direction': complete and all(
            sign * (b[1] - a[1]) > 0 for a, b in zip(points, points[1:])),
    }
    failures = []
    if not complete:
        failures.append('missing_required_match')
    if any(e is not None and e > 5 for e in errors):
        failures.append('position_error_over_5m')
    if complete and not checks['forward_direction']:
        failures.append('wrong_or_zero_observed_progress')
    return {'case_id': case['id'], 'split': case['split'],
            'outcome': 'PASS' if all(checks.values()) else 'FAIL',
            'checks': checks, 'failures': failures,
            'matched_observations': sum(p is not None for p in points),
            'position_errors_m': [round(e, 4) if e is not None else None for e in errors]}


def _report(system, rows, execution):
    return {'test_id': 'GPS-001', 'classification': 'synthetic-analytical-correctness-only',
            'system': system, 'version': VERSIONS[system], 'execution': execution,
            'map_sha256': sha256(FIXTURE.read_bytes()).hexdigest(),
            'oracle_sha256': sha256(ORACLE.read_bytes()).hexdigest(), 'cases': rows,
            'independent_real_road_truth': False, 'real_device_tests': 0,
            'configuration': {
                'DMN': 'streaming directed temporal matcher; no location lookahead',
                'OSRM': 'car.lua MLD; radiuses=6m; tidy=false; four original tracepoint slots',
                'Valhalla': 'auto; map_snap; search_radius=20m; matched_points alignment',
                'GraphHopper': 'car; gps_accuracy=10m; extended_json; exact four-point alignment',
            }[system]}


def run_dmn():
    imported = import_osm_xml(FIXTURE.read_bytes(), provenance=Provenance(
        'synthetic GPS-001', 'synthetic-v1', 'hand authored synthetic',
        'Synthetic OSM format; no OpenStreetMap contributor road data used'))
    rows = []
    for case in load_cases():
        matcher = TemporalRoadMatcher(DirectedRoadMatcher(imported.graph, imported.coordinates))
        points, reasons = [], []
        for obs in case['observations']:
            fix = GPSFix(*obs)
            result = matcher.update(fix)
            reasons.append(result.reason)
            if result.status != 'MATCHED':
                points.append(None)
            else:
                edge = imported.graph.edges[result.edge_id]
                points.append(closest_point_on_road(
                    (fix.latitude, fix.longitude), imported.coordinates[edge.source],
                    imported.coordinates[edge.target])[0])
        row = judge(case, points)
        row['decision_reasons'] = reasons
        rows.append(row)
    return _report('DMN', rows, 'actual_local_python')


def run_external(system):
    # These are actual pinned loopback executables, never injected replies.
    if system == 'OSRM':
        from benchmarks.osrm_live_reference import wait_for_local_router
        wait_for_local_router()
    elif system == 'Valhalla':
        from benchmarks.valhalla_live_reference import wait_for_local_router
        wait_for_local_router()
    elif system == 'GraphHopper':
        from benchmarks.graphhopper_live_reference import wait_for_graphhopper
        wait_for_graphhopper()
    else:
        raise ValueError('Unsupported live reference')
    rows = []
    for case in load_cases():
        fixes = [GPSFix(*obs) for obs in case['observations']]
        if system == 'OSRM':
            # GPS-001 requires every original observation. Test the hypothesis
            # that OSRM's optional tidy preprocessing caused baseline omissions;
            # keep the existing historical UK adapter configuration unchanged.
            response = request_local_osrm_match(local_match_url(fixes).replace('tidy=true', 'tidy=false'))
            points = [None] * 4
            if response.get('code') == 'Ok':
                points = [(p['location'][1], p['location'][0]) if p else None
                          for p in response['tracepoints']]
        elif system == 'Valhalla':
            response = local_valhalla_trace(trace_body(fixes))
            points = [None] * 4 if response.get('unroutable') else [
                (p['lat'], p['lon']) if p and p.get('type') in ('matched', 'interpolated')
                else None for p in response['matched_points']]
        else:
            response = request_local_graphhopper_match(research_gpx(fixes))
            points = [None] * 4 if response.get('no_match') else flattened_matched_points(response)
        rows.append(judge(case, points))
    return _report(system, rows, 'actual_live_loopback')


def scoreboard(reports):
    roster = ['DMN'] + [r['name'] for r in json.loads(
        (ROOT / 'config/dmn-engine-first-programme.json').read_text())['reference_families']]
    supplied = {}
    for report in reports:
        name = report['system']
        if name in supplied or name not in roster:
            raise ValueError('Duplicate or unknown engine')
        supplied[name] = report
    rows = []
    ids = [c['id'] for c in load_cases()]
    for name in roster:
        report = supplied.get(name)
        rankable = False
        if report:
            if (report.get('test_id') != 'GPS-001'
                    or report.get('map_sha256') != sha256(FIXTURE.read_bytes()).hexdigest()
                    or report.get('oracle_sha256') != sha256(ORACLE.read_bytes()).hexdigest()
                    or [c['case_id'] for c in report['cases']] != ids):
                raise ValueError('Nonmatching cases, map or oracle')
            rankable = report.get('execution') == (
                'actual_local_python' if name == 'DMN' else 'actual_live_loopback')
        passed = sum(c['outcome'] == 'PASS' for c in report['cases']) if rankable else 0
        failed = len(ids) - passed if rankable else 0
        rows.append({'system': name, 'rank': None,
                     'score_out_of_ten': round(10 * passed / len(ids), 3) if rankable else None,
                     'passed': passed, 'failed': failed, 'planned': len(ids),
                     'unresolved': 0, 'not_run': 0 if rankable else len(ids),
                     'reason': 'Synthetic closed-world output contract only' if rankable else
                     BLOCKERS.get(name, 'No actual GPS-001 execution record'),
                     'cases': report['cases'] if rankable else []})
    rows.sort(key=lambda r: (r['score_out_of_ten'] is None,
                            -(r['score_out_of_ten'] or 0), r['system']))
    previous = None
    for index, row in enumerate([r for r in rows if r['score_out_of_ten'] is not None], 1):
        if previous is None or row['score_out_of_ten'] != previous:
            rank = index
        row['rank'] = rank
        previous = row['score_out_of_ten']
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=list(VERSIONS))
    parser.add_argument('--reports', nargs='*', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((ROOT / 'results').resolve()):
        raise ValueError('Write ephemeral reports only under ignored results/')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.engine:
        report = run_dmn() if args.engine == 'DMN' else run_external(args.engine)
    else:
        report = {'test_id': 'GPS-001', 'scope': 'Synthetic analytical correctness only',
                  'formula': '10 * passing complete cases / six planned cases; ties share rank',
                  'rows': scoreboard([json.loads(p.read_text()) for p in args.reports or []])}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
