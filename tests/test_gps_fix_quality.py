"""Pure GNSS input checks, NOT measured Android positioning tests."""
import math
import unittest
from gps.fix_quality import GPSFix, assess_fix

def f(t=1000, lat=53.48, lon=-2.24, accuracy=5.0, speed=9.0, bearing=90.0):
    return GPSFix(t, lat, lon, accuracy, speed, bearing)

class GPSFixQualityTests(unittest.TestCase):
    def test_normal_fix_is_accepted(self):
        self.assertEqual(assess_fix(f()).status, "VALID")
    def test_reject_invalid_latitude(self):
        with self.assertRaises(ValueError): f(lat=91)
    def test_reject_invalid_longitude(self):
        with self.assertRaises(ValueError): f(lon=-181)
    def test_reject_nan_accuracy(self):
        with self.assertRaises(ValueError): f(accuracy=math.nan)
    def test_reject_negative_speed(self):
        with self.assertRaises(ValueError): f(speed=-1)
    def test_reject_nonfinite_bearing(self):
        with self.assertRaises(ValueError): f(bearing=math.inf)
    def test_reject_out_of_range_bearing(self):
        with self.assertRaises(ValueError): f(bearing=360)
    def test_missing_heading_is_uncertain_not_pass(self):
        r=assess_fix(f(bearing=None))
        self.assertEqual((r.status,r.reason),("UNCERTAIN","heading_unavailable"))
    def test_low_accuracy_is_uncertain(self):
        self.assertEqual(assess_fix(f(accuracy=140)).status,"UNCERTAIN")
    def test_out_of_order_or_duplicate_time_rejected(self):
        self.assertEqual(assess_fix(f(t=1000), previous=f(t=1000)).reason,"duplicate_or_out_of_order")
        self.assertEqual(assess_fix(f(t=900), previous=f(t=1000)).status,"REJECTED")
    def test_stale_fix_rejected(self):
        self.assertEqual(assess_fix(f(t=1000), now_ms=12000).reason,"stale_timestamp")
    def test_future_fix_rejected(self):
        self.assertEqual(assess_fix(f(t=1000), now_ms=999).reason,"future_timestamp")
    def test_implausible_gnss_speed_rejected(self):
        self.assertEqual(assess_fix(f(speed=110)).reason,"implausible_reported_speed")
    def test_implausible_displacement_rejected(self):
        self.assertEqual(assess_fix(f(t=2000,lat=53.49),previous=f(t=1000)).reason,"implausible_position_jump")
    def test_uncertainty_avoids_false_jump_confidence(self):
        a=f(t=1000,accuracy=750, bearing=90)
        b=f(t=2000,lat=53.49,accuracy=750,bearing=90)
        self.assertEqual(assess_fix(b,previous=a).status,"UNCERTAIN")
    def test_realistic_small_motion_accepted(self):
        self.assertEqual(assess_fix(f(t=2000,lat=53.48001),previous=f(t=1000)).status,"VALID")
    def test_parameter_validation(self):
        with self.assertRaises(ValueError): assess_fix(f(),max_age_ms=-1)
        with self.assertRaises(ValueError): assess_fix(f(),max_plausible_speed_mps=0)

if __name__ == "__main__":
    unittest.main()
