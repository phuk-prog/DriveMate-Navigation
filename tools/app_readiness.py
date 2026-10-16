"""Evidence inventory for DMN app adoption; never averages away safety blockers."""
import argparse
import json
from pathlib import Path
from tools.validation_readiness import audit
ROOT=Path(__file__).resolve().parents[1]


def readiness():
    source=ROOT/'references/gps001-uk-topology-20261015.json'
    evidence=json.loads(source.read_text());uk=evidence['report'];comparisons=audit()
    gates=[
        dict(id='uk_coverage_regression',status='BLOCKED',reason='Seven backward-adjacent cases remain unresolved; no independent evidence closes this tradeoff',prior_correct=24,current_correct=uk['temporal_correct'],confident_wrong=uk['temporal_confident_wrong'],withheld=uk['temporal_withheld'],evidence=str(source.relative_to(ROOT)),ci_url=evidence['ci_url']),
        dict(id='source_backed_real_map_test_batches',status='INCOMPLETE',reason='Requested real-map/GPS batches not yet completed against independently justified source-backed expectations; historical invented-map controls do not fill this gate'),
        dict(id='ten_applicable_reference_cohort',status='INCOMPLETE',reason='No ten-engine shared real-map judged cohort exists; historical static executions are not a universal capability or shared cohort',historical_static_families=comparisons['actual_static_families'],minimum=10),
        dict(id='integrated_dmn_replay',status='INCOMPLETE',reason='Matching/progress/rerouting/guidance/arrival components have not been verified together in the app; caller-supplied assessments remain isolated research inputs'),
        dict(id='android_native_offline_lifecycle',status='UNVERIFIED',reason='Host Python offline namespace proof is not actual Android/native routing, permissions, background, stop/restart or failure recovery evidence'),
        dict(id='target_device_performance_and_long_runs',status='UNVERIFIED',reason='No frozen target-device budgets or measured phone/emulator lifecycle and sustained-run evidence; host synthetic-grid timings do not establish this'),
        dict(id='reversible_app_integration',status='NOT_IMPLEMENTED',reason='No verified app feature isolation, existing-navigation fallback or rollback/upgrade validation; production repository has not been modified')]
    return dict(classification='app-adoption readiness inventory; not a new engine test or certification',status='NOT_READY_FOR_LIVE_NAVIGATION',ready_for_live_navigation=False,ready_to_replace_existing_navigation=False,overall_score=None,interpretation='No aggregate score or competitor win overrides an unresolved critical gate. Prototype experimentation is not production readiness.',gates=gates,next_action='Complete executable real-map reference expansion and integrated replay; close each gate with actual source/run/artifact evidence before considering app adoption')


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();r=readiness()
    if a.output:
        if not a.output.resolve().is_relative_to((ROOT/'results').resolve()):raise ValueError('Output under results only')
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2))

if __name__=='__main__':main()
