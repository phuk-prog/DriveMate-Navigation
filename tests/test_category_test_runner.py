"""Integrity checks for the isolated category runner, not navigation claims."""
import json
import tempfile
from pathlib import Path
import unittest
from tools.category_test_runner import REGISTRY, validate, run_one

class CategoryRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(REGISTRY.read_text())
    def test_all_unit_files_assigned_exactly_once(self):
        self.assertEqual(validate(self.data)["category_count"],23)
        self.assertGreaterEqual(validate(self.data)["unit_test_files"],65)
    def test_missing_unit_is_rejected(self):
        changed=json.loads(json.dumps(self.data))
        changed["categories"][0]["test_files"].pop()
        with self.assertRaisesRegex(ValueError,"exactly one category"):
            validate(changed)
    def test_no_impl_lanes_must_be_not_run(self):
        lanes=next(c for c in self.data["categories"] if c["id"]=="lanes")
        with tempfile.TemporaryDirectory() as dest:
            self.assertEqual(run_one(lanes,Path(dest)),0)
            evidence=json.loads((Path(dest)/"lanes.json").read_text())
        self.assertEqual(evidence["status"],"NOT_RUN")
        self.assertEqual(evidence["unit_total"],0)
        self.assertIsNone(evidence["engine_rank"])
    def test_no_unit_categories_predeclare_engine_scores(self):
        for cat in self.data["categories"]:
            self.assertIsNone(cat["engine_rank"])
            self.assertIsNone(cat["navigation_score"])
