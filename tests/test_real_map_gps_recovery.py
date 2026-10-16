"""Synthetic analytical scoring controls, not real-road/GNSS observations."""
import unittest
from benchmarks.real_map_gps_recovery import judge

class GPS003JudgeTests(unittest.TestCase):
    def test_clear_withholding_is_availability_failure(self):
        self.assertFalse(judge('MATCH', 'MATCHED', 'a', 'b', True)['passed'])
        self.assertFalse(judge('MATCH', 'AMBIGUOUS', None, 'b', True)['passed'])

    def test_noisy_claim_on_wrong_road_is_failure(self):
        self.assertFalse(judge('SAFE', 'MATCHED', 'a', 'b', True)['passed'])
        self.assertTrue(judge('SAFE', 'AMBIGUOUS', None, 'b', True)['passed'])

    def test_rejected_packet_must_not_replace_history(self):
        self.assertFalse(judge('REJECT', 'REJECTED', None, 'b', False)['passed'])
        self.assertTrue(judge('REJECT', 'REJECTED', None, 'b', True)['passed'])
