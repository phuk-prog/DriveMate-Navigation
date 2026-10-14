"""Revision/map checked larger-route comparison, with narrowly scoped rankings."""
import json
import math
from pathlib import Path
import subprocess
from statistics import median
from benchmarks.expanded_fixture import suite
from benchmarks.expanded_comparison import LABELS
from benchmarks.expanded_report import tally
from benchmarks.route_quality_fixture import PROTOCOL,controls,judge_route


def build(root,expected_commit=None):
    sha=expected_commit or subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    data=suite();truth={c['id']:c for c in data['quality_cases']};records={}
    for path in Path(root).rglob('quality.json'):
        r=json.loads(path.read_text());e=r['engine']
        if e not in LABELS or e in records:raise ValueError('Unknown/duplicate quality engine')
        if r.get('commit_sha')!=sha or r.get('dataset_sha256')!=data['dataset_sha256'] or r.get('protocol')!=PROTOCOL or r.get('fresh_execution') is not True:
            raise ValueError('Stale or mismatched quality execution')
        if r.get('judge_controls')!=controls(data):raise ValueError('Missing quality controls')
        if len(r['cases'])!=len(truth) or {c['id'] for c in r['cases']}!=set(truth):raise ValueError('Quality coverage mismatch')
        for c in r['cases']:
            source=truth[c['id']]
            if any(c.get(k)!=v for k,v in source.items()):raise ValueError('Quality case truth changed')
            if c['status'] not in ('pass','fail','unresolved'):raise ValueError('Invalid quality outcome')
            if c['status']=='pass':
                independent=judge_route(data,source,c.get('actual_ways'),c.get('actual_ways') is None)
                if independent['status']!='pass':raise ValueError('False route-quality pass')
                for key in ('distance_m','minimum_m','distance_ratio'):
                    a,b=c.get(key),independent[key]
                    if b is None:
                        if a is not None:raise ValueError('False no-route quality metric')
                    elif not isinstance(a,(float,int)) or isinstance(a,bool) or not math.isfinite(a) or not math.isclose(a,b,rel_tol=1e-9):
                        raise ValueError('Quality distance differs from author oracle')
            if c.get('instruction_status')=='pass' and (c['status']!='pass' or c.get('actual_turns')!=source['expected_turns']):
                raise ValueError('False junction-instruction pass')
            if source['expected_turns'] is not None and e in ('routingkit','pgrouting') and c.get('instruction_status')!='not_supported':
                raise ValueError('Algorithm cannot earn navigation instruction score')
        records[e]=r
    groups=[('legal_routes',list(truth)),
            ('distance_within_1_percent',[k for k,c in truth.items() if c['category']!='reverse_no_route']),
            ('stateless_reroute',[k for k,c in truth.items() if c['category']=='stateless_reroute']),
            ('junction_instructions',[k for k,c in truth.items() if c['category']=='junction_instructions'])]
    categories=[];issues=[]
    for category,ids in groups:
        counts={}
        for e in LABELS:
            rows={c['id']:c for c in records.get(e,{}).get('cases',[])};states=[]
            for ident in ids:
                c=rows.get(ident);status='unresolved'
                if category=='junction_instructions' and e in ('routingkit','pgrouting'):status='not_supported'
                elif c:
                    status=c['status']
                    if category=='junction_instructions':status=c.get('instruction_status') or 'unresolved'
                    elif category=='distance_within_1_percent' and status=='pass':status='pass' if c['distance_ratio']<=1.01 else 'fail'
                states.append(status)
                if status in ('fail','unresolved'):
                    issues.append({'category':category,'engine':e,'case':ident,'outcome':status,
                                   'issue':c.get('issue') if c and c.get('issue') else
                                     'Turn-family mismatch' if category=='junction_instructions' else
                                     'Distance exceeds independent shortest by >1%' if c and category=='distance_within_1_percent' and c['status']=='pass' else 'Missing or unresolved execution'})
            counts[e]=tally(states)
        ranks={}
        for name,cohort in [('native-road-import',list(LABELS)[:5]),('supplied-transition-algorithm',list(LABELS)[5:])]:
            complete=all(not counts[e]['unresolved'] and not counts[e]['not_supported'] for e in cohort)
            ordered=sorted(cohort,key=lambda e:counts[e]['fail']) if complete else []
            ranks[name]=[{'engine':e,'rank':1+sum(counts[v]['fail']<counts[e]['fail'] for v in cohort)} for e in ordered]
        categories.append({'category':category,'counts':counts,'ranks':ranks})
    speeds=[]
    for path in Path(root).rglob('quality_speed.json'):
        r=json.loads(path.read_text())
        if r.get('dataset_sha256')!=data['dataset_sha256'] or r.get('commit_sha')!=sha:raise ValueError('Speed revision/map mismatch')
        if any(not isinstance(s.get('milliseconds'),(int,float)) or isinstance(s['milliseconds'],bool) or
               not math.isfinite(s['milliseconds']) or s['milliseconds']<=0 for s in r['samples']):
            raise ValueError('Invalid paired timing sample')
        expected={(e,c['id'],i) for e in ('drivemate','graphhopper') for c in data['quality_cases']
                  if c['id'].split('/')[-1] in ('alternatives0','replan0') for i in range(10)}
        actual={(s['engine'],s['case'],s['repeat']) for s in r['samples']}
        for sample in r['samples']:
            source=truth.get(sample['case'])
            if source is None or judge_route(data,source,sample.get('actual_ways'),False)['status']!='pass':
                raise ValueError('Timed sample has no independently legal complete path')
            if sample['engine']=='graphhopper' and not (sample.get('endpoint_check') or {}).get('within_2m'):
                raise ValueError('Timed sample lacks endpoint equivalence')
        r['complete']=not r['errors'] and actual==expected and len(r['samples'])==len(expected)
        r['summary']={}
        for e in ('drivemate','graphhopper'):
            values=sorted(s['milliseconds'] for s in r['samples'] if s['engine']==e)
            if values:r['summary'][e]={'requests':len(values),'median_ms':median(values),
                                     'p95_ms':values[math.ceil(.95*len(values))-1],'max_ms':max(values)}
        speeds.append(r)
    if len(speeds)>1:raise ValueError('Duplicate paired timing execution')
    return {'commit_sha':sha,'dataset_sha256':data['dataset_sha256'],'protocol':PROTOCOL,
            'nodes':len(data['nodes']),'ways':len(data['ways']),'categories':categories,
            'issues':issues,'paired_speed':speeds,'overall_rank':None}


