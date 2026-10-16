"""Strict comparable-cohort scorecard for synthetic JUNCTION-001."""
import json
from hashlib import sha256
from benchmarks.junction_trial import MAP, ORACLE, ROOT, VERSIONS, cases


def scoreboard(reports):
    ids=[c['id'] for c in cases()]
    roster=['DMN']+[r['name'] for r in json.loads((ROOT/'config/dmn-engine-first-programme.json').read_text())['reference_families']]
    supplied={}
    for r in reports:
        name=r['system']
        if name not in roster or name in supplied:raise ValueError('Unknown or duplicate system')
        if r['test_id']!='JUNCTION-001' or r['map_sha256']!=sha256(MAP.read_bytes()).hexdigest() or r['oracle_sha256']!=sha256(ORACLE.read_bytes()).hexdigest() or [c['case_id'] for c in r['cases']]!=ids:
            raise ValueError('Nonmatching cohort')
        expected='actual_local_python' if name=='DMN' else 'actual_live_loopback'
        if r['execution']!=expected or not r['instructions_enabled']:raise ValueError('Not actual maneuver execution')
        if any(c['outcome'] not in ('PASS','FAIL','UNRESOLVED','UNSUPPORTED','NOT_RUN') for c in r['cases']):raise ValueError('Unknown outcome')
        supplied[name]=r
    rows=[]
    for name in roster:
        r=supplied.get(name)
        reason=('No actual JUNCTION-001 execution supplied' if name in VERSIONS else
                'No app/native maneuver replay harness implemented' if name in ('OsmAnd','Organic Maps') else
                'No permitted automated replay interface established' if name=='Waze' else
                'No configured permitted access and identical-map interface; paid calls unauthorized')
        cs=r['cases'] if r else [dict(case_id=i,outcome='NOT_RUN',reason=reason) for i in ids]
        counts={s:sum(c['outcome']==s for c in cs) for s in ('PASS','FAIL','UNRESOLVED','UNSUPPORTED','NOT_RUN')}
        complete=counts['PASS']+counts['FAIL']==len(ids)
        rows.append(dict(system=name,rank=None,score_out_of_ten=10*counts['PASS']/len(ids) if complete else None,counts=counts,cases=cs))
    rows.sort(key=lambda r:(r['score_out_of_ten'] is None,-(r['score_out_of_ten'] or 0),r['system']))
    previous=None;rank=None
    for i,r in enumerate([r for r in rows if r['score_out_of_ten'] is not None],1):
        if previous!=r['score_out_of_ten']:rank=i
        r['rank']=rank;previous=r['score_out_of_ten']
    return dict(test_id='JUNCTION-001',classification='synthetic analytical maneuver semantics; not surveyed road truth',formula='10 * passed / 5; ties share rank; incomplete cohorts unranked',map_sha256=sha256(MAP.read_bytes()).hexdigest(),oracle_sha256=sha256(ORACLE.read_bytes()).hexdigest(),rows=rows)
