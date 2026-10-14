import copy
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from benchmarks.expanded_fixture import suite, legal_paths, judge, mutation_controls
from benchmarks.expanded_report import build
from benchmarks.expanded_comparison import clean_trace


def evidence():
    data=suite()
    rows=[]
    for c in data['cases']:
        paths=legal_paths(data,c)
        rows.append({**c,**judge(data,c,list(paths[0]) if paths else None,not paths),
                     'exit_status':'pass' if c['exit_number'] else None})
    traces=[{'case':c['id'],'status':'pass','input_sha256':hashlib.sha256(json.dumps(clean_trace(data,c)[1],sort_keys=True).encode()).hexdigest()} for c in data['cases']
            if c['id'].split('/')[-1] in ('no_chained_turn','only_chained_turn',
                                         'no_inside_via_reset','asymmetric_ring_exit_5','compound_no_only_detour')]
    return {'engine':'drivemate','fresh_execution':True,'dataset_sha256':data['dataset_sha256'],
            'protocol':data['protocol'],'commit_sha':'test-revision',
            'route_cases':rows,'clean_traces':traces,'mutation_controls':mutation_controls(data)}


class ExpandedReportTests(unittest.TestCase):
    def test_absent_competitors_cannot_earn_passes_or_rank(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            Path(temp,'expanded.json').write_text(json.dumps(evidence()))
            report=build(temp,expected_commit='test-revision')
            c=report['categories'][0]
            self.assertEqual(c['counts']['graphhopper']['pass'],0)
            self.assertEqual(c['counts']['graphhopper']['unresolved'],92)
            self.assertFalse(c['rankings']['native_road_import']['complete_cohort'])
            self.assertEqual(c['rankings']['native_road_import']['ranks'],[])
            self.assertIsNone(report['overall_rank'])

    def test_map_mismatch_and_missing_mutants_fail_closed(self):
        for mutate in ('map','mutations','coverage'):
            with self.subTest(mutate=mutate),tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
                row=evidence()
                if mutate=='map': row['dataset_sha256']='different'
                elif mutate=='mutations': row['mutation_controls']=[]
                else: row['route_cases'].pop()
                Path(temp,'expanded.json').write_text(json.dumps(row))
                with self.assertRaises(ValueError): build(temp,expected_commit='test-revision')

    def test_trace_input_mismatch_cannot_be_compared(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            a=evidence();b=copy.deepcopy(a);b['engine']='graphhopper'
            b['clean_traces'][0]['input_sha256']='changed'
            Path(temp,'a').mkdir();Path(temp,'b').mkdir()
            Path(temp,'a','expanded.json').write_text(json.dumps(a))
            Path(temp,'b','expanded.json').write_text(json.dumps(b))
            with self.assertRaises(ValueError): build(temp,expected_commit='test-revision')

    def test_previous_revision_evidence_cannot_be_scored(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            Path(temp,'expanded.json').write_text(json.dumps(evidence()))
            with self.assertRaises(ValueError): build(temp,expected_commit='new-revision')

    def test_uniformly_wrong_trace_hashes_cannot_be_scored(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            a=evidence();a['clean_traces'][0]['input_sha256']='uniformly-wrong'
            Path(temp,'expanded.json').write_text(json.dumps(a))
            with self.assertRaises(ValueError): build(temp,expected_commit='test-revision')
