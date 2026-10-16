"""Rank only actually judged applicable reports; keep exclusions out of rankings.

Does not execute engines, grant access or manufacture a minimum-ten cohort.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def rank_applicable(reports,*,test_id,case_ids,map_sha256,oracle_sha256,road_source=None,historical=False):
    config=json.loads((ROOT/'config/dmn-expanded-validation-programme.json').read_text())
    if not historical and (not isinstance(road_source,dict) or road_source.get('kind')!='licensed_public_real_map' or road_source.get('map_sha256')!=map_sha256 or not all(road_source.get(k) for k in ('source_url','snapshot','attribution'))):
        raise ValueError('Future comparison requires a verified real-map source manifest; only GPS may be simulated')
    roster=['DMN']+[r['family'] for r in config['references']]
    if not case_ids or len(set(case_ids))!=len(case_ids):raise ValueError('Frozen unique cases required')
    ranked=[];excluded=[];seen=set()
    for r in reports:
        name=r['system']
        if name not in roster or name in seen:raise ValueError('Unknown/duplicate canonical engine family')
        seen.add(name)
        if (r['test_id']!=test_id or r['map_sha256']!=map_sha256 or r['oracle_sha256']!=oracle_sha256
                or [c['case_id'] for c in r['cases']]!=case_ids):raise ValueError('Different or incomplete frozen cohort')
        execution='actual_local_python' if name=='DMN' else 'actual_live_loopback'
        if r['execution']!=execution:raise ValueError('Actual supported execution evidence required')
        if not r.get('version'):raise ValueError('Version/configuration evidence required')
        unusable=[c for c in r['cases'] if c['outcome'] not in ('PASS','FAIL')]
        if unusable:
            excluded.append(dict(system=name,reason='Unsupported/unresolved/not-run cases prevent comparable judged cohort',cases=unusable));continue
        passed=sum(c['outcome']=='PASS' for c in r['cases'])
        ranked.append(dict(system=name,rank=None,passed=passed,failed=len(case_ids)-passed,score_out_of_ten=10*passed/len(case_ids),version=r['version'],cases=r['cases']))
    for name in roster:
        if name not in seen:
            reason=next((r.get('reason','No matching executed cohort supplied') for r in config['references'] if r['family']==name),'No matching executed cohort supplied')
            excluded.append(dict(system=name,reason=reason))
    ranked.sort(key=lambda r:(-r['score_out_of_ten'],r['system']))
    previous=None
    for i,r in enumerate(ranked,1):
        if r['score_out_of_ten']!=previous:rank=i
        r['rank']=rank;previous=r['score_out_of_ten']
    n=sum(r['system']!='DMN' for r in ranked);minimum=config['minimum_external_engines_per_competitive_cohort']
    return dict(test_id=test_id,classification='selection/re-ranking of supplied executed evidence, not a new navigation execution',formula=f'10 * passes / {len(case_ids)}; ties share rank',ranked=ranked,exclusions_audit=excluded,actual_applicable_external_count=n,minimum_external_target=minimum,minimum_ten_met=n>=minimum,comparison_status='MINIMUM_MET' if n>=minimum else 'EXPLORATORY_MINIMUM_TEN_NOT_MET')
