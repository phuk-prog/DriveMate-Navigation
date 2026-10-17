"""Contract tests: exercise register integrity, not real-road navigation."""
import json
import unittest
from copy import deepcopy
from tools.dmn_atomic_coverage import REGISTRY, validate

class AtomicCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(REGISTRY.read_text(encoding="utf-8"))
    def test_72_categories_in_12_domains_and_216_distinct_checks(self):
        self.assertEqual(validate(self.data), {"domains":12,"categories":72,"atomic_checks":216,
            "tested_in_this_suite":0,"out_of_ten_ranking":None,"check_status":"planned_not_run"})
    def test_no_missing_checks(self):
        altered=deepcopy(self.data)
        altered["categories"][0]["checks"].pop()
        with self.assertRaisesRegex(ValueError,"3 named"): validate(altered)
    def test_no_unsupported_extra_ranking(self):
        altered=deepcopy(self.data)
        altered["categories"][0]["checks"][0]["score"]=10
        with self.assertRaisesRegex(ValueError,"scores"): validate(altered)
    def test_no_fabricated_pass(self):
        altered=deepcopy(self.data)
        altered["categories"][0]["checks"][0]["status"]="passed"
        with self.assertRaisesRegex(ValueError,"invent"): validate(altered)
    def test_reject_duplicate_ids(self):
        altered=deepcopy(self.data)
        altered["categories"][1]["checks"][0]["id"]="NAV-001-A"
        with self.assertRaisesRegex(ValueError,"unstable ID"): validate(altered)
    def test_unique_group_coverage(self):
        altered=deepcopy(self.data)
        altered["categories"][6]["group"]=altered["categories"][0]["group"]
        with self.assertRaisesRegex(ValueError,"six categories"): validate(altered)

if __name__ == "__main__":
    unittest.main()
