import copy
import json
from pathlib import Path
import tempfile
import unittest
from benchmarks.expanded_fixture import suite
from benchmarks.fault_comparison import scenarios, controls, PROTOCOL, clocked_input_hash
from benchmarks.fault_report import build, markdown


def record(engine='graphhopper'):
    data=suite();rows=scenarios(data)
    bases={r['base_case']:r for r in rows}
    return {'engine':engine,'fresh_execution':True,'dataset_sha256':data['dataset_sha256'],
        'protocol':PROTOCOL,'commit_sha':'test-revision','driving_side':data['driving_side'],
        'batch_interface':True,'judge_controls':controls(),'streaming_diagnostics':[],
        'cases':[{**{k:r[k] for k in ('id','base_case','split','fault','expected_ways','input_sha256')},
                  'status':'pass','actual_ways':r['expected_ways'],'issue':None} for r in rows],
        'clean_controls':[{'case':c,'status':'pass','input_sha256':r['baseline_input_sha256'],
                           'actual_ways':r['expected_ways']} for c,r in bases.items()]}


class FaultReportTests(unittest.TestCase):
    def test_absent_evidence_does_not_publish_an_all_pass_statement(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            text=markdown(build(temp,expected_commit='test-revision'))
            self.assertNotIn('All covered cases | Pass',text)
            self.assertIn('Batch evidence incomplete',text)

    def test_candidate_diagnostics_cannot_publish_false_success(self):
        data=suite();rows=scenarios(data)
        candidate=record('drivemate');candidate['batch_interface']=False;candidate['clean_controls']=[]
        for r in candidate['cases']: r['status']='not_supported';r['actual_ways']=None
        candidate['streaming_diagnostics']=[{'case':r['id'],'fault':r['fault'],
            'input_sha256':clocked_input_hash(r['samples']),'expected_ways':r['expected_ways'],
            'actual_ways':r['expected_ways'],'sequence_equal':True,'sample_count':len(r['samples']),
            'rejected_samples':[]} for r in rows]
        candidate['recovery_diagnostics']=[]
        for r in rows:
            if r['fault']!='compound' or not r['base_case'].endswith('asymmetric_ring_exit_5'): continue
            for variant,samples in (('clean_control',r['baseline_samples']),('compound',r['samples'])):
                candidate['recovery_diagnostics'].append({'case':r['base_case']+'/'+variant,
                    'input_sha256':clocked_input_hash(samples),'expected_ways':r['expected_ways'],
                    'actual_ways':r['expected_ways'],'status':'pass','snapshot_advances_on_rejection':0,
                    'sample_count':len(samples),'frames':[{'sample':i,'match_status':'matched','guidance_available':True} for i in range(len(samples))]})
        for change in ('stream_success','stream_input','recovery_success','recovery_frames'):
            with self.subTest(change=change),tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
                changed=copy.deepcopy(candidate)
                if change=='stream_success': changed['streaming_diagnostics'][0]['actual_ways']=[999]
                elif change=='stream_input': changed['streaming_diagnostics'][0]['input_sha256']='wrong'
                elif change=='recovery_success': changed['recovery_diagnostics'][0]['actual_ways']=[999]
                else: changed['recovery_diagnostics'][0]['frames']=[]
                Path(temp,'faults.json').write_text(json.dumps(changed))
                with self.assertRaises(ValueError): build(temp,expected_commit='test-revision')

    def test_incomplete_cohort_and_absent_execution_cannot_be_ranked(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            Path(temp,'faults.json').write_text(json.dumps(record()))
            result=build(temp,expected_commit='test-revision')
            all_faults=next(c for c in result['categories'] if c['category']=='batch_faults_all')
            self.assertEqual(all_faults['counts']['osrm']['unresolved'],80)
            self.assertEqual(all_faults['counts']['drivemate']['not_supported'],80)
            self.assertEqual(all_faults['ranks'],[])

    def test_uniform_input_change_stale_sha_missing_controls_and_fake_pass_rejected(self):
        for change in ('input','revision','baseline','mutants','fake_pass'):
            with self.subTest(change=change),tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
                row=record()
                if change=='input': row['cases'][0]['input_sha256']='wrong'
                elif change=='revision': row['commit_sha']='old'
                elif change=='baseline': row['clean_controls']=[]
                elif change=='mutants': row['judge_controls']=[]
                else: row['cases'][0]['actual_ways']=[999]
                Path(temp,'faults.json').write_text(json.dumps(row))
                with self.assertRaises(ValueError): build(temp,expected_commit='test-revision')

    def test_complete_batch_cohort_ties_without_live_candidate_rank(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            for engine in ('graphhopper','osrm','osrm-ch','valhalla'):
                directory=Path(temp,engine);directory.mkdir()
                (directory/'faults.json').write_text(json.dumps(record(engine)))
            result=build(temp,expected_commit='test-revision')
            self.assertEqual(len(result['categories'][0]['ranks']),4)
            self.assertTrue(all(r['rank']==1 for r in result['categories'][0]['ranks']))
