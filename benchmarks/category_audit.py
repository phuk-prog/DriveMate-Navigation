"""Explain every executed check: exact category, numerator, denominator, issues.

Head-to-head categories only compare matching case IDs and accepted evidence.
Candidate-only synthetic stress cases are kept separate and cannot improve the
competitive rank of DriveMate. Route subgroups overlap; never add their totals.
"""
import json
from pathlib import Path
from collections import Counter
from benchmarks.head_to_head import BACKENDS
from benchmarks.benchmark_ranking import judge

ENGINE_NAMES={'osrm':'OSRM MLD','osrm-ch':'OSRM CH','valhalla':'Valhalla',
              'routingkit':'RoutingKit CH','pgrouting':'pgRouting'}
GUIDANCE=('DriveMate','GraphHopper','OSRM MLD','OSRM CH','Valhalla')
ROUTES=('urban_route','urban_wrong_turn_replan','via_way_ban_detour',
        'origin_inside_via_way','reverse_one_way_no_route',
        'ring_exit_1','ring_exit_2','ring_exit_3','ring_exit_4')
RINGS=tuple(x for x in ROUTES if x.startswith('ring_exit_'))
GPS=('urban_clean','legal_wrong_turn_reroute','via_way_ban_detour','ring_exit_4')
GROUPS=(('route_all','All routing and legal no-route outcomes',ROUTES),
        ('restrictions','One-way and via-way legal restrictions',ROUTES[2:5]),
        ('junction_routes','Urban junction and stateless replan paths',ROUTES[:2]),
        ('roundabout_routes','Roundabout road-path choices',RINGS))
VALID=('pass','fail','unknown','not tested')

def one(root,suffix):
    paths=[p for p in Path(root).rglob('*') if p.is_file() and p.as_posix().endswith(suffix)]
    if len(paths)>1:raise ValueError('Duplicate evidence path '+suffix)
    return json.loads(paths[0].read_text()) if paths else None

def tally(states):
    s=Counter(states)
    if set(s)-set(VALID):raise ValueError('Invalid result category: '+str(set(s)-set(VALID)))
    return {'passed':s['pass'],'failed':s['fail'],'unknown':s['unknown'],
            'not_tested':s['not tested'],'total':sum(s.values())}

def category(ident,title,caseids,mapping,method):
    vals={name:tally(mapping.get(name,{}).get(cid,'not tested') for cid in caseids)
          for name in BACKENDS}
    return {'id':ident,'name':title,'cases':list(caseids),'method':method,
            'counts':vals,'scope':'equivalent-synthetic-subset'}

def build_shared(root,comparison):
    rows=comparison['cases'];ids={x['case']:x for x in rows}
    if set(ids)!=set(ROUTES) or len(ids)!=len(rows):
        raise ValueError('Expected nine unique authored routing cases')
    mapping={name:{case['case']:case['results'].get(name,'not tested') for case in rows}
             for name in BACKENDS}
    shared=[category(ident,title,subset,mapping,'Independent expected route/no-route, identical source map')
            for ident,title,subset in GROUPS]
    gh=one(root,'whole_drive/reference/comparison.json')
    if not gh or gh.get('dataset_sha256')!=comparison.get('dataset_sha256'):
        raise ValueError('Missing paired candidate and GraphHopper evidence')
    other={}
    for doc in Path(root).rglob('comparison.json'):
        item=json.loads(doc.read_text())
        engine=item.get('engine')
        if engine in ENGINE_NAMES:
            if engine in other or item.get('dataset_sha256')!=comparison.get('dataset_sha256') or item.get('fresh_execution') is not True:
                raise ValueError('Duplicated/unverified external evidence '+engine)
            other[engine]=item
    pairs={r['case']:r for r in gh['routes']}
    numbered={name:{} for name in BACKENDS}
    observed={}
    for cid in RINGS:
        row=pairs[cid];observed[cid]={'expected':row['expected_exit_number']}
        if row['expected_exit_number']!=int(cid.rsplit('_',1)[1]):
            raise ValueError('Roundabout number source mismatch')
        for name,prefix in (('DriveMate','drivemate'),('GraphHopper','graphhopper')):
            status=row.get(prefix+'_exit_status')
            if status not in VALID[:3]:raise ValueError('Exit score not separately measured '+name)
            numbered[name][cid]=status
            observed[cid][name]=row.get(prefix+'_exit_number',row.get('graphhopper_exit_numbers') if name=='GraphHopper' else None)
        for engine,item in other.items():
            name=ENGINE_NAMES[engine]
            if name not in GUIDANCE:continue
            subset={x['case']:x for x in item['cases']}
            if cid not in subset:raise ValueError('Incomplete roundabout numbers '+name)
            value=subset[cid]
            status=value.get('exit_status')
            if status not in VALID[:3]:raise ValueError('Not an actual exit instruction: '+name)
            numbered[name][cid]='unknown' if value.get('route_status')=='unknown' else status
            observed[cid][name]=value.get('roundabout_exits')
    shared.append(category('roundabout_numbering','Roundabout correct exit number',RINGS,numbered,
                           'Actual separately reported exit ordinal, not merely a road route'))
    refs={x['case']:x for x in gh.get('batch_matches',())}
    if set(refs)!=set(GPS):raise ValueError('Incomplete clean GPS baseline traces')
    traced={name:{} for name in BACKENDS}
    for cid in GPS:
        for name,key in (('DriveMate','drivemate_online_status'),('GraphHopper','graphhopper_batch_status')):
            traced[name][cid]=refs[cid][key]
    for eng,doc in other.items():
        name=ENGINE_NAMES[eng]
        if name not in GUIDANCE:continue
        matches={x['case']:x for x in doc.get('batch_matches',())}
        if set(matches)!=set(GPS):raise ValueError('Incomplete shared GPS trace set '+name)
        for cid,entry in matches.items():
            if entry['expected_observed_ways']!=refs[cid]['expected_observed_ways']:
                raise ValueError('GPS ground truth mismatch '+name+':'+cid)
            traced[name][cid]=entry['status']
    shared.append(category('clean_gps','Clean GPS observed road sequences',GPS,traced,
                           'Four identical authored traces; batch/live protocol differs; NOT outage recovery'))
    one_junction=pairs.get('urban_route',{})
    sign=one_junction.get('graphhopper_turn_status')
    if sign in VALID[:3]:
        shared.append(category('turn_signs','Junction turn-sign instructions',('urban_route',),
                               {'GraphHopper':{'urban_route':sign}},
                               'Independently expected manoeuvre signs; only GraphHopper has explicit measured evidence'))
    return shared,observed,gh,other

