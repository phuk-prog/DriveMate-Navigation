"""Author-validated batch fault categories; streaming diagnostics stay separate."""
import json
import subprocess
from pathlib import Path
from benchmarks.expanded_fixture import suite
from benchmarks.expanded_comparison import LABELS
from benchmarks.expanded_report import tally
from benchmarks.fault_comparison import BATCH, FAULTS, PROTOCOL, scenarios, controls, clocked_input_hash, recovery_cases


def build(root,*,expected_commit=None):
    expected_commit=expected_commit or subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    data=suite();truth={r['id']:r for r in scenarios(data)};records={}
    bases={r['base_case']:r for r in truth.values()}
    for path in Path(root).rglob('faults.json'):
        record=json.loads(path.read_text());engine=record['engine']
        if engine not in LABELS or engine in records: raise ValueError('Unknown/duplicate fault evidence engine')
        if record.get('fresh_execution') is not True or record.get('commit_sha')!=expected_commit:
            raise ValueError('Fault evidence is not the current verified execution')
        if record.get('dataset_sha256')!=data['dataset_sha256'] or record.get('protocol')!=PROTOCOL or record.get('driving_side')!=data['driving_side']:
            raise ValueError('Fault evidence map/protocol/driving side mismatch')
        if record.get('batch_interface')!=(engine in BATCH): raise ValueError('Incorrect interface cohort')
        if record.get('judge_controls')!=controls(): raise ValueError('Fault judge controls missing or changed')
        if len(record['cases'])!=len(truth) or {r['id'] for r in record['cases']}!=set(truth):
            raise ValueError('Fault case coverage mismatch')
        baseline={r['case']:r for r in record['clean_controls']}
        if engine in BATCH:
            if len(record['clean_controls'])!=len(bases) or set(baseline)!=set(bases):
                raise ValueError('Missing clean controls for batch fault comparison')
            for name,r in baseline.items():
                if r['input_sha256']!=bases[name]['baseline_input_sha256']:
                    raise ValueError('Clean control input mismatch')
                if r['status']=='pass' and r['actual_ways']!=bases[name]['expected_ways']:
                    raise ValueError('False clean-control pass')
        elif baseline: raise ValueError('Unmatched interface cannot publish batch clean controls')
        for r in record['cases']:
            expected=truth[r['id']]
            for key in ('input_sha256','base_case','split','fault','expected_ways'):
                if r[key]!=expected[key]: raise ValueError('Fault input or independent truth differs')
            if engine not in BATCH and r['status']!='not_supported':
                raise ValueError('Unmatched streaming/algorithm interface cannot earn batch result')
            if r['status']=='pass' and r['actual_ways']!=expected['expected_ways']:
                raise ValueError('False fault-path pass')
            if engine in BATCH and baseline[r['base_case']]['status']!='pass' and r['status']!='unresolved':
                raise ValueError('Fault result requires passing same-protocol clean control')
        stream=record.get('streaming_diagnostics',[]);recovery=record.get('recovery_diagnostics',[])
        if engine!='drivemate' and (stream or recovery): raise ValueError('Candidate diagnostics on a reference record')
        if engine=='drivemate':
            if len(stream)!=len(truth) or {r['case'] for r in stream}!=set(truth):
                raise ValueError('Streaming diagnostic coverage mismatch')
            for r in stream:
                source=truth[r['case']]
                if r['input_sha256']!=clocked_input_hash(source['samples']) or r['expected_ways']!=source['expected_ways'] or r['fault']!=source['fault']:
                    raise ValueError('Streaming diagnostic input/truth mismatch')
                if r['sequence_equal']!=(r['actual_ways']==source['expected_ways']) or r['sample_count']!=len(source['samples']):
                    raise ValueError('False streaming diagnostic success/coverage')
                indices=[x['sample'] for x in r['rejected_samples']]
                if any(not isinstance(i,int) or isinstance(i,bool) or not 0<=i<r['sample_count'] for i in indices) or len(set(indices))!=len(indices):
                    raise ValueError('Invalid streaming rejected-fix index')
            expected_recovery={case:(source,samples) for case,source,samples in recovery_cases(data)}
            if len(recovery)!=len(expected_recovery) or {r['case'] for r in recovery}!=set(expected_recovery):
                raise ValueError('Recovery diagnostic coverage mismatch')
            for r in recovery:
                source,samples=expected_recovery[r['case']]
                if r['input_sha256']!=clocked_input_hash(samples) or r['expected_ways']!=source['expected_ways'] or r['sample_count']!=len(samples):
                    raise ValueError('Recovery diagnostic input/truth mismatch')
                if r['status'] not in ('pass','fail','unresolved'): raise ValueError('Invalid recovery diagnostic outcome')
                if r['status']=='pass' and (r['actual_ways']!=source['expected_ways'] or r['snapshot_advances_on_rejection']!=0):
                    raise ValueError('False recovery diagnostic success')
                frames=r['frames']
                if len(frames)>len(samples) or [f['sample'] for f in frames]!=list(range(len(frames))):
                    raise ValueError('Recovery frame indices differ from input')
                if r['status']=='pass' and (len(frames)!=len(samples) or any(f['guidance_available'] and f['match_status']!='matched' for f in frames)):
                    raise ValueError('Incomplete or untrusted recovery success')
        records[engine]=record
    groups=[('batch_clean_controls',sorted(bases))]+[('batch_faults_all',sorted(truth))]
    groups += [('batch_'+f,sorted(k for k,r in truth.items() if r['fault']==f)) for f in FAULTS]
    groups += [('batch_faults_'+s,sorted(k for k,r in truth.items() if r['split']==s)) for s in ('discovery','holdout')]
    categories=[]
    for category,ids in groups:
        counts={}
        for engine in LABELS:
            rows=records.get(engine,{})
            states=({r['case']:r['status'] for r in rows.get('clean_controls',())} if category=='batch_clean_controls'
                    else {r['id']:r['status'] for r in rows.get('cases',())})
            default='unresolved' if engine in BATCH else 'not_supported'
            counts[engine]=tally(states.get(cid,default) for cid in ids)
        complete=all(e in records and not counts[e]['unresolved'] and not counts[e]['not_supported'] for e in BATCH)
        ranks=[];last=None;rank=0
        if complete:
            for i,e in enumerate(sorted(BATCH,key=lambda e:counts[e]['fail']),1):
                if last!=counts[e]['fail']: rank=i;last=counts[e]['fail']
                ranks.append({'engine':e,'rank':rank,'failed':counts[e]['fail']})
        categories.append({'category':category,'cases':ids,'counts':counts,'ranks':ranks,
                           'complete_batch_cohort':complete})
    issues=[]
    for engine,record in records.items():
        for r in record['cases']+record['clean_controls']:
            if r['status'] in ('fail','unresolved'): issues.append({'engine':engine,**r})
    return {'commit_sha':expected_commit,'dataset_sha256':data['dataset_sha256'],'protocol':PROTOCOL,
        'executed_engines':list(records),'categories':categories,'issues':issues,'judge_controls':controls(),
        'streaming_diagnostics':records.get('drivemate',{}).get('streaming_diagnostics',[]),
        'recovery_diagnostics':records.get('drivemate',{}).get('recovery_diagnostics',[]),
        'overall_rank':None,'scope':'Batch road-sequence reconstruction only; no live GPS, lane or full-navigation rank'}


