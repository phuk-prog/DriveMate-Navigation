"""Zero-claim planned-coverage inventory for the owner-review DMN programme.

This is NOT a reference engine runner. Existing historical scores and artifacts live
on their original branches and must not be overwritten by this plan inventory.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "dmn-engine-first-programme.json"


def inventory(config: dict) -> dict:
    if config.get("status") != "proposed_pending_owner_decisions":
        raise ValueError("Only approved-as-proposal configuration can be summarized")
    refs = config.get("reference_families")
    cats = config.get("categories")
    if config.get("minimum_reference_families") != 10:
        raise ValueError("Confirmed programme minimum must remain ten")
    if not isinstance(refs, list) or len(refs) < config["minimum_reference_families"]:
        raise ValueError("Need at least ten reference families")
    if not isinstance(cats, list) or not cats or not all(isinstance(c, str) and c for c in cats):
        raise ValueError("Invalid or empty category list")
    if len(set(cats)) != len(cats):
        raise ValueError("Duplicate category")
    names = []
    for ref in refs:
        if not isinstance(ref, dict) or not isinstance(ref.get("name"), str) or not ref["name"]:
            raise ValueError("Invalid reference")
        if ref.get("selection") != "proposed" or ref.get("execution") != "not_run_under_new_programme":
            raise ValueError("This inventory cannot certify executed references")
        if any(field in ref for field in ("score", "rank", "passed", "failed")):
            raise ValueError("Proposed reference cannot have invented scores")
        names.append(ref["name"].casefold())
    if len(set(names)) != len(names):
        raise ValueError("Duplicate reference family")
    policy = config.get("evidence_policy")
    if not isinstance(policy, dict) or any(
        policy.get(k) is not v
        for k, v in {
            "score_unrun": False,
            "include_unknowns": True,
            "unknown_is_pass": False,
            "full_ranking_requires_comparable_complete_results": True,
            "provider_consensus_is_legal_truth": False,
            "no_unapproved_billable_requests": True,
            "no_unauthorized_automated_provider_collection": True,
        }.items()
    ):
        raise ValueError("Unsafe or missing evidence policy")

    return {
        "programme": "DMN engine-first",
        "status": "proposal_no_new_reference_executions",
        "candidate": config.get("primary_candidate"),
        "external_reference_families_minimum": config["minimum_reference_families"],
        "external_reference_families_proposed": len(refs),
        "categories_proposed": len(cats),
        "family_category_slots_proposed_not_test_cases": len(refs) * len(cats),
        "reference_families_executed_under_this_new_programme": 0,
        "reference_families": [
            {"name": r["name"], "status": "not_run", "category_scores": {c: None for c in cats}}
            for r in refs
        ],
        "overall_ranking": None,
        "historical_evidence": "Retained in original benchmark branches; not merged into this plan inventory",
        "note": "Slots are planning placeholders, NOT scenario denominators or tested/failed/unresolved route counts.",
    }


def main() -> None:
    cfg = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    print(json.dumps(inventory(cfg), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
