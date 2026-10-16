"""Current adoption state must not be inferred from synthetic scores or names."""
import unittest
from tools.app_readiness import readiness

class AppReadinessTests(unittest.TestCase):
    def test_current_actual_evidence_blocks_live_adoption(self):
        r=readiness();self.assertFalse(r['ready_for_live_navigation'])
        self.assertFalse(r['ready_to_replace_existing_navigation']);self.assertIsNone(r['overall_score'])
        g=next(g for g in r['gates'] if g['id']=='uk_coverage_regression')
        self.assertEqual((g['prior_correct'],g['current_correct'],g['confident_wrong'],g['withheld']),(24,17,0,23))
        self.assertEqual(g['status'],'BLOCKED')
    def test_independent_truth_and_android_proof_are_unverified(self):
        gates={g['id']:g for g in readiness()['gates']}
        self.assertNotEqual(gates['source_backed_real_map_test_batches']['status'],'PASS')
        self.assertNotEqual(gates['android_native_offline_lifecycle']['status'],'PASS')
