"""Fail-closed audit of case-specific legal evidence for TURN-001 five no-route cases.

Read-only policy/evidence integrity check. Does NOT decide what UK road law is,
make network requests, modify the routing engine or convert OSM tags into truth.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "turn001-official-evidence.json"
CASE_IDS = {10558420, 13613008, 16644804, 4853555, 7615778}
ALLOWED_STATUS = {"UNVERIFIED", "PARTIAL", "CONFLICTED", "VERIFIED"}


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != 1:
        errors.append("Unsupported evidence register schema")
    sources = data.get("source_catalog", [])
    ids = [r.get("id") for r in sources]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate source ids")
    known_sources = set(ids)
    for source in sources:
        if not str(source.get("url", "")).startswith("https://"):
            errors.append(f"Non-HTTPS source URL {source.get('id')}")
        if source.get("exact_case_proof") is True and source.get("type") in (
            "official_portal", "general_service_guidance", "licensing_information"
        ):
            errors.append(f"Generic source falsely marked exact evidence: {source.get('id')}")
    cases = data.get("cases", [])
    case_ids = {row.get("relation_id") for row in cases}
    if len(cases) != len(case_ids) or case_ids != CASE_IDS:
        errors.append("Case ids must be exactly the five frozen TURN-001 relations, no duplicates")
    verified_count = 0
    for case in cases:
        rid = case.get("relation_id", "?")
        status = case.get("verification_status")
        if status not in ALLOWED_STATUS:
            errors.append(f"{rid}: unsupported status {status}")
        for source_id in case.get("candidate_sources", []):
            if source_id not in known_sources:
                errors.append(f"{rid}: unknown source {source_id}")
        if case.get("policy_change_authorized"):
            errors.append(f"{rid}: evidence register cannot authorize driving-rule modifications")
        ev = case.get("site_evidence", [])
        for item in ev:
            if item.get("source_id") not in known_sources:
                errors.append(f"{rid}: site evidence references unknown source")
            if not item.get("specific_location_match"):
                errors.append(f"{rid}: site evidence must match exact manoeuvre geometry")
        if status == "VERIFIED":
            verified_count += 1
            if not case.get("specific_legal_order_found") or not case.get("dated_site_signage_found"):
                errors.append(f"{rid}: VERIFIED requires dated legal order AND dated site signs")
            if len({e.get("source_id") for e in ev if e.get("specific_location_match")}) < 2:
                errors.append(f"{rid}: VERIFIED requires at least two distinct site-specific sources")
            if not any(e.get("evidence_type") == "final_legal_order" for e in ev):
                errors.append(f"{rid}: VERIFIED requires a final site-specific legal order")
            if not any(e.get("evidence_type") == "dated_signage" for e in ev):
                errors.append(f"{rid}: VERIFIED requires corroborated dated road signs")
            if not all(e.get("observation_date") and e.get("valid_at_review_date") is True
                       for e in ev):
                errors.append(f"{rid}: VERIFIED evidence must be dated and effective at review")
            if case.get("jurisdiction") == "UNCONFIRMED":
                errors.append(f"{rid}: VERIFIED requires confirmed highway authority")
    if data.get("verified_cases") != verified_count:
        errors.append("Declared verified_cases does not match case statuses")
    if data.get("permission_to_modify_engine") is not False:
        errors.append("Case evidence must never grant engine change permission")
    if not data.get("baseline", {}).get("frozen_map_sha256"):
        errors.append("Source map hash missing")
    return errors


def self_test(data: dict) -> None:
    assert validate(data) == [], "Baseline evidence manifest must validate"
    changed = copy.deepcopy(data)
    changed["cases"][0]["verification_status"] = "VERIFIED"
    changed["verified_cases"] = 1
    assert any("VERIFIED" in e for e in validate(changed)), "False verification must fail"
    changed = copy.deepcopy(data)
    changed["cases"][1]["policy_change_authorized"] = True
    assert any("driving-rule modifications" in e for e in validate(changed))
    changed = copy.deepcopy(data)
    changed["cases"][2]["site_evidence"] = [{"source_id": "missing", "specific_location_match": True}]
    assert any("unknown source" in e for e in validate(changed))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        for item in errors:
            print("INVALID:", item)
        return 1
    if args.self_test:
        self_test(data)
    print("PASS — five evidence records validated; independently verified:",
          data["verified_cases"], "/5; engine policy unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
