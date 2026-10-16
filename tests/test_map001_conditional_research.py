"""Synthetic UK local-time conditional probes; not legal-navigation validation."""
import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from benchmarks.map001_conditional_research import parse_source, source_evidence

UK=ZoneInfo("Europe/London")
def time(h,m=0):
    return datetime(2026,10,14,h,m,tzinfo=UK)

class ConditionalTimeSourceTests(unittest.TestCase):
    def test_glasgow_daytime_no(self):
        a=parse_source("no @ 07:00-19:00")
        self.assertFalse(a.active(time(6,59)))
        self.assertTrue(a.active(time(7)))
        self.assertTrue(a.active(time(18,59)))
        self.assertFalse(a.active(time(19)))
    def test_bracketed_glasgow_and_turn_rule(self):
        self.assertTrue(parse_source("no @ (07:00-19:00)").active(time(12)))
        self.assertEqual(parse_source("no_left_turn @ 07:00-19:00").value,"no_left_turn")
        self.assertFalse(parse_source("no_right_turn @ 07:00-19:00").active(time(20)))
    def test_belfast_overnight_delivery_not_general_permission(self):
        parsed=parse_source("delivery @ (18:00-11:00)")
        self.assertTrue(parsed.active(time(23)))
        self.assertTrue(parsed.active(time(3)))
        self.assertTrue(parsed.active(time(10,59)))
        self.assertFalse(parsed.active(time(11)))
        self.assertFalse(parsed.active(time(17,59)))
        evidence=source_evidence("belfast","144822061","way","motor_vehicle:conditional",
                               "delivery @ (18:00-11:00)")
        self.assertEqual(evidence["route_permission"],"NOT_GRANTED")
        self.assertFalse(evidence["actual_permission_and_current_order_verified"])
    def test_require_uk_aware_time(self):
        parsed=parse_source("no @ 07:00-19:00")
        with self.assertRaises(ValueError):parsed.active(datetime(2026,10,14,12))
        with self.assertRaises(ValueError):parsed.active(datetime(2026,10,14,12,tzinfo=timezone.utc))
    def test_unsupported_complex_and_calendar_conditions_remain_unknown(self):
        for raw in ("no @ (Mo-Fr 07:00-19:00)", "no @ sunrise-sunset",
                    "delivery @ 18:00-11:00; yes @ 11:00-18:00",
                    "yes @ PH", "no @ 25:00-26:00", "no @ 11:00-11:00"):
            with self.subTest(raw=raw),self.assertRaises(ValueError):parse_source(raw)


if __name__=="__main__":
    unittest.main()
