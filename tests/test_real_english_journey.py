"""A first executable contract for the native+GPS real-road journey scorecard."""
import unittest
from pathlib import Path
from benchmarks.real_english_journey import replay_case
from benchmarks.whole_drive import prepared


class RealEnglishJourneyContractTests(unittest.TestCase):
    def test_simulated_journey_is_separate_from_live_device_claims(self):
        p = prepared()
        r = replay_case(p, "synthetic-contract", "osm:1", "osm:4")
        self.assertEqual(r["routing_backend"], "compiled_cpp_via_native_adapter")
        self.assertEqual(r["fix_source"], "simulated_from_public_OSM_geometry")
        self.assertIn(r["status"], ("pass", "fail", "unresolved"))
        self.assertIn("arrival", r["components"])
        self.assertIn("native_routing", r["components"])

    def test_real_road_workflow_writes_inspectable_journey_result(self):
        wf = (Path(__file__).resolve().parents[1] /
              ".github/workflows/real-england-speed.yml").read_text()
        self.assertIn("python -m benchmarks.real_english_journey", wf)
        self.assertIn("results/real-england/journeys.json", wf)


if __name__ == "__main__":
    unittest.main()
