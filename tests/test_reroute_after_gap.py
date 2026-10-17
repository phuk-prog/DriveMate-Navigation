"""Rerouting waits for fresh good fixes after a GPS gap (owner-approved, 17 Oct 2026). Synthetic."""
import unittest

from engine.rerouting_controller import ReroutingController
from engine.routing import Route


class RerouteAfterGapTests(unittest.TestCase):
    def controller(self, **kw):
        c = ReroutingController(**kw)
        c.begin(Route(("unit-only",), 100, 10), now_ms=0)
        return c

    def off(self, c, t, reliable=True):
        return c.observe(timestamp_ms=t, now_ms=t, reliable=reliable, on_route=False)

    def test_original_behaviour_reroutes_straight_after_a_gap(self):
        c = self.controller()
        self.off(c, 1000)
        self.assertIsNone(self.off(c, 30000))
        self.assertIsNotNone(self.off(c, 31000))

    def test_after_a_gap_three_good_fixes_come_first(self):
        c = self.controller(post_gap_ms=5000)
        self.off(c, 1000)
        for t in (30000, 31000, 32000):
            self.assertIsNone(self.off(c, t))
        self.assertIsNone(self.off(c, 33000))
        self.assertIsNotNone(self.off(c, 34000))

    def test_weak_fixes_do_not_count_as_fresh(self):
        c = self.controller(post_gap_ms=5000, post_gap_reliable_samples=2)
        self.off(c, 1000)
        self.assertIsNone(self.off(c, 30000, reliable=False))
        self.assertIsNone(self.off(c, 31000))
        self.assertIsNone(self.off(c, 32000))
        self.assertIsNone(self.off(c, 33000))
        self.assertIsNotNone(self.off(c, 34000))

    def test_invalid_settings(self):
        for kw in ({"post_gap_ms": 0}, {"post_gap_ms": "5"}, {"post_gap_reliable_samples": 0}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                ReroutingController(**kw)


if __name__ == "__main__":
    unittest.main()
