"""Render retained executed evidence; never run engines or fill missing timings."""
from hashlib import sha256
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'references'


def load(name):return json.loads((REF/name).read_text())


def render():
    lines=['# Executed research results and rankings','',
           'Generated from retained evidence by `python -m tools.research_results`. This is a view of recorded runs, not a new engine execution.',
           '', 'Scores:10 × passed / frozen judged cases; highest first, ties share rank. Historical invented-map analytical controls do not establish real-road superiority. Unsupported/unavailable families are excluded from active tables and remain in the linked source audits. No overall score mixes these cohorts.', '',
           'Timing unit: milliseconds(ms), not milligrams. Missing measured calculation latency is UNAVAILABLE. Predicted journey time and maneuver duration are not calculation latency.', '']
    for label,name in [('GPS-001 output contract','gps001-expanded-scorecard-20261015.json'),('ROUTE-001 one-way analytical control','route001-expanded-scorecard-20261015.json'),('ROUTE-002 shared static legality controls','route002-scorecard-20261016.json'),('JUNCTION-001 analytical maneuvers','junction001-scorecard-20261016.json')]:
        d=load(name);ranked=[r for r in d['rows'] if r.get('rank') is not None]
        ranked.sort(key=lambda r:(r['rank'],r['system']))
        lines += ['## '+label,'','Historical synthetic analytical road layout. Calculation speed was not measured comparably across these engines.','',f'[Full per-case verdicts, versions/configurations, hashes, execution sources and excluded-family audit](../references/{name}).','', '| Rank | Engine | Pass / judged | Score /10 | Calculation latency |','|---:|---|---:|---:|---|']
        case_ids=d.get('ranked_case_ids')
        for r in ranked:
            cases=[c for c in r['cases'] if not case_ids or c['case_id'] in case_ids]
            passed=sum(c['outcome']=='PASS' for c in cases)
            if not cases or abs(10*passed/len(cases)-r['score_out_of_ten'])>.001:
                raise ValueError('Retained score/denominator mismatch: '+name+' '+r['system'])
            lines.append(f"|{r['rank']}|{r['system']}|{passed}/{len(cases)}|{r['score_out_of_ten']:.3f}|UNAVAILABLE|")
        ids=case_ids or [c['case_id'] for c in ranked[0]['cases']]
        lines += ['', '| Case |'+'|'.join(r['system'] for r in ranked)+'|','|---|'+'---|'*len(ranked)]
        for cid in ids:
            cells=[]
            for r in ranked:
                c=next(c for c in r['cases'] if c['case_id']==cid);cells.append(c['outcome'])
            lines.append('|'+cid+'|'+'|'.join(cells)+'|')
        failures=[]
        for r in ranked:
            for c in r['cases']:
                if c['outcome']=='FAIL' and (not case_ids or c['case_id'] in case_ids):
                    failed_checks=[key for key,value in c.get('checks',{}).items() if value is False]
                    reasons=c.get('failures') or failed_checks or ['required output contract failed; see raw case']
                    failures.append('- '+r['system']+' / '+c['case_id']+': '+str(reasons))
        if failures:lines += ['', 'Recorded failures:', '', *failures]
        lines.append('')
    lines += ['## Isolated DMN safety controllers','', 'These are single-system analytical controls, with no competitive winner. Full cases and actual execution metadata are linked.', '', '| Test | Passed / actual cases | Scope | Evidence |','|---|---:|---|---|']
    for name,scope in [('gps002-stream-batch-20261015.json','synthetic streaming faults'),('reroute001-after-20261016.json','isolated reroute lifecycle; additional controls separate'),('arrival001-after-20261016.json','isolated arrival controller'),('offline001-after-20261016.json','host Python offline routes in isolated namespace; not Android')]:
        d=load(name);r=d['report'];cases=r['cases'];passed=sum(c['outcome']=='PASS' for c in cases)
        lines.append(f"|{r['test_id']}|{passed}/{len(cases)}|{scope}|[cases](../references/{name})|")
    lines += ['', '## RESOURCE-001 calculation timing','',
              'One DMN family, three algorithm configurations on invented weighted grids. Values below are the retained CI timing-worker measurements, ten warm samples each. Setup is separate. All displayed cases passed analytical route checks. These do not rank different navigation families or predict Android speed.', '',
              '| Case | Configuration | Median ms | p95 ms | Graph build ms | Additional preparation ms |','|---|---|---:|---:|---:|---:|']
    r=load('resource001-ci-20261016.json')['report']
    workers=[w for w in r['workers'] if w['phase']=='timing']
    rows=[]
    for w in workers:
        for c in w['cases']:
            if c['outcome']!='PASS':raise ValueError('Do not present failing resource result as valid speed')
            rows.append((c['case_id'],c['median_ns'],w,c))
    for cid,_,w,c in sorted(rows,key=lambda x:(x[0],x[1])):
        lines.append(f"|{cid}|{w['configuration']}|{c['median_ns']/1e6:.6f}|{c['p95_ns']/1e6:.6f}|{w['graph_build_ns']/1e6:.6f}|{w['prepare_ns']/1e6:.6f}|")
    lines += ['', 'Within each identical case, rows are ordered by measured median. These are configurations of one family, not extra engines. With10 samples, nearest-rank p95 is the largest sample; do not treat it as a stable population estimate. [Raw samples, CPU/runtime, memory scopes, versions and CI](../references/resource001-ci-20261016.json).', '',
              '## Real-map reference output probes','',
              'Itinero and Routino each passed3/3 frozen endpoint/output cases. No path-law or GNSS-quality verdict is implied. Each Routino time includes a new CLI process; Itinero did not retain a comparable per-request latency, so there is no cross-engine speed rank.', '',
              '| Request | Routino first ms | Routino confirmation ms | Max endpoint error m | Itinero calculation ms |','|---|---:|---:|---:|---|']
    first=load('ref007-routino-real-map-20261016.json')['report'];confirm=load('ref007-routino-confirmation-20261016.json')['report']
    for a,b,c in zip(first['raw_outputs'],confirm['raw_outputs'],confirm['cases']):
        lines.append(f"|{c['case_id']}|{a['wall_ns']/1e6:.6f}|{b['wall_ns']/1e6:.6f}|{max(c['start_error_m'],c['end_error_m']):.6f}|UNAVAILABLE|")
    lines += ['', '[Routino exact commands/configuration/output and CI](../references/ref007-routino-confirmation-20261016.json); [Itinero exact evidence](../references/ref006-itinero-confirmation-20261016.json). The endpoint contract matches; speed scopes do not. No overall winner is assigned.', '', '## Unresolved and incomplete evidence','',
              '- UK40-case replay:17 source-map-correct,0 confidently wrong,23 withheld; seven lost matches remain unresolved. [Diagnostics](../references/gps001-uk-topology-20261015.json).',
              '- REAL-ONEWAY-001:zero eligible one-way ways in fixed extract; zero route calculations, no pass/rank. [Inventory](../references/real-oneway-inventory-20261016.json).',
              '- Seven historical external routing families are not a ten-engine common real-map/GPS cohort.',
              '- App, emulator/native lifecycle, physical GNSS, independent road-law and sustained target-device claims remain unverified.', '']
    gps=REF/'gps003-real-map-20261016.json'
    if gps.is_file():
        d=json.loads(gps.read_text());r=d['report'];lines += ['## GPS-003 real-map stream results','',f"{r['passed']}/{r['total']} streams pass across{len(r['manifest']['segments'])} map-derived base segments;{r['events']} simulated GPS updates. Counts:{r['counts']}. Map agreement and analytical fault expectations, not independent GNSS or legal truth. No competitive rank.", '', '| Stream | Outcome | Per-event actual status | Per-event calculation ms |','|---|---|---|---|']
        for c in r['cases']:
            lines.append('|'+c['case_id']+'|'+c['outcome']+'|'+', '.join(e['actual_status'] for e in c['events'])+'|'+', '.join(f"{e['calculation_ns']/1e6:.6f}" for e in c['events'])+'|')
        lines += ['', '[Every frozen signal, expected/actual edge, check, failure reason, source/oracle hash and CI](../references/gps003-real-map-20261016.json). Single-update wall times are diagnostic, not cross-engine benchmarks.','']
    lines += ['## Whole-app programme','', 'See [whole-app validation programme](APP_VALIDATION_PROGRAMME.md). App test discovery is not execution. Private app inventory stays outside this public repository. New versions/configurations must be retested; old results do not transfer automatically.','']
    return '\n'.join(lines)


def main():
    (ROOT/'docs/DMN_RESULTS_OVERVIEW.md').write_text(render())

if __name__=='__main__':main()
