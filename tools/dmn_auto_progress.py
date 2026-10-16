"""Evidence-only DMN automatic category progress, reusing existing CI verdicts.

The owner has authorized moving through category TESTS automatically. This
process never edits navigation behaviour, infers signed road law, claims
external reference executions from units, or triggers app/APK operations.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path

from tools.category_test_runner import REGISTRY, validate

KNOWN_STATUSES = frozenset({"UNIT_PASS", "UNIT_FAIL", "NOT_RUN", "INFRA_FAILURE"})
FAILED = frozenset({"UNIT_FAIL", "INFRA_FAILURE"})


def load_progress(registry: Path, results: Path) -> dict:
    catalog = json.loads(registry.read_text(encoding="utf-8"))
    validate(catalog)
    entries = catalog["categories"]
    summary_path = results / "index.json"
    if not summary_path.is_file():
        raise ValueError("Missing source CI category index; cannot infer test results")
    index_bytes = summary_path.read_bytes()
    index = json.loads(index_bytes)
    original = index.get("results")
    if not isinstance(original, list) or len(original) != len(entries):
        raise ValueError("CI index does not cover every registered category")
    if [r.get("category") for r in original] != [e["id"] for e in entries]:
        raise ValueError("CI index order or identity differs from frozen category queue")

    rows: list[dict] = []
    blockers: list[dict] = []
    all_cases: list[dict] = []
    for order, (category, overview) in enumerate(zip(entries, original), start=1):
        label = category["label"]
        path = results / (category["id"] + ".json")
        if not path.is_file():
            raise ValueError("Case-level evidence missing for " + category["id"])
        record_bytes = path.read_bytes()
        record = json.loads(record_bytes)
        status = record.get("status")
        if status not in KNOWN_STATUSES:
            raise ValueError("Unrecognized result type for " + category["id"])
        if record.get("category") != category["id"] or overview.get("status") != status:
            raise ValueError("Index / individual category mismatch: " + category["id"])
        if record.get("engine_rank") is not None or record.get("navigation_score") is not None:
            raise ValueError("Unit tests cannot promote a competitive score")
        if status != "INFRA_FAILURE" and record.get("classification") != "UNIT_CONTRACT_ONLY":
            raise ValueError("Unqualified unit result: " + category["id"])
        if status == "NOT_RUN" and category["test_files"]:
            raise ValueError("Existing category tests were omitted: " + category["id"])
        if status in ("UNIT_PASS", "UNIT_FAIL"):
            if record.get("unit_total", 0) <= 0:
                raise ValueError("Run with zero actual cases: " + category["id"])
            counts = Counter(r["result"] for r in record["cases"])
            if set(counts) - {"PASS", "FAIL", "ERROR", "SKIP"}:
                raise ValueError("Unknown case verdict")
            for field, outcome in (("passed", "PASS"), ("failed", "FAIL"),
                                   ("errors", "ERROR"), ("skipped", "SKIP")):
                if counts[outcome] != record[field] or record[field] != overview[field]:
                    raise ValueError("Case count does not agree with index")
            if sum(counts.values()) != record["unit_total"]:
                raise ValueError("Incomplete per-case outcome list")
            all_cases.extend({"category":category["id"], "case_id":r["id"],
                              "result":r["result"],"detail":r.get("detail", "")[-600:]}
                             for r in record["cases"] if r["result"] in ("FAIL", "ERROR"))
        reason = ("UNIT_CONTRACT_COMPLETE_NOT_ROAD_OR_COMPETITOR_VERIFIED"
                  if status == "UNIT_PASS" else
                  "TEST_IMPLEMENTATION_MISSING" if status == "NOT_RUN" else
                  "BLOCKED_BY_FAILED_UNIT_OR_INFRASTRUCTURE")
        unit = {"order":order,"category":category["id"],"label":label,
                "unit_status":status,"unit_total":record.get("unit_total", 0),
                "passed":record.get("passed", 0),"failed":record.get("failed", 0),
                "errors":record.get("errors", 0),"skipped":record.get("skipped", 0),
                "scope":category["scope"],
                "evidence_sha256":sha256(record_bytes).hexdigest(),
                "research_status":reason,
                "independent_uk_road_truth":"NOT_ESTABLISHED_BY_UNIT_TEST",
                "live_reference_rank":"NOT_EXECUTED_BY_UNIT_TEST",
                "next_action":(
                    "Investigate recorded case failure, freeze fix and rerun applicable cohort"
                    if status in FAILED else
                    "Implement missing measurable tests without inventing road truth"
                    if status == "NOT_RUN" else
                    "Advance to next category test; retain real-road and live-reference gaps")}
        rows.append(unit)
        if status in FAILED or status == "NOT_RUN":
            blockers.append({"category":category["id"],"status":status,
                             "reason":reason,"unit_case_file":path.name})

    # Continue collecting the next category's independent test results even
    # after a failure. A failed earlier category is never promoted to verified.
    if not rows or rows[0]["category"] != "map_data":
        raise ValueError("Automated progression must begin at MAP-001")
    first_blocker = blockers[0]["category"] if blockers else None
    next_priority = first_blocker or rows[0]["category"]
    output = {
        "trial":"DMN-21-CATEGORY-AUTOMATIC-RESEARCH-QUEUE-1",
        "source_registry_sha256":sha256(registry.read_bytes()).hexdigest(),
        "source_ci_index_sha256":sha256(index_bytes).hexdigest(),
        "git_head":os.getenv("GITHUB_SHA"),
        "category_count":len(rows),"categories_executed":len(rows),
        "unit_contract_pass_categories":sum(r["unit_status"]=="UNIT_PASS" for r in rows),
        "failed_or_infrastructure_categories":sum(r["unit_status"] in FAILED for r in rows),
        "unimplemented_categories":sum(r["unit_status"]=="NOT_RUN" for r in rows),
        "failed_case_count":len(all_cases),
        "all_category_results_collected_sequentially":True,
        "automatic_next_test_enabled":True,
        "next_priority_category":next_priority,
        "next_category_independent_result_required":True,
        "category_queue":rows,"unresolved":blockers,
        "failures":all_cases,
        "evidence_levels":{
            "unit_contract":"VALIDATED_FROM_SAME_RUN_JSON",
            "verified_real_road_legality":"NOT_PROVEN_BY_THIS_QUEUE",
            "live_multi_engine_rank":"NOT_EXECUTED_BY_THIS_QUEUE",
            "gps_phone_field_accuracy":"NOT_EXECUTED_BY_THIS_QUEUE"},
        "guardrails":{
            "no_app_or_apk":True,"no_auto_merges":True,
            "no_permanent_engine_behavior_mutations":True,
            "no_silent_reference_engine_fixes":True,
            "no_score_for_missing_engines":True,
            "no_global_cross_category_ranking":True,
            "failure_is_not_pass":True},
    }
    return output


def write_progress(registry: Path, results: Path) -> dict:
    report = load_progress(registry, results)
    results.mkdir(parents=True, exist_ok=True)
    (results/"dmn-auto-progress.json").write_text(json.dumps(report,indent=2)+"\n")
    md = ["# DMN automatic 21-category test queue","",
          "All categories run in order with individually recorded, auditable results.",
          "Unit PASS is **not** evidence of independently lawful UK navigation or a live engine ranking.",
          "A failure is retained and gets priority, but other tests remain independently runnable.",
          "",
          "| Order | Engine category | Unit result | Cases | Next research state |",
          "|---:|---|---|---:|---|"]
    for row in report["category_queue"]:
        md.append(f"| {row['order']} | {row['label']} | {row['unit_status']} | "
                  f"{row['passed']}/{row['unit_total']} | {row['research_status']} |")
    md.extend(["",f"**Investigate first:** {report['next_priority_category']}",
               "",
               "Next actions require stronger frozen real-road truth and genuine comparable "
               "external references; missing data must remain UNKNOWN/NOT_JUDGED.",
               "No app, APK, release, merge, or automatic unsafe navigation change."])
    (results/"dmn-auto-progress.md").write_text("\n".join(md)+"\n")
    print(json.dumps({k:report[k] for k in (
        "trial","category_count","unit_contract_pass_categories",
        "failed_or_infrastructure_categories","unimplemented_categories",
        "next_priority_category")},indent=2),flush=True)
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--registry",type=Path,default=REGISTRY)
    args = p.parse_args()
    write_progress(args.registry,args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
