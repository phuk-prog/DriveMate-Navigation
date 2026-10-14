"""Safety-first, evidence-backed ranks: same cases and no invented winners."""
import json
from pathlib import Path

def judge(comparison):
    cases=comparison.get('cases',())
    if not cases:return {'status':'no_case_matched_evidence','rankings':[],'failures':[]}
    result=[];failures=[]
    for name,s in comparison.get('summaries',{}).items():
        if s['not_tested'] or s['test_cases']!=len(cases):continue
        if s['passed']+s['failed']+s['unknown']!=len(cases):
            raise ValueError('Inconsistent outcome totals: '+name)
        safety=0
        for item in cases:
            status=item['results'][name]
            if status=='fail':
                severity=('CRITICAL: forbidden route request produced a route'
                    if item['expected_ways'] is None else
                    'ROUTE MISMATCH: investigate legality or alternate routing')
                if item['expected_ways'] is None:safety+=1
                failures.append({'engine':name,'case':item['case'],
                                 'severity':severity,'status':'fail'})
            elif status=='unknown':
                failures.append({'engine':name,'case':item['case'],
                                 'severity':'UNRESOLVED: not a pass or confirmed fail',
                                 'status':'unknown'})
        result.append({'engine':name,'passed':s['passed'],'failed':s['failed'],
            'unknown':s['unknown'],'safety_failures':safety,
            'scenario_count':len(cases),'score':round(100*s['passed']/len(cases),2)})
    result.sort(key=lambda e:(e['safety_failures'],-e['passed'],e['failed'],e['unknown']))
    last=None;rank=0
    for index,e in enumerate(result,1):
        key=(e['safety_failures'],e['passed'],e['failed'],e['unknown'])
        if key!=last:rank=index;last=key
        e['rank']=rank
    return {'status':'synthetic_route_ranking','rankings':result,'failures':failures,
        'policy':[
            'Rank only executions of the identical route-case set, on an identical map',
            'Confirmed prohibited-path failures disqualify otherwise higher scores',
            'Then order by passes, mismatches, unresolved outcomes',
            'Equal measured outcomes produce equal rank, not arbitrary placement',
            'No unmeasured engine ranks last and no inferred product-level winner',
        ]}

def markdown(report):
    lines=['# Safety-first ranking: comparable synthetic route cases','',
        'Ranks only executed routing-core cases. This is not a real-driving or complete-app leaderboard.',
        '',
        '| Place | Engine/configuration | Score | Passed | Failed | Unresolved | Prohibited-path failures |',
        '|---:|---|---:|---:|---:|---:|---:|']
    for e in report['rankings']:
        lines.append(f"| {e['rank']} | {e['engine']} | {e['score']:.2f}/100 | "
                     f"{e['passed']}/{e['scenario_count']} | {e['failed']} | {e['unknown']} | {e['safety_failures']} |")
    if not report['rankings']:lines.append('| — | No equivalent completed cases | — | — | — | — | — |')
    lines+=['','## Highlighted failures and unresolved results','',
            '| Severity | Engine | Scenario | Outcome |','|---|---|---|---|']
    for issue in report['failures']:
        lines.append(f"| **{issue['severity']}** | {issue['engine']} | {issue['case']} | {issue['status']} |")
    if not report['failures']:lines.append('| No failures or unknown results in the measured subset | — | — | — |')
    lines+=['','## Rules','']
    lines+=['- '+x for x in report.get('policy',())]
    lines+=['',
      'Caution: RoutingKit CH and pgRouting search an explicitly prepared graph from '
      'the same authored source. This compares their routing algorithms, not native OSM importing, '
      'roundabout exit numbering, live GPS recovery, lane guidance or instruction delivery.']
    return '\n'.join(lines)+'\n'

def save(report,out):
    p=Path(out);p.mkdir(parents=True,exist_ok=True)
    (p/'RANKING.md').write_text(markdown(report))
    (p/'ranking.json').write_text(json.dumps(report,indent=2)+'\n')
