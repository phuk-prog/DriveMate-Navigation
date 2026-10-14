"""Fail-closed comparable category ledger for fresh expanded engine evidence."""
from collections import Counter
import json
import hashlib
import subprocess
from pathlib import Path
from benchmarks.expanded_fixture import suite
from benchmarks.expanded_comparison import LABELS, clean_trace

STATES=('pass','fail','unresolved','not_supported')


def tally(states):
    counts=Counter(states)
    if set(counts)-set(STATES): raise ValueError('Invalid expanded outcome')
    return {**{s:counts[s] for s in STATES},'total':sum(counts.values())}


def build(root, *, expected_commit=None):
    expected_commit=expected_commit or subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    data=suite();expected={c['id'] for c in data['cases']};records={}
    commits=set()
    for path in Path(root).rglob('expanded.json'):
        r=json.loads(path.read_text());name=r['engine']
        if name not in LABELS or name in records: raise ValueError('Unknown or duplicate engine evidence')
        if r.get('fresh_execution') is not True or r.get('dataset_sha256')!=data['dataset_sha256'] or r.get('protocol')!=data['protocol']:
            raise ValueError('Expanded evidence has stale or mismatched map/protocol')
        if r.get('commit_sha')!=expected_commit:
            raise ValueError('Expanded evidence revision differs from current report checkout')
        if len(r['route_cases'])!=len(expected) or {c['id'] for c in r['route_cases']}!=expected:
            raise ValueError('Expanded route case coverage mismatch')
        if not all(c['baseline_passed'] and c['detected'] for c in r['mutation_controls']):
            raise ValueError('Expanded judge mutation control failed')
        if r['mutation_controls']!=__import__('benchmarks.expanded_fixture',fromlist=['mutation_controls']).mutation_controls(data):
            raise ValueError('Missing or mismatched mutation controls')
        records[name]=r;commits.add(r['commit_sha'])
    if len(commits)>1: raise ValueError('Cannot combine different code revisions')
    categories=[]
    groups=[('all_routes',data['cases'])]
    for key in sorted({c['category'] for c in data['cases']}):
        groups.append((key,[c for c in data['cases'] if c['category']==key]))
    groups.extend((split+'_routes',[c for c in data['cases'] if c['split']==split])
                  for split in ('discovery','holdout'))
    for category,cases in groups:
        ids={c['id'] for c in cases};scores={}
        for engine in LABELS:
            states={c['id']:c['status'] for c in records.get(engine,{}).get('route_cases',())}
            scores[engine]=tally(states.get(c['id'],'unresolved') for c in cases)
        categories.append({'category':category,'cases':sorted(ids),'counts':scores,
            'rank_scope':'Native road import engines and supplied-transition algorithms ranked separately'})
    rings=[c for c in data['cases'] if c['exit_number'] is not None]
    exit_scores={}
    for engine in LABELS:
        values={c['id']:c['exit_status'] for c in records.get(engine,{}).get('route_cases',())}
        exit_scores[engine]=tally(values.get(c['id'],'not_supported' if engine in ('routingkit','pgrouting') else 'unresolved') for c in rings)
    categories.append({'category':'roundabout_exit_instructions','cases':[c['id'] for c in rings],
                       'counts':exit_scores,'rank_scope':'Authored simple-ring exit numbers only; no physical lane guidance'})
    trace_ids={c['id'] for c in data['cases'] if c['id'].split('/')[-1] in
               ('no_chained_turn','only_chained_turn','no_inside_via_reset','asymmetric_ring_exit_5','compound_no_only_detour')}
    trace_scores={};hashes={}
    expected_hashes={c['id']:hashlib.sha256(json.dumps(clean_trace(data,c)[1],sort_keys=True).encode()).hexdigest()
                     for c in data['cases'] if c['id'] in trace_ids}
    for engine in LABELS:
        traces=records.get(engine,{}).get('clean_traces',())
        values={c['case']:c['status'] for c in traces}
        if engine in records and (len(traces)!=len(trace_ids) or set(values)!=trace_ids):
            raise ValueError('Clean trace case coverage mismatch')
        for c in traces:
            if c['status']=='not_supported': continue
            digest=c['input_sha256']
            if digest!=expected_hashes[c['case']]:
                raise ValueError('GPS input differs from independently authored trace')
            if c['case'] in hashes and hashes[c['case']]!=digest:
                raise ValueError('Cross-engine GPS input mismatch')
            hashes[c['case']]=digest
        trace_scores[engine]=tally(values.get(cid,'not_supported' if engine in ('routingkit','pgrouting') else 'unresolved') for cid in sorted(trace_ids))
    categories.append({'category':'clean_observed_road_sequence','cases':sorted(trace_ids),
                       'counts':trace_scores,'rank_scope':'Output sequence only; live/batch temporal and per-fix interfaces differ'})
    # Publish category ranks only for complete cohorts with matching interfaces.
    for c in categories:
        c['rankings']={}
        cohorts={'native_road_import':tuple(LABELS)[:5],
                 'supplied_transition_algorithm':('routingkit','pgrouting')}
        if c['category']=='roundabout_exit_instructions': cohorts={'exit_instructions':tuple(LABELS)[:5]}
        if c['category']=='clean_observed_road_sequence': cohorts={}
        for cohort,names in cohorts.items():
            eligible=[e for e in names if e in records and not c['counts'][e]['unresolved'] and not c['counts'][e]['not_supported']]
            complete=len(eligible)==len(names)
            order=sorted(eligible,key=lambda e:c['counts'][e]['fail']) if complete else []
            ranks=[];last=None;rank=0
            for i,e in enumerate(order,1):
                failures=c['counts'][e]['fail']
                if failures!=last: rank=i;last=failures
                ranks.append({'engine':e,'rank':rank,'failures':failures})
            c['rankings'][cohort]={'ranks':ranks,'excluded':[e for e in names if e not in eligible],
                'complete_cohort':complete}
    issues=[]
    for engine,r in records.items():
        for c in r['route_cases']:
            if c['status']!='pass' or c.get('exit_status') in ('fail','unresolved'):
                issues.append({'engine':engine,'case':c['id'],'category':c['category'],'status':c['status'],
                    'issue':c['issue'],'expected_ways':c.get('allowed_ways'), 'actual_ways':c.get('actual_ways'),
                    'exit_status':c.get('exit_status'),'expected_exit':c.get('exit_number'),
                    'actual_exits':c.get('actual_exit_numbers'),'endpoint_check':c.get('endpoint_check')})
        for c in r['clean_traces']:
            if c['status'] in ('fail','unresolved'):
                issues.append({'engine':engine,**c,'category':'clean_observed_road_sequence'})
    return {'dataset_sha256':data['dataset_sha256'],'protocol':data['protocol'],
        'commit_sha':next(iter(commits),None),'executed_engines':list(records),'categories':categories,
        'issues':issues,'mutation_controls':next(iter(records.values()))['mutation_controls'] if records else [],
        'candidate_fix_diagnostics':records.get('drivemate',{}).get('clean_traces',[]),
        'not_supported':['Physical occupied-lane/spiral-roundabout lane guidance',
                         'Comparable live GPS loss and recovery controller',
                         'Voice timing and delivery','Real-road validated permissions','On-device efficiency'],
        'overall_rank':None,
        'overall_reason':'Coverage/interface differences do not support an overall navigation-system rank. Legal/critical route failures take precedence over any speed claim; no speed comparison is run.'}