def markdown(report):
    lines=['# Matched batch GPS fault comparison','',
        f"Revision `{report['commit_sha']}`; map `{report['dataset_sha256']}`.",'',
        '80 synthetic fault cases (40 discovery, 40 held out), plus 20 clean controls per batch engine. '
        'All receive identical seven-decimal coordinates and declared 3m accuracy, with no clock. '
        'No measured sensor accuracy or live GPS recovery is claimed. Category subsets overlap.','']
    for c in report['categories']:
        lines+=['## '+c['category'].replace('_',' '),'',
            '| Engine | Passed/total | Failed | Unresolved | Not supported |',
            '|---|---:|---:|---:|---:|']
        for e,label in LABELS.items():
            n=c['counts'][e]
            lines.append(f"| {label} | {n['pass']}/{n['total']} | {n['fail']} | {n['unresolved']} | {n['not_supported']} |")
        lines+=['','Batch category ranks: '+(', '.join(f"{r['rank']}: {LABELS[r['engine']]}" for r in c['ranks']) or
                                             'withheld because the matched cohort is incomplete/unresolved')+'.','']
    lines+=['## Exact failed or unresolved cases','',
        '| Engine | Case | Outcome | Diagnosis |','|---|---|---|---|']
    for r in report['issues']:
        lines.append(f"| {LABELS[r['engine']]} | {r.get('id',r.get('case'))} | {r['status']} | {str(r.get('issue')).replace('|','/')} |")
    if not report['issues']:
        if all(e in report['executed_engines'] for e in BATCH):
            lines.append('| All executed batch engines | All covered cases | Pass | No mismatch in this subset |')
        else: lines.append('| Batch evidence incomplete | - | Unresolved | Missing executions are not passes |')
    lines+=['','API rejection or splitting is a failed complete reconstruction after a passing clean control. '
            'Unmappable geometry and runtime/transport errors remain unresolved. All raw responses are retained.','',
            '## DriveMate streaming matcher diagnostics','']
    rows=report['streaming_diagnostics']
    if rows:
        lines+=['| Fault | Expected sequence recovered | Traces with rejected fixes |','|---|---:|---:|']
        for f in FAULTS:
            selected=[r for r in rows if r['fault']==f]
            lines.append(f"| {f} | {sum(r['sequence_equal'] for r in selected)}/{len(selected)} | {sum(bool(r['rejected_samples']) for r in selected)} |")
    else: lines.append('Candidate streaming evidence unavailable.')
    for r in rows:
        if not r['sequence_equal']:
            lines.append(f"- Streaming mismatch {r['case']}: expected {r['expected_ways']}, accepted {r['actual_ways']}; rejected-fix details retained in JSON.")
    lines+=['','These are single streaming-matcher diagnostics, excluded from batch ranks. '
            'They do not rank live recovery controllers, guidance or voice.','',
            '## Paired candidate-only recovery-controller probes','',
            '| Case | Outcome | Expected accepted sequence | Actual accepted sequence |','|---|---|---|---|']
    for r in report['recovery_diagnostics']:
        lines.append(f"| {r['case']} | {r['status']} | {r['expected_ways']} | {r['actual_ways']} |")
    if not report['recovery_diagnostics']: lines.append('| Unavailable | Unresolved | - | - |')
    lines+=['','Twenty author paths across four layouts each have one clean control and four spatial-fault controller probes. '
            'Rejected fixes must not advance the trusted snapshot. This is candidate-only evidence, '
            'not an external whole-navigation or sensor-calibration comparison.','',
            f"Judge controls detected: {sum(r['baseline_passed'] and r['detected'] for r in report['judge_controls'])}/{len(report['judge_controls'])}. "
            'No proprietary code, engine binary or personal trace is copied into the candidate.','',
            '**Overall navigation winner: not established.** Legal route failures in the separate routing ledger '
            'remain higher priority than these trace outcomes. Large unseen gaps, junction ambiguity, physical '
            'sensor calibration, spiral lanes, device efficiency and spoken guidance remain outside this test.','']
    return '\n'.join(lines)


def save(root,out):
    result=build(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'GPS_FAULT_SCORECARD.md').write_text(markdown(result),encoding='utf-8')
    (out/'gps_fault_category_results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result
