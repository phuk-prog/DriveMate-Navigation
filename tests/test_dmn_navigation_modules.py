"""DMN granular navigation contract matrix — inventory, not measured navigation quality."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "config" / "dmn_navigation_modules.json"
CONFIG = ROOT / "config" / "dmn-engine-first-programme.json"


class ModuleCoverageContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text(encoding="utf-8"))
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_each_scoreboard_category_has_independent_modules(self):
        groups = self.data["summary_groups"]
        self.assertEqual([g["id"] for g in groups], self.config["categories"])
        self.assertTrue(all(len(g["modules"]) >= 3 for g in groups))
        self.assertGreaterEqual(sum(len(g["modules"]) for g in groups), 50)

    def test_each_module_has_isolated_unique_atomic_checks(self):
        seen_modules = set()
        for group in self.data["summary_groups"]:
            for module in group["modules"]:
                mid = module["id"]
                self.assertNotIn(mid, seen_modules)
                seen_modules.add(mid)
                self.assertEqual(module["contract_boundary"], "dmn." + mid)
                self.assertGreaterEqual(len(module["checks"]), 4)
                seen = set()
                for check in module["checks"]:
                    self.assertNotIn(check["id"], seen)
                    seen.add(check["id"])
                    self.assertEqual(check["outcome"], "NOT_RUN")
        self.assertGreaterEqual(sum(len(m["checks"]) for g in self.data["summary_groups"]
                                    for m in g["modules"]), 200)

    def test_unexecuted_inventory_cannot_create_fake_scores_or_failures(self):
        self.assertEqual(self.data["evidence_status_default"], "NOT_RUN")
        for group in self.data["summary_groups"]:
            for module in group["modules"]:
                self.assertFalse(any("score" in k or "passed" in k or "failed" in k
                                     for k in module))
                for check in module["checks"]:
                    self.assertNotIn("score", check)
                    self.assertEqual(check["outcome"], "NOT_RUN")

    def test_separate_speed_and_positioning_concerns(self):
        module_ids = {m["id"] for g in self.data["summary_groups"] for m in g["modules"]}
        for name in ("speed_heading", "speed_handling", "compute_latency", "traffic_eta",
                     "road_matching", "sensor_fusion", "turn_restrictions",
                     "lane_uncertainty", "arrival_side", "region_maps", "replanning"):
            self.assertIn(name, module_ids)


if __name__ == "__main__":
    unittest.main()