def markdown(report):
    lines=['# Expanded competitor head-to-head evidence','',
        f"Revision: `{report['commit_sha']}`. Map: `{report['dataset_sha256']}`.",'',
        '92 shared route cases across four independently authored layouts: 46 discovery, 46 held out. '
        'Synthetic legality/reachability, not real-world route safety or optimal cost. Category subgroups overlap; do not sum them.','']
    for c in report['categories']:
        lines += ['## '+c['category'].replace('_',' '),'',
            '| Engine | Passed/total | Failed | Unresolved | Not supported |',
            '|---|---:|---:|---:|---:|']
        for engine,label in LABELS.items():
            s=c['counts'][engine]
            lines.append(f"| {label} | {s['pass']}/{s['total']} | {s['fail']} | {s['unresolved']} | {s['not_supported']} |")
        lines += ['',c['rank_scope']+'.']
        for cohort,r in c['rankings'].items():
            ranks=', '.join(f"{x['rank']}: {LABELS[x['engine']]} ({x['failures']} failed)" for x in r['ranks'])
            lines.append(f"{cohort.replace('_',' ')} category ranks: {ranks or 'unavailable'}.")
            if r['excluded']: lines.append('Unranked due to absent/unresolved/unsupported evidence: '+', '.join(LABELS[x] for x in r['excluded'])+'.')
        if not c['rankings']: lines.append('Sequence outcomes shown; no live-versus-batch controller rank.')
        lines.append('')
    lines+=['## Exact failing or unresolved scenarios','',
            '| Engine | Scenario | Outcome | Evidence diagnosis |','|---|---|---|---|']
    for i in report['issues']:
        status=i['status'] + ('; exit '+i['exit_status'] if i.get('exit_status') in ('fail','unresolved') else '')
        detail=i.get('issue') or ('Incorrect exit number' if i.get('exit_status')=='fail' else 'Exit output unresolved')
        lines.append(f"| {LABELS[i['engine']]} | {i.get('case')} | {status} | {detail.replace('|','/')} |")
    if not report['issues']: lines.append('| — | — | — | No failures in the executed subset |')
    lines+=['','Raw route/match responses are retained alongside each engine’s expanded.json. '
            'A legality mismatch identifies the violated authored case; vendor-internal root cause remains unproven until isolated. '
            'Endpoint divergence is unresolved interface evidence, not a proved illegal route.','',
            '## Defect-detection controls','',
            f"{sum(x['baseline_passed'] and x['detected'] for x in report['mutation_controls'])}/{len(report['mutation_controls'])} corrupt-output judge controls detected with clean baselines. "
            'These controls validate the independent judge; they do not inject faults into competitor binaries.','',
            '## Candidate per-fix diagnostics','']
    for c in report['candidate_fix_diagnostics']:
        rejected=c.get('rejected_clean_samples',())
        if rejected:
            counts=Counter(x['status'] for x in rejected)
            lines.append(f"- {c['case']}: {len(rejected)}/{c['sample_count']} clean fixes rejected ({dict(counts)}); full-sequence outcome: {c['status']}.")
    lines+=['','Conservative fix rejection is recorded separately from complete road-sequence reconstruction. '
            'External batch APIs do not expose equivalent streaming acceptance/controller evidence.','',
            '## Remaining boundaries','']
    lines += ['- '+x+': not supported by this shared benchmark.' for x in report['not_supported']]
    lines += ['', '**Overall winner: not established.** '+report['overall_reason'],'']
    return '\n'.join(lines)


def save(root,out):
    r=build(root)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'EXPANDED_SCORECARD.md').write_text(markdown(r))
    (out/'expanded_category_results.json').write_text(json.dumps(r,indent=2)+'\n')
    return r


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,default=Path('results/expanded-report'))
    args=ap.parse_args();save(args.input,args.output)
