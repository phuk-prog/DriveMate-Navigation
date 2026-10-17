import unittest
from engine.instruction_cues import instruction_phase
def prompt(**extra):
    args=dict(distance_m=80,speed_mps=15,reliable_fix=True,
              on_correct_route=True,maneuver_verified=True,observation_age_ms=100)
    args.update(extra)
    return instruction_phase(**args)
class InstructionTimingTests(unittest.TestCase):
    def test_approach_and_turn_are_distinct(self):
        self.assertEqual(prompt(distance_m=70),"APPROACH")
        self.assertEqual(prompt(distance_m=150),"WAIT")
        self.assertEqual(prompt(distance_m=5),"NOW")
    def test_unreliable_evidence_withholds_instruction(self):
        for opt in ({"reliable_fix":False},{"on_correct_route":False},
                    {"maneuver_verified":False},{"observation_age_ms":5000}):
            self.assertEqual(prompt(**opt),"WITHHOLD")
    def test_no_duplicates_or_stationary_false_notice(self):
        self.assertEqual(prompt(distance_m=10,spoken_before=True),"ALREADY_GIVEN")
        self.assertEqual(prompt(distance_m=40,speed_mps=0),"WAIT")
    def test_nan_invalid(self):
        with self.assertRaises(ValueError):prompt(distance_m=float("nan"))
