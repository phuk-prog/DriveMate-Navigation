"""Second "now" call, speed-based lead and the short progress bridge (owner-approved, 17 Oct 2026)."""
import unittest

from engine.instruction_cues import instruction_phase, lead_seconds_for
from engine.progress_estimator import ProgressEstimator


def phase(**extra):
    args = dict(distance_m=40, speed_mps=10, reliable_fix=True, on_correct_route=True,
                maneuver_verified=True, observation_age_ms=0)
    args.update(extra)
    return instruction_phase(**args)


class NowAndLeadTests(unittest.TestCase):
    def test_now_call_after_the_approach_call(self):
        self.assertEqual(phase(distance_m=40, now_given=False), "APPROACH")
        self.assertEqual(phase(distance_m=12, spoken_before=True, now_given=False), "NOW")
        self.assertEqual(phase(distance_m=5, spoken_before=True, now_given=True), "ALREADY_GIVEN")

    def test_original_single_call_unchanged(self):
        self.assertEqual(phase(distance_m=5, spoken_before=True), "ALREADY_GIVEN")

    def test_gates_still_withhold(self):
        self.assertEqual(phase(distance_m=12, now_given=False, reliable_fix=False), "WITHHOLD")
        self.assertEqual(phase(distance_m=12, now_given=False, observation_age_ms=4000), "WITHHOLD")

    def test_lead_by_speed(self):
        self.assertEqual(lead_seconds_for(10), 5.0)
        self.assertEqual(lead_seconds_for(20), 8.0)
        self.assertEqual(lead_seconds_for(31), 12.0)
        self.assertEqual(phase(distance_m=300, speed_mps=31, lead_seconds=lead_seconds_for(31)), "APPROACH")

    def test_progress_bridge_is_short(self):
        est = ProgressEstimator()
        self.assertIsNone(est.estimate(timestamp_ms=0))
        est.confirm(timestamp_ms=1000, along_m=100, speed_mps=10)
        self.assertEqual(est.estimate(timestamp_ms=3000), (120.0, 2000))
        self.assertIsNone(est.estimate(timestamp_ms=4500))
        est.reset()
        self.assertIsNone(est.estimate(timestamp_ms=1500))


if __name__ == "__main__":
    unittest.main()
