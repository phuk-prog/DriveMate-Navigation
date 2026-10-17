"""Use real retained reports; negative control changes are not new executions."""
import copy
import json
import unittest
from pathlib import Path
from benchmarks.applicable_cohort import rank_applicable,ROOT

class ApplicableTests(unittest.TestCase):
    def reports(self):return json.loads((ROOT/'references/junction001-executed-20261016.json').read_text())['reports']
    def rank(self,reports):
        r=self.reports()[0]
        return rank_applicable(reports,test_id=r['test_id'],case_ids=[c['case_id'] for c in r['cases']],map_sha256=r['map_sha256'],oracle_sha256=r['oracle_sha256'],historical=True)
    def test_only_six_actual_systems_appear_in_active_table(self):
        r=self.rank(self.reports())
        self.assertEqual(len(r['ranked']),6);self.assertEqual(r['actual_applicable_external_count'],5)
        self.assertFalse(r['minimum_ten_met']);self.assertEqual(len(r['exclusions_audit']),10)
        self.assertTrue(all(x['system'] not in {y['system'] for y in r['ranked']} for x in r['exclusions_audit']))
    def test_unsupported_engine_excluded_not_zero_scored(self):
        reports=copy.deepcopy(self.reports());r=next(r for r in reports if r['system']=='BRouter');r['cases'][0]['outcome']='UNSUPPORTED'
        result=self.rank(reports)
        self.assertNotIn('BRouter',[r['system'] for r in result['ranked']])
        self.assertIn('BRouter',[r['system'] for r in result['exclusions_audit']])
    def test_actual_failures_stay_ranked_and_specific(self):
        r=self.rank(self.reports());b=next(x for x in r['ranked'] if x['system']=='BRouter')
        self.assertEqual((b['passed'],b['failed'],b['score_out_of_ten']),(4,1,8))
    def test_mismatched_oracle_rejected(self):
        rs=copy.deepcopy(self.reports());rs[0]['oracle_sha256']='changed'
        with self.assertRaises(ValueError):self.rank(rs)

    def test_future_invented_map_cannot_enter_requested_comparison(self):
        r=self.reports()[0]
        with self.assertRaises(ValueError):
            rank_applicable(self.reports(),test_id=r['test_id'],case_ids=[c['case_id'] for c in r['cases']],map_sha256=r['map_sha256'],oracle_sha256=r['oracle_sha256'],road_source={'kind':'invented'})
