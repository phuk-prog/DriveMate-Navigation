"""Fail-closed automatic category progress and no false road-law ranking."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.category_test_runner import REGISTRY
from tools.dmn_auto_progress import load_progress, write_progress


def fixture():
    source=json.loads(REGISTRY.read_text())
    reports=[]
    for category in source["categories"]:
        reports.append({
            "category":category["id"],"label":category["label"],"scope":category["scope"],
            "status":"UNIT_PASS","unit_total":1,"passed":1,"failed":0,
            "errors":0,"skipped":0,"cases":[{"id":category["id"]+".fixture","result":"PASS"}],
            "classification":"UNIT_CONTRACT_ONLY",
            "engine_rank":None,"navigation_score":None,
            "independent_real_road_truth":False})
    return reports


def write_casefiles(root, rows):
    root.mkdir(parents=True,exist_ok=True)
    for row in rows:
        (root/(row["category"]+".json")).write_text(json.dumps(row)+"\n")
    index={"results":[{key:r[key] for key in
             ("category","label","status","unit_total","passed","failed","errors","skipped")}
            for r in rows],
           "classification":"Per-category unittest executions; NOT navigation engine competition",
           "category_count":len(rows),
           "unit_total":sum(r["unit_total"] for r in rows),
           "unit_passed":sum(r["passed"] for r in rows),
           "engine_ranking":None,"independent_real_road_truth":False}
    (root/"index.json").write_text(json.dumps(index)+"\n")


class AutoProgressTest(unittest.TestCase):
    def test_all_21_categories_run_in_exact_owner_queue_without_false_scores(self):
        rows=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            write_casefiles(path,rows)
            report=write_progress(REGISTRY,path)
            self.assertEqual(report["category_count"],21)
            self.assertEqual(report["unit_contract_pass_categories"],21)
            self.assertEqual(report["failed_or_infrastructure_categories"],0)
            self.assertEqual(report["category_queue"][0]["category"],"map_data")
            self.assertEqual(report["category_queue"][1]["category"],"legal_routing")
            self.assertEqual(report["category_queue"][-1]["category"],"reference_adapters")
            self.assertTrue(report["all_category_results_collected_sequentially"])
            self.assertFalse(report["guardrails"]["no_score_for_missing_engines"] is False)
            self.assertEqual(report["evidence_levels"]["verified_real_road_legality"],
                             "NOT_PROVEN_BY_THIS_QUEUE")
            self.assertTrue((path/"dmn-auto-progress.json").exists())
            self.assertTrue((path/"dmn-auto-progress.md").exists())

    def test_real_failure_survives_and_later_categories_still_progress(self):
        rows=fixture()
        rows[1].update(status="UNIT_FAIL",passed=0,failed=1,
                       cases=[{"id":"legal_routing.bad_turn","result":"FAIL",
                               "detail":"Rejected an illegal turn"}])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            write_casefiles(path,rows)
            report=load_progress(REGISTRY,path)
            self.assertEqual(report["next_priority_category"],"legal_routing")
            self.assertEqual(report["failed_case_count"],1)
            self.assertEqual(report["failures"][0]["result"],"FAIL")
            self.assertEqual(report["category_queue"][2]["unit_status"],"UNIT_PASS")
            self.assertEqual(report["failed_or_infrastructure_categories"],1)
            self.assertNotEqual(report["category_queue"][1]["research_status"],
                                "UNIT_CONTRACT_COMPLETE_NOT_ROAD_OR_COMPETITOR_VERIFIED")

    def test_missing_category_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            write_casefiles(p,fixture())
            (p/"legal_routing.json").unlink()
            with self.assertRaisesRegex(ValueError,"missing for legal_routing"):
                load_progress(REGISTRY,p)

    def test_missing_case_or_false_qualified_rank_is_rejected(self):
        rows=fixture()
        rows[0]["cases"]=[]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            write_casefiles(p,rows)
            with self.assertRaisesRegex(ValueError,"Case count"):
                load_progress(REGISTRY,p)
        rows=fixture()
        rows[0]["navigation_score"]=10
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            write_casefiles(p,rows)
            with self.assertRaisesRegex(ValueError,"cannot promote"):
                load_progress(REGISTRY,p)

    def test_tampered_source_index_does_not_continue(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            write_casefiles(p,fixture())
            index=json.loads((p/"index.json").read_text())
            index["results"].reverse()
            (p/"index.json").write_text(json.dumps(index))
            with self.assertRaisesRegex(ValueError,"order or identity"):
                load_progress(REGISTRY,p)


if __name__ == "__main__":
    unittest.main()
