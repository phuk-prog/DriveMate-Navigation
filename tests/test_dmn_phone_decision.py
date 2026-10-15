"""DMN candidate measures cannot be promoted to whole Android app scores."""
import unittest
from pathlib import Path
from benchmarks.dmn_phone_decision import decide, COMPONENTS


class DMNDecisionTests(unittest.TestCase):
    def test_no_fake_phone_winner_with_no_evidence(self):
        x = decide()
        self.assertEqual(x["project"], "DMN")
        self.assertFalse(x["standalone_app_required"])
        self.assertFalse(x["production_app_modified"])
        self.assertEqual(x["phone_decision"], "PENDING_EVIDENCE_AND_USER_APPROVAL")
        self.assertIsNone(x["speed_evidence"]["overall_navigation_winner"])
        self.assertEqual(set(x["component_choice"]), set(COMPONENTS))

    def test_journey_counts_keep_unknown_not_exercised_separate(self):
        rows = [
            {"status": "unresolved", "components": {
                "native_routing": "pass", "gps_matching": "unresolved",
                "arrival": "pass", "roundabouts": "not_exercised"}},
            {"status": "fail", "components": {
                "native_routing": "pass", "gps_matching": "fail",
                "arrival": "unresolved", "roundabouts": "not_exercised"}}
        ]
        j = {"category": "DriveMate-native-full-GPS-journey-replay-on-real-English-roads",
             "source_snapshot": "2026-10-13",
             "scenario_count": 2, "pass": 0, "fail": 1,
             "unresolved": 1, "cases": rows}
        x = decide(j)["journey_evidence"]
        self.assertEqual(x["components"]["native_routing"]["pass"], 2)
        self.assertEqual(x["components"]["gps_matching"]["unresolved"], 1)
        self.assertEqual(x["components"]["roundabouts"]["attempted"], 0)
        self.assertEqual(x["components"]["arrival"]["pass"], 1)
        self.assertEqual(x["pass"], 0)
        j["pass"] = 1
        with self.assertRaises(ValueError):
            decide(j)

    def test_host_speed_only_and_unavailable_reference(self):
        speed = {"category": "real-English-roads-warm-http-speed",
                 "implementations": {
                     "native": {"complete": True, "passed_requests": 20,
                                "total_requests": 20, "p95_ms": 1.2},
                     "external": {"complete": False, "passed_requests": 0,
                                  "total_requests": 20, "p95_ms": None}}}
        x = decide(speed=speed)
        self.assertEqual(len(x["speed_evidence"]["eligible"]), 1)
        self.assertEqual(len(x["speed_evidence"]["excluded"]), 1)
        self.assertIsNone(x["speed_evidence"]["overall_navigation_winner"])

    def test_workflows_record_phone_decision(self):
        root = Path(__file__).resolve().parents[1] / ".github/workflows"
        for file in ("real-england-speed.yml", "real-england-journey.yml"):
            text = (root / file).read_text()
            self.assertIn("python -m benchmarks.dmn_phone_decision", text)
            self.assertIn("dmn-phone-decision.json", text)


if __name__ == "__main__":
    unittest.main()
