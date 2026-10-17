"""Evidence eligibility and complete frozen lifecycle replay, not device tests."""
import copy
import unittest
from benchmarks.rerouting_lifecycle_trial import run_dmn,coverage,ADDITIONAL

class ReroutingLifecycleTrialTests(unittest.TestCase):
    def test_frozen_and_adversarial_cohorts_pass_with_actual_planner(self):
        for path in (None,ADDITIONAL):
            r=run_dmn() if path is None else run_dmn(path)
            self.assertEqual(len(r['cases']),16 if path is None else 3)
            self.assertTrue(all(c['outcome']=='PASS' for c in r['cases']))
            self.assertTrue(all(s['passed'] for c in r['cases'] for s in c['events']))
            self.assertGreater(r['actual_core_route_calculations'],0)

    def test_other_controller_interfaces_are_not_mocked_passes(self):
        rows=coverage(run_dmn())['rows']
        self.assertEqual(len(rows),13)
        for row in rows[1:]:
            self.assertIsNone(row['rank'])
            self.assertIsNone(row['score_out_of_ten'])
            self.assertEqual(row['failed'],0)
            self.assertEqual(row['not_run']+row['unsupported'],16)
            self.assertTrue(all(c.get('reason') for c in row['cases']))

    def test_wrong_or_incomplete_evidence_is_not_scored(self):
        report=run_dmn()
        for key,value in [('oracle_sha256','wrong'),('execution','injected'),('test_id','GPS-002')]:
            changed=copy.deepcopy(report);changed[key]=value
            with self.assertRaises(ValueError):coverage(changed)
        changed=copy.deepcopy(report);changed['cases'].pop()
        with self.assertRaises(ValueError):coverage(changed)