def candidate(root):
    rows=[]
    def add(ident,name,total,failures,explanation='Synthetic DriveMate-only oracle'):
        if not isinstance(total,int) or total<1:raise ValueError('Missing denominator '+ident)
        issues=list(failures)
        bad=set(str(x) for x in issues)
        if len(bad)>total:raise ValueError('More failing cases than attempted '+ident)
        rows.append({'id':ident,'name':name,'passed':total-len(bad),
                     'failed':len(bad),'total':total,'failures':issues,'method':explanation})
    adv=one(root,'navigation_adversarial/report.json')
    if adv:
        for case in adv['checks']:
            n=case['category'];fail=case.get('failures',[])
            if n=='roundabout_geometry':
                add('roundabout_geometry','Generated roundabout exit paths',case['exit_cases'],
                    [f['case'] for f in fail if not str(f['case']).endswith(':extra')])
                add('roundabout_ambiguous','Ambiguous/non-simple ring suppression',case['unsupported_topologies'],
                    [f['case'] for f in fail if str(f['case']).endswith(':extra')])
            elif n=='multi_arm_junctions':
                legal=[];banned=[]
                for f in fail:
                    key=f['case'];arms,_,out=map(int,key.split(':'))
                    (banned if out==arms//2 else legal).append(key)
                add('junction_legal','Multi-arm legal junction choices',case['legal_turn_cases'],legal)
                add('junction_banned','Prohibited turn rejection',case['banned_turn_cases'],banned)
            elif n=='gps_corruption':
                add('gps_corrupt','Corrupt GPS observations rejected',case['fault_cases'],
                    [f['case'] for f in fail if not str(f['case']).endswith(':valid')])
                add('gps_restart','Valid GPS after corrupt fixes',case['valid_fix_controls'],
                    [f['case'] for f in fail if str(f['case']).endswith(':valid')])
            elif n=='independent_routing_oracle':
                add('routing_generated','Independent shortest-path oracle',case['route_executions'],
                    [str(f['case'])+':'+str(f['mode']) for f in fail])
            elif n=='compound_gps_recovery':
                add('recovery_compound','Repeated GPS loss and recovery',case['journey_cases'],
                    [f['case'] for f in fail])
    gps=one(root,'gps_expanded_validation.json')
    if gps:
        p=gps['projection']
        add('gps_projection','GPS geometry precision',p['cases'],[f['case'] for f in p['failures']])
        r=gps['roundabout_gps_journeys']
        add('gps_roundabout_journey','GPS-guided roundabout journeys',len(r),
            [x['exit'] for x in r if not x['passed']])
    recovery=one(root,'gps_recovery_expanded.json')
    if recovery:
        for key,label in (('hard_sweep','Adversarial GPS recovery'),('reachability_oracle','GPS recovery graph reachability')):
            data=recovery[key]
            add('gps_'+key,label,data['cases'],[x.get('case',i) for i,x in enumerate(data['failures'])])
        add('gps_ring_loss','Roundabout GPS-loss recovery',1,
            [] if recovery['ring_recovery']['passed'] else ['roundabout-recovery'])
    inst=one(root,'instruction_expanded_validation.json')
    if inst:
        a=inst['adversarial_sweep']
        add('instructions_streams','Instruction timing and delivery variations',a['cases'],
            [f['case'] for f in a['failures']])
        add('instructions_ring','Roundabout guidance after GPS outage',1,
            [] if inst['roundabout_replay']['passed'] else ['roundabout-instruction'])
    journey=one(root,'whole_drive/drivemate.json')
    if journey:
        add('whole_journeys','Complete journeys and reroutes',len(journey['cases']),
            [x['case'] for x in journey['cases'] if x['status']!='pass'])
    mutation=one(root,'navigation_mutation/report.json')
    if mutation:
        hard=mutation['hard_holdout']
        add('hard_holdout','Larger holdout graph / junction route decisions',
            hard['executed'],
            [r['case'] for r in hard['results'] if r['status']!='pass'],
            'Independent graph-route oracle on eight 64-node asymmetric graphs; routing algorithms tested separately')
        muts=mutation['mutations']
        add('mutation_sensitivity','Deliberately injected safety faults detected',
            muts['injected'],
            [r['case'] for r in muts['cases']
             if not r['injected_fault_detected'] or not r['baseline_correct']],
            'Benchmark self-test only: detection of intentionally sabotaged graph or routing inputs')
    unit=one(root,'unittest/per_test.json')
    if unit:
        tests=unit['tests']
        if unit['total_discovered']!=len(tests):raise ValueError('Incomplete method evidence')
        for name,counts in sorted(unit['categories'].items()):
            found=[x for x in tests if x['category']==name]
            if len(found)!=counts['total_discovered']:raise ValueError('Unit method counts inconsistent')
            errors=[x['test'] for x in found if x['status'] in ('fail','error','unexpected_success')]
            add('unit:'+name,'Regression methods: '+name,len(found),errors,
                'Each unittest method; skipped methods are separately disclosed')
            rows[-1]['skipped']=counts['skipped']
            rows[-1]['passed']=counts['passed']
            rows[-1]['failed']=counts['failed']
            rows[-1]['method_outcomes']=[{'test':x['test'],'status':x['status'],
                                      'detail':x.get('detail',x.get('reason'))} for x in found]
    if len({x['id'] for x in rows})!=len(rows):raise ValueError('Duplicate category')
    return rows

def rank_per_category(row):
    eligible=[(name,r) for name,r in row['counts'].items() if r['total'] and r['not_tested']==0]
    eligible.sort(key=lambda x:(-x[1]['passed'],x[1]['failed'],x[1]['unknown']))
    ranks={};last=None;pos=0
    for i,(name,r) in enumerate(eligible,1):
        key=(r['passed'],r['failed'],r['unknown'])
        if key!=last:pos=i;last=key
        ranks[name]=pos
    return ranks

def build(root,head):
    shared,ordinal,gh,other=build_shared(root,head)
    own=candidate(root)
    issue=[]
    for category in shared:
        for cid in category['cases']:
            for name,stats in category['counts'].items():
                if stats['not_tested']==stats['total']:continue
                source=next(x for x in head['cases'] if x['case']==cid) if cid in ROUTES else None
                if category['id'] in ('roundabout_numbering','clean_gps','turn_signs'):
                    if category['id']=='roundabout_numbering':
                        raw=gh if name in ('DriveMate','GraphHopper') else next(
                            (v for k,v in other.items() if ENGINE_NAMES[k]==name),None)
                        if name=='DriveMate': rec=next(x for x in gh['routes'] if x['case']==cid);status=rec['drivemate_exit_status']
                        elif name=='GraphHopper': rec=next(x for x in gh['routes'] if x['case']==cid);status=rec['graphhopper_exit_status']
                        elif raw: rec=next(x for x in raw['cases'] if x['case']==cid);status=rec['exit_status']
                        else:continue
                    elif category['id']=='clean_gps':
                        if name=='DriveMate': rec=next(x for x in gh['batch_matches'] if x['case']==cid);status=rec['drivemate_online_status']
                        elif name=='GraphHopper': rec=next(x for x in gh['batch_matches'] if x['case']==cid);status=rec['graphhopper_batch_status']
                        else:
                            raw=next((v for k,v in other.items() if ENGINE_NAMES[k]==name),None)
                            if not raw:continue
                            rec=next(x for x in raw['batch_matches'] if x['case']==cid);status=rec['status']
                    else: status=next(x for x in gh['routes'] if x['case']==cid)['graphhopper_turn_status'] if name=='GraphHopper' else 'not tested'
                else:status=source['results'].get(name,'not tested') if source else 'not tested'
                if status in ('fail','unknown'):
                    issue.append({'category':category['name'],'engine':name,'case':cid,
                                  'outcome':status,'expected':ordinal.get(cid,{}).get('expected') if category['id']=='roundabout_numbering'
                                    else source.get('expected_ways') if source else None,
                                  'note':'Inspect actual response and verify legality/map equivalence before modifying engine'})
    for row in own:
        for case in row['failures']:
            is_test_harness=row['id']=='mutation_sensitivity'
            issue.append({'category':row['name'],
                          'engine':'Benchmark validator' if is_test_harness else 'DriveMate',
                          'case':case,'outcome':'fail',
                          'note':('Fix mutation detector/coverage and rerun gate' if is_test_harness
                                  else 'Reproduce and repair the specific failing algorithmic behaviour; rerun category and regressions')})
    return {'classification':'Executed synthetic evidence only, not an overall real-road ranking',
            'shared_categories':shared,'category_ranks':{x['id']:rank_per_category(x) for x in shared},
            'drivemate_only_categories':own,'issues':issue,'routing_ranking':judge(head),
            'notes':['Overlapping route subgroups must not be summed','Regression methods differ from synthetic observations',
                     'No competitor credit for candidate-only evidence',
                     'A missing comparable result is not zero or a failure']}
def markdown(report):
    lines=['# DriveMate category-by-category navigation results','',
      'Figures are correct / attempted. Every untested capability is shown as a dash, not as a failure.',
      '',
      '| What the check tests | '+' | '.join(BACKENDS)+' |',
      '|---|'+'---:|'*len(BACKENDS)]
    for c in report['shared_categories']:
        def value(e):
            s=c['counts'][e]
            if s['not_tested']==s['total']:return '—'
            return str(s['passed'])+'/'+str(s['total'])+(' ('+str(s['failed'])+' FAIL)' if s['failed'] else '')+(' ('+str(s['unknown'])+' UNRESOLVED)' if s['unknown'] else '')
        lines.append('| '+c['name']+' | '+' | '.join(value(e) for e in BACKENDS)+' |')
    lines+=['','These categories overlap in places; they must **not** be added to obtain a larger sample count.',
             'Roundabout exit instructions are separately measured from roundabout road-path choices.',
             'Ranking: equal results share equal rank. There is no justified overall whole-navigation winner.',
             '',
             '## Per-category ranking of eligible engines','',
             '| Category | Rank among measured implementations |','|---|---|']
    for c in report['shared_categories']:
        ranks=report['category_ranks'][c['id']]
        ranked=sorted(ranks.items(),key=lambda v:(v[1],BACKENDS.index(v[0])))
        lines.append('| '+c['name']+' | '+(', '.join(str(i)+'= '+name for name,i in ranked) or 'Not comparable')+' |')
    lines+=['','## DriveMate-only synthetic and regression checks','',
            'These are not competitor test results. A skipped regression method is separate from failure.',
            '','| Check | Passed / attempted | Failures | Skipped |','|---|---:|---:|---:|']
    for c in report['drivemate_only_categories']:
        lines.append('| '+c['name']+' | '+str(c['passed'])+'/'+str(c['total'])+' | '+str(c['failed'])+
                     ' | '+str(c.get('skipped',0))+' |')
    lines+=['','## Every identified failed or unresolved case','',
             '| Outcome | Check | Engine | Case |','|---|---|---|---|']
    for i in report['issues']:
        lines.append('| **'+i['outcome'].upper()+'** | '+i['category']+' | '+i['engine']+' | '+str(i['case'])+' |')
    if not report['issues']:lines.append('| No reported failures/unresolved results in completed executed checks | — | — | — |')
    lines+=['','See category_results.json for recorded cases, counts, issue details and each category rank. '
             'The candidate artifact also includes results/unittest/per_test.json for every regression method. '
             'The existing 36-category planned backlog is not claimed as executed evidence.']
    return '\n'.join(lines)+'\n'
def save(report,folder):
    out=Path(folder);out.mkdir(parents=True,exist_ok=True)
    (out/'CATEGORY_SCORECARD.md').write_text(markdown(report))
    (out/'category_results.json').write_text(json.dumps(report,indent=2)+'\n')
