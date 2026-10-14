import unittest
from benchmarks.gps_recovery_validation import history_matrix, judge_history_case, history_controls


class RecoveryHistoryMatrixTests(unittest.TestCase):
    def test_uncertain_history_cannot_earn_pass_with_guidance(self):
        row={'expected_status':'history_uncertain','expected_histories':2,
             'status':'history_uncertain','history_count':2,'guidance_available':False,
             'rejected_snapshot_advances':0,'history_inferred':True,
             'histories':[['up','uk'],['down','dk']],
             'expected_suffixes':[['up','uk'],['down','dk']]}
        self.assertTrue(judge_history_case(row))
        for key,value in (('guidance_available',True),('history_count',1),
                          ('rejected_snapshot_advances',1),('history_inferred',False),
                          ('histories',[['up','uk'],['invented','dk']])):
            self.assertFalse(judge_history_case(row|{key:value}))

    def test_controls_catch_corrupt_safety_results(self):
        rows=history_controls()
        self.assertEqual(len(rows),5)
        self.assertTrue(all(r['baseline_passed'] and r['detected'] for r in rows))

    def test_rotated_forks_retain_unknown_past_and_enforce_recovery_bounds(self):
        result=history_matrix()
        self.assertEqual(result['cases'],64)
        self.assertEqual(sum(r['split']=='holdout' for r in result['results']),32)
        self.assertEqual(result['failures'],[])
