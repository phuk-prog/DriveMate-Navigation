"""Frozen streaming contract and evidence eligibility; synthetic, no field truth."""
import copy
import unittest
from benchmarks.gps_fault_batch import run_dmn, coverage, load_cases

class GpsFaultBatchTests(unittest.TestCase):
    def test_all_frozen_cases_execute_and_pass(self):
        report=run_dmn()
        self.assertEqual(len(report['cases']),16)
        self.assertEqual([c['case_id'] for c in report['cases']],[c['id'] for c in load_cases()])
        self.assertTrue(all(c['outcome']=='PASS' for c in report['cases']))
        self.assertTrue(all(e['passed'] for c in report['cases'] for e in c['events']))

    def test_other_interfaces_are_unranked_with_per_case_reasons(self):
        rows=coverage(run_dmn())['rows']
        self.assertEqual(len(rows),13)
        for row in rows[1:]:
            self.assertIsNone(row['rank'])
            self.assertIsNone(row['score_out_of_ten'])
            self.assertEqual(row['failed'],0)
            self.assertEqual(row['unsupported']+row['not_run'],16)
            self.assertTrue(all(c.get('reason') for c in row['cases']))

    def test_mismatched_or_incomplete_evidence_cannot_be_scored(self):
        report=run_dmn()
        for key,value in [('oracle_sha256','changed'),('execution','mock'),('test_id','GPS-001')]:
            changed=copy.deepcopy(report);changed[key]=value
            with self.assertRaises(ValueError):coverage(changed)
        changed=copy.deepcopy(report);changed['cases'].pop()
        with self.assertRaises(ValueError):coverage(changed)
        changed=copy.deepcopy(report);changed['cases'][0]['outcome']='UNSUPPORTED'
        with self.assertRaises(ValueError):coverage(changed)
