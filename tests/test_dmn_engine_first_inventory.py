"""Contract checks for a proposed reference portfolio; no engine is executed."""
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.dmn_engine_first_inventory import inventory, DEFAULT_CONFIG


class EngineFirstInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))

    def test_twelve_distinct_external_families_proposed_not_measured(self):
        result = inventory(self.config)
        self.assertEqual(result["external_reference_families_minimum"], 10)
        self.assertEqual(result["external_reference_families_proposed"], 12)
        self.assertEqual(result["categories_proposed"], 14)
        self.assertEqual(result["family_category_slots_proposed_not_test_cases"], 168)
        self.assertEqual(result["reference_families_executed_under_this_new_programme"], 0)
        self.assertIsNone(result["overall_ranking"])
        for engine in result["reference_families"]:
            self.assertEqual(engine["status"], "not_run")
            self.assertTrue(all(x is None for x in engine["category_scores"].values()))

    def test_more_than_twelve_allowed_and_minimum_enforced(self):
        data = deepcopy(self.config)
        data["reference_families"].append({"name": "Other permitted independent engine", "selection": "proposed", "execution": "not_run_under_new_programme"})
        self.assertEqual(inventory(data)["external_reference_families_proposed"], 13)
        data["reference_families"] = data["reference_families"][:9]
        with self.assertRaisesRegex(ValueError, "Need at least ten"):
            inventory(data)

    def test_google_and_waze_remain_unexecuted_and_unscored(self):
        result = inventory(self.config)
        refs = {r["name"]: r for r in result["reference_families"]}
        for name in ("Google Maps", "Waze"):
            self.assertEqual(refs[name]["status"], "not_run")
            self.assertTrue(all(score is None for score in refs[name]["category_scores"].values()))

    def test_provider_access_safeguards_required(self):
        data = deepcopy(self.config)
        data["evidence_policy"]["no_unauthorized_automated_provider_collection"] = False
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            inventory(data)

    def test_osrm_variants_do_not_count_twice(self):
        names = [r["name"] for r in self.config["reference_families"]]
        self.assertIn("OSRM", names)
        self.assertEqual(names.count("OSRM"), 1)

    def test_duplicate_family_fails(self):
        data = deepcopy(self.config)
        data["reference_families"].append(deepcopy(data["reference_families"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate reference"):
            inventory(data)

    def test_claiming_score_for_unrun_reference_fails(self):
        data = deepcopy(self.config)
        data["reference_families"][0]["score"] = 10
        with self.assertRaisesRegex(ValueError, "invented"):
            inventory(data)

    def test_claiming_executed_reference_fails(self):
        data = deepcopy(self.config)
        data["reference_families"][0]["execution"] = "passed"
        with self.assertRaisesRegex(ValueError, "cannot certify"):
            inventory(data)

    def test_unknown_as_pass_policy_fails(self):
        data = deepcopy(self.config)
        data["evidence_policy"]["unknown_is_pass"] = True
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            inventory(data)


if __name__ == "__main__":
    unittest.main()
