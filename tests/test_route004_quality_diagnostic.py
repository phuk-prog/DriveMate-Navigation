import json
from pathlib import Path
import tempfile
import unittest

from tools.route004_quality_diagnostic import diagnose


def evidence(distances):
    return {"test_id":"ROUTE-004","results":[
        {"engine":engine,"cases":[{"case_id":"X-reverse","outcome":"PASS","distance_m":distance}]}
        for engine,distance in distances]}


class Route004QualityDiagnosticTests(unittest.TestCase):
    def run_report(self, value):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"source.json"
            path.write_text(json.dumps(value))
            return diagnose(path)

    def test_large_spread_is_unresolved_not_ranked(self):
        report=self.run_report(evidence([("DMN",251.5),("OSRM",171.4),("BRouter",251.0)]))
        self.assertEqual(report["review_case_count"],1)
        self.assertEqual(report["quality_ranking"],"NOT_JUDGED")
        self.assertEqual(report["cases"][0]["status"],"UNRESOLVED_ROUTE_QUALITY_DIVERGENCE")
        self.assertFalse(report["cases"][0]["competitor_consensus_is_truth"])

    def test_small_spread_is_not_flagged(self):
        report=self.run_report(evidence([("DMN",100),("OSRM",105),("BRouter",110)]))
        self.assertEqual(report["review_case_count"],0)

    def test_failed_and_incomplete_cohorts_do_not_become_comparisons(self):
        value=evidence([("DMN",100),("OSRM",130),("BRouter",140)])
        value["results"][1]["cases"][0]["outcome"]="FAIL"
        report=self.run_report(value)
        self.assertEqual(report["review_case_count"],0)

    def test_wrong_source_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"ROUTE-004"):
            self.run_report({"test_id":"OTHER","results":[]})


if __name__ == "__main__":
    unittest.main()
