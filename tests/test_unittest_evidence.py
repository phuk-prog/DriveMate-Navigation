"""Unittest evidence categories: totals must reflect method-level statuses."""
import unittest
from tools.unittest_evidence import category,summarise

class UnittestEvidenceTests(unittest.TestCase):
    def test_mapped_named_subsystems(self):
        self.assertEqual(category('test_gps_matching.GpsMatchingTests.test_outlier'),
                         'GPS positioning and matching')
        self.assertEqual(category('test_roundabouts.RoundaboutTests.test_ring'),
                         'Roundabouts and exit guidance')
        self.assertEqual(category('test_lane_guidance.LaneTests.test_markings'),
                         'Lane indications and connectivity')
    def test_status_counts_do_not_promote_skipped_to_pass(self):
        rows=[{'test':'a','category':'Roundabouts and exit guidance','status':'pass'},
              {'test':'b','category':'Roundabouts and exit guidance','status':'fail'},
              {'test':'c','category':'Roundabouts and exit guidance','status':'skipped'}]
        s=summarise(rows)['Roundabouts and exit guidance']
        self.assertEqual((s['passed'],s['failed'],s['skipped'],s['total_discovered']),(1,1,1,3))
    def test_unfinished_test_rejected(self):
        with self.assertRaises(ValueError):
            summarise([{'test':'x','category':'GPS','status':'running'}])
if __name__=='__main__':unittest.main()
