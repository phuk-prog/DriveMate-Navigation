import unittest
from engine.traffic_evidence import traffic_decision
def decision(**extra):
    args=dict(age_seconds=30,speed_factor=.7,closure_state="OPEN",
              verified_closure=False,legal_detour_available=False)
    args.update(extra)
    return traffic_decision(**args)
class TrafficEvidenceTests(unittest.TestCase):
    def test_current_mapped_traffic_is_safely_reported(self):
        self.assertTrue(decision()["use_traffic_speed"])
        self.assertFalse(decision()["propose_reroute"])
    def test_stale_closure_fails_closed(self):
        self.assertEqual(decision(age_seconds=301,closure_state="CLOSED",
             verified_closure=True,legal_detour_available=True)["status"],"STALE")
    def test_unverified_closure_cannot_force_reroute(self):
        self.assertFalse(decision(closure_state="CLOSED",
                 legal_detour_available=True)["propose_reroute"])
    def test_verified_closure_still_requires_legal_detour(self):
        self.assertFalse(decision(closure_state="CLOSED",
                 verified_closure=True)["propose_reroute"])
        self.assertTrue(decision(closure_state="CLOSED",verified_closure=True,
                 legal_detour_available=True)["propose_reroute"])
    def test_bad_traffic_is_invalid(self):
        with self.assertRaises(ValueError):decision(speed_factor=float("nan"))