def markdown(r):
    lines=['# Larger-map route quality, replanning and instructions','',
           f"Revision `{r['commit_sha']}`; map `{r['dataset_sha256']}`.",
           f"Shared map: {r['nodes']} author nodes, {r['ways']} ways; 64 new cases, 32 held out.",'',
           'Distance compares each legal result with independently shortest authored distance. '
           'The 1% criterion is a distance objective, not vendor cost equivalence. Category subsets overlap.']
    for category in r['categories']:
        lines+=['','## '+category['category'],'','| Engine | Passed/total | Failed | Unresolved | Not supported |','|---|---:|---:|---:|---:|']
        for e,c in category['counts'].items():lines.append(f"| {LABELS[e]} | {c['pass']}/{c['total']} | {c['fail']} | {c['unresolved']} | {c['not_supported']} |")
        for cohort,ranks in category['ranks'].items():lines.append(cohort+' ranks: '+(', '.join(f"{x['rank']}: {LABELS[x['engine']]}" for x in ranks) or 'unavailable (incomplete/unsupported cohort)'))
    lines+=['','## Paired same-host warm configured-service timings','']
    if not r['paired_speed']:lines.append('Unavailable; no speed ranking.')
    for s in r['paired_speed']:
        lines+=['| Service | Requests | Median ms | p95 ms | Maximum ms |','|---|---:|---:|---:|---:|']
        for e,v in s['summary'].items():lines.append(f"| {LABELS[e]} | {v['requests']} | {v['median_ms']:.3f} | {v['p95_ms']:.3f} | {v['max_ms']:.3f} |")
        lines.append('Complete paired workload: '+str(s['complete'])+'. '+s['scope']+'.')
        if s['complete']:lines.append('p95 order for this workload: '+', '.join(LABELS[e] for e in sorted(s['summary'],key=lambda e:s['summary'][e]['p95_ms'])))
        lines.extend('- '+x for x in s['limits'])
    lines+=['','## Exact failed or unresolved checks','', '| Category | Engine | Case | Outcome | Diagnosis |','|---|---|---|---|---|']
    for x in r['issues']:lines.append(f"| {x['category']} | {LABELS[x['engine']]} | {x['case']} | {x['outcome']} | {x['issue']} |")
    lines+=['','Stateless replanning does not test live missed-turn detection. Instruction checks cover fixed 90-degree turn families, not spoken timing, occupied lanes or arrival.',
            'Other engine timings were collected in different CI jobs and cannot establish a common-host speed winner.',
            '**Overall navigation winner: not established.** Earlier legal/critical failures remain higher priority than distance or speed.','']
    return '\n'.join(lines)


def save(root,out):
    r=build(root);out=Path(out)
    (out/'ROUTE_QUALITY_SCORECARD.md').write_text(markdown(r),encoding='utf-8')
    (out/'route_quality_results.json').write_text(json.dumps(r,indent=2)+'\n')
    return r
