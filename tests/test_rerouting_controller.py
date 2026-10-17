"""Synthetic lifecycle controls; these routes are unit-test payloads, not engine evidence."""
import unittest
from engine.routing import Route
from engine.rerouting_controller import ReroutingController

class ReroutingControllerTests(unittest.TestCase):
    def setUp(self):
        self.route=Route(('unit-only',),100,10)
        self.controller=ReroutingController()
        self.controller.begin(self.route,now_ms=0)

    def test_two_independent_observations_required(self):
        c=self.controller
        self.assertIsNone(c.observe(timestamp_ms=1000,now_ms=1000,reliable=True,on_route=False))
        self.assertIsNone(c.observe(timestamp_ms=1500,now_ms=1500,reliable=True,on_route=False))
        self.assertIsNotNone(c.observe(timestamp_ms=2000,now_ms=2000,reliable=True,on_route=False))

    def test_clock_rollback_rejects_without_poisoning_later_evidence(self):
        c=self.controller
        c.observe(timestamp_ms=1000,now_ms=1000,reliable=True,on_route=False)
        with self.assertRaises(ValueError):c.observe(timestamp_ms=900,now_ms=900,reliable=True,on_route=False)
        self.assertIsNotNone(c.observe(timestamp_ms=2000,now_ms=2000,reliable=True,on_route=False))

    def test_stop_rejects_late_result(self):
        c=self.controller
        c.observe(timestamp_ms=1000,now_ms=1000,reliable=True,on_route=False)
        token=c.observe(timestamp_ms=2000,now_ms=2000,reliable=True,on_route=False)
        c.stop(now_ms=2500)
        self.assertFalse(c.complete(token,self.route,now_ms=3000))
        self.assertIsNone(c.installed_route)
        self.assertFalse(c.active)

    def test_invalid_policy_or_sample_cannot_start_work(self):
        for kwargs in ({'minimum_off_route_samples':1},{'minimum_sample_gap_ms':0},{'cooldown_ms':True}):
            with self.assertRaises(ValueError):ReroutingController(**kwargs)
        with self.assertRaises(ValueError):self.controller.observe(timestamp_ms=True,now_ms=1,reliable=True,on_route=False)
        self.assertIsNone(self.controller.pending_request)

    def test_first_corroborating_sample_must_still_be_fresh_at_request_time(self):
        c=self.controller
        c.observe(timestamp_ms=1000,now_ms=1000,reliable=True,on_route=False)
        self.assertIsNone(c.observe(timestamp_ms=2000,now_ms=12000,reliable=True,on_route=False))
        self.assertIsNotNone(c.observe(timestamp_ms=12000,now_ms=12000,reliable=True,on_route=False))
