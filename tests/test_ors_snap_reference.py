import unittest
from benchmarks.ors_snap_reference import snap_body, aligned_points
from benchmarks.navigation_trial import load_cases
from gps.fix_quality import GPSFix

class OrsSnapTests(unittest.TestCase):
    def test_request_preserves_lon_lat_order_and_radius(self):
        import json
        fixes = [GPSFix(*x) for x in load_cases()[0]['observations']]
        body = json.loads(snap_body(fixes))
        self.assertEqual(body['locations'][0], [fixes[0].longitude, fixes[0].latitude])
        self.assertEqual(body['radius'], 20)

    def test_null_slot_preserves_alignment(self):
        self.assertEqual(aligned_points({'locations':[None, {'location':[2,1]}, None, None]}),
                         [None, (1,2), None, None])

    def test_partial_output_is_not_aligned_by_guessing(self):
        self.assertEqual(aligned_points({'locations':[{'location':[2,1]}]}), [None]*4)

    def test_nonfinite_output_is_rejected(self):
        with self.assertRaises(ValueError):
            aligned_points({'locations':[{'location':[float('nan'),1]}]*4})
