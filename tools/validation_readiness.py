"""Audit programme readiness; this does not execute or certify routing engines."""
import argparse
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'config/dmn-expanded-validation-programme.json'


def audit(config=None,*,cohort_reports=None,cohort_spec=None):
    c=json.loads(CONFIG.read_text()) if config is None else config
    refs=c['references'];names=[r['family'] for r in refs]
    if len(names)!=len(set(names)) or any(n in ('DMN','OSRM CH','OSRM MLD') for n in names):raise ValueError('Distinct external canonical families required')
    target=c['minimum_external_engines_per_competitive_cohort']
    if type(target) is not int or target<10:raise ValueError('Minimum ten external references required')
    selected=[r for r in refs if r['target_ten']]
    if len(selected)<target:raise ValueError('Candidate roster below minimum')
    original=json.loads((ROOT/'config/dmn-engine-first-programme.json').read_text())['reference_families']
    if not {r['name'] for r in original}<=set(names):raise ValueError('Original families must remain in historical/exclusion audit')
    actual={}
    for r in refs:
        if r['execution_status']=='EXECUTED_STATIC_ROUTING':
            path=(ROOT/r['evidence']).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file():raise ValueError('Missing execution evidence')
            report=json.loads(path.read_text());engine=next((x for x in report.get('reports',[report.get('report',{})]) if x.get('system')==r['family']),None)
            if not engine or engine['execution'] not in ('actual_live_loopback','actual_dotnet_source_build_and_route_calculation','actual_packaged_cli_import_and_route_calculation') or not engine['cases']:raise ValueError('No actual reference execution in cited evidence')
            actual[r['family']]=dict(family=r['family'],source_sha=report['run_sha'],ci_url=report['ci_url'],scope=engine['test_id']+' actual routing integration only; not shared real-map or GPS-quality cohort',quality_score=None)
        elif r['execution_status']!='NOT_RUN':raise ValueError('Unrecognized execution claim')
    if c['scale_policy']['executed_generated_variants_under_this_revision']!=0:raise ValueError('No million-case execution evidence exists for this revision')
    if len({b['id'] for b in c['batches']})!=len(c['batches']) or any(not b['checks'] for b in c['batches']):raise ValueError('Explicit unique batch checks required')
    cohort=None
    if cohort_reports is not None or cohort_spec is not None:
        if cohort_reports is None or not isinstance(cohort_spec,dict) or cohort_spec.get('historical'):
            raise ValueError('Actual common real-map cohort required; historical executions cannot fill it')
        from benchmarks.applicable_cohort import rank_applicable
        cohort=rank_applicable(cohort_reports,**cohort_spec)
    return dict(classification='capability/evidence audit only; not navigation test outcomes',minimum_external_target=target,actual_static_families=len(actual),candidate_execution_target_met=len(actual)>=target,ten_engine_requirement_met=bool(cohort and cohort['minimum_ten_met']),shared_real_map_cohort_status=cohort['comparison_status'] if cohort else 'NO_EXECUTED_COMMON_COHORT_SUPPLIED',actual_prior_static_executions=list(actual.values()),candidate_target_families=[r['family'] for r in selected],active_cohort_policy=c['selection_policy']['active_comparison'],excluded_from_active_comparisons=[dict(family=r['family'],reason=r['reason']) for r in refs if r['execution_status']=='NOT_RUN'],new_generated_variants_executed=0,batch_count=len(c['batches']),external_execution_this_audit=0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();r=audit()
    if a.output:
        if not a.output.resolve().is_relative_to((ROOT/'results').resolve()):raise ValueError('Output must be under results')
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2))

if __name__=='__main__':main()
