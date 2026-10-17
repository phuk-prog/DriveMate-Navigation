"""Arrival when the car stops near the destination (owner-approved, 17 Oct 2026). Synthetic."""
import unittest

from engine.arrival_controller import ArrivalController

DEST = (53.0, -2.0)


class StoppedArrivalTests(unittest.TestCase):
    def started(self, **kw):
        c = ArrivalController(**kw)
        return c, c.begin(DEST, route_length_m=500, now_ms=0)

    def obs(self, c, rev, t, *, reliable, on_route, remaining, speed, position=(53.00008, -2.0)):
        return c.observe(context_revision=rev, timestamp_ms=t, now_ms=t, position=position, accuracy_m=5,
                         reliable=reliable, on_route=on_route, remaining_m=remaining, speed_mps=speed)

    def test_stopped_after_on_route_progress_arrives(self):
        c, rev = self.started()
        self.obs(c, rev, 1000, reliable=True, on_route=True, remaining=45, speed=3)
        self.assertEqual(self.obs(c, rev, 2000, reliable=False, on_route=False, remaining=1e9, speed=0), "CANDIDATE")
        self.assertEqual(self.obs(c, rev, 3000, reliable=False, on_route=False, remaining=1e9, speed=0), "ARRIVED")

    def test_no_recent_progress_no_stopped_arrival(self):
        c, rev = self.started()
        self.obs(c, rev, 1000, reliable=True, on_route=True, remaining=45, speed=3)
        self.assertEqual(self.obs(c, rev, 30000, reliable=False, on_route=False, remaining=1e9, speed=0), "WITHHELD")

    def test_progress_far_from_the_end_does_not_count(self):
        c, rev = self.started()
        self.obs(c, rev, 1000, reliable=True, on_route=True, remaining=300, speed=10)
        self.assertEqual(self.obs(c, rev, 2000, reliable=False, on_route=False, remaining=1e9, speed=0), "WITHHELD")

    def test_stopped_too_far_from_the_destination(self):
        c, rev = self.started()
        self.obs(c, rev, 1000, reliable=True, on_route=True, remaining=45, speed=3)
        self.assertEqual(self.obs(c, rev, 2000, reliable=False, on_route=False, remaining=1e9, speed=0,
                                  position=(53.0005, -2.0)), "WITHHELD")

    def test_without_speed_the_original_rules_apply(self):
        c, rev = self.started()
        c.observe(context_revision=rev, timestamp_ms=1000, now_ms=1000, position=(53.00008, -2.0), accuracy_m=5,
                  reliable=True, on_route=True, remaining_m=45)
        self.assertEqual(c.observe(context_revision=rev, timestamp_ms=2000, now_ms=2000, position=(53.00008, -2.0),
                                   accuracy_m=5, reliable=False, on_route=False, remaining_m=1e9), "WITHHELD")

    def test_option_can_be_switched_off(self):
        c, rev = self.started(stopped_arrival=False)
        self.obs(c, rev, 1000, reliable=True, on_route=True, remaining=45, speed=3)
        self.assertEqual(self.obs(c, rev, 2000, reliable=False, on_route=False, remaining=1e9, speed=0), "WITHHELD")


if __name__ == "__main__":
    unittest.main()
