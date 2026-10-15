"""DMN adaptive study: turn reproducible anomalies into distinct regression-test proposals.

No navigation is executed here. Nothing is silently marked pass, or written to
GitHub. Reviewed proposals become canonical tests in later changes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "config/dmn-atomic-test-matrix.json"
BLOCKED_KEYS = {"latitude", "longitude", "lat", "lon", "gps_trace", "device_id",
                "phone_number", "email", "home_address", "work_address",
                "imei", "personal_route", "user_id", "raw_trace"}
SOURCE_KINDS = {"public_nonpersonal", "synthetic_over_public_roads",
                "historical_aggregate", "manual_nonpersonal", "fixture_only"}
OUTCOMES = {"PASS", "FAIL", "UNKNOWN", "UNSUPPORTED", "NOT_RUN", "NOT_COMPARABLE"}
SIGNALS = {"wrong_route", "legality_dispute", "wrong_road", "gps_loss",
           "bad_speed", "wrong_instruction", "wrong_lane", "bad_arrival",
           "reroute_problem", "offline_failure", "map_gap", "coverage_gap",
           "provider_disagreement", "flaky", "slow_response", "resource_spike",
           "unexpected_behavior", "new_capability", "boundary_case"}
PRIORITY_SIGNALS = {"wrong_route", "legality_dispute", "wrong_road",
                    "wrong_instruction", "wrong_lane", "bad_arrival"}


def _non_personal(value):
    if isinstance(value, dict):
        if any(str(k).lower() in BLOCKED_KEYS for k in value):
            raise ValueError("Raw personal/sensor trace fields are forbidden in public discovery")
        for val in value.values():
            _non_personal(val)
    elif isinstance(value, list):
        for item in value:
            _non_personal(item)
    elif isinstance(value, str):
        if len(value) > 3000:
            raise ValueError("Use a bounded description, not a raw driving trace")
        if re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", value, re.I):
            raise ValueError("Personal contact information is not allowed")


def _matrix_ids(matrix):
    cats = matrix["categories"]
    return ({c["id"]: c for c in cats},
            {ch["id"] for c in cats for ch in c["checks"]},
            {d["name"] for d in matrix["domains"]})


def _require_text(v, field):
    if not isinstance(v, str) or not v.strip():
        raise ValueError("Required nonblank field: " + field)
    return v.strip()


def _candidate(obs, cats, checks, groups, source):
    if not isinstance(obs, dict):
        raise ValueError("Observation must be an object")
    outcome = _require_text(obs.get("outcome"), "outcome")
    signal = _require_text(obs.get("signal"), "signal")
    if outcome not in OUTCOMES or signal not in SIGNALS:
        raise ValueError("Unknown outcome or anomaly signal")
    # A clean PASS alone is not a reason to invent more tests.
    if outcome == "PASS" and signal not in {
        "flaky", "provider_disagreement", "slow_response",
        "resource_spike", "boundary_case", "unexpected_behavior"
    }:
        return None
    if outcome == "NOT_RUN" and signal not in {"coverage_gap", "new_capability"}:
        return None
    parent = obs.get("category_id")
    new_title = obs.get("proposed_category")
    if parent is None:
        _require_text(new_title, "proposed_category")
        group = _require_text(obs.get("proposed_group"), "proposed_group")
        # New groups are permitted as *proposals*. Do not edit existing baseline IDs.
        extension = True
    else:
        if parent not in cats:
            raise ValueError("Unknown category; propose an extension instead")
        if new_title is not None:
            raise ValueError("Use either an existing category or a proposed new category")
        group = cats[parent]["group"]
        extension = False
    check_id = obs.get("check_id")
    if check_id is not None and (
            parent is None or check_id not in checks or
            check_id not in {c["id"] for c in cats[parent]["checks"]}):
        raise ValueError("An existing check must belong to the selected category")
    reproducible = _require_text(obs.get("reproduction"), "reproduction")
    expectation = _require_text(obs.get("expected"), "expected")
    actual = _require_text(obs.get("observed"), "observed")
    signature = _require_text(obs.get("failure_signature"), "failure_signature")
    case_id = _require_text(obs.get("case_id"), "case_id")
    oracle = obs.get("oracle")
    if outcome == "FAIL" and (not isinstance(oracle, str) or not oracle.strip()):
        raise ValueError("FAIL requires an independent or explicitly scoped oracle; otherwise UNKNOWN")
    reference = _require_text(obs.get("evidence_ref"), "evidence_ref")
    if not (reference.startswith("https://github.com/") or
            reference.startswith("https://www.openstreetmap.org/") or
            reference.startswith("https://www.gov.uk/")):
        raise ValueError("Use an auditable public evidence link, not a private location source")
    # Same problem across multiple reruns must resolve to one stable test proposal.
    identity = json.dumps([parent or group, new_title or "", check_id or "",
                           signal, signature.strip().casefold()],
                          ensure_ascii=True, separators=(",", ":"))
    stable_id = "DISC-" + sha256(identity.encode("utf-8")).hexdigest()[:12].upper()
    unknown_oracle = not (isinstance(oracle, str) and oracle.strip())
    return {
        "id": stable_id,
        "status": "candidate_needs_review",
        "observed_outcome": outcome,
        "signal": signal,
        "source_kind": source,
        "category_id": parent,
        "proposed_category": new_title if extension else None,
        "group": group,
        "requires_category_extension": extension,
        "existing_check_id": check_id,
        "failure_signature": signature,
        "priority": "safety_review" if signal in PRIORITY_SIGNALS else
                    "high" if signal in {"gps_loss", "reroute_problem", "offline_failure",
                                         "bad_speed", "coverage_gap"} else "normal",
        "example_case_id": case_id,
        "reproduction": reproducible,
        "expected": expectation,
        "observed": actual,
        "oracle": oracle,
        "requires_independent_truth": unknown_oracle,
        "evidence_ref": reference,
        "test_to_implement": _require_text(obs.get("new_test"), "new_test"),
        "required_followup": [
            "Check source/legality and reproduce the distinct failure mode",
            "Confirm that an existing test does not already cover the behavior",
            "Add narrow executable assertion, fixture and relevant component contract",
            "Rerun targeted case, neighboring components, held-out and end-to-end regressions",
            "Retain before/after results; only score independently judged comparable outcomes"
        ],
    }


def propose(batch: dict, matrix: dict, existing: list | None = None) -> dict:
    _non_personal(batch)
    if batch.get("schema_version") != 1 or batch.get("source_kind") not in SOURCE_KINDS:
        raise ValueError("Missing batch schema or unsupported evidence source")
    source = batch["source_kind"]
    run_url = _require_text(batch.get("run_url"), "run_url")
    if not run_url.startswith("https://github.com/"):
        raise ValueError("A public GitHub run/provenance link is required")
    observations = batch.get("observations")
    if not isinstance(observations, list):
        raise ValueError("observations must be a list")
    cats, checks, groups = _matrix_ids(matrix)
    prior = {c["id"]: c for c in (existing or [])}
    if len(prior) != len(existing or []):
        raise ValueError("Duplicate existing discovery IDs")
    added = []
    duplicates = []
    for obs in observations:
        item = _candidate(obs, cats, checks, groups, source)
        if item is None:
            continue
        if item["id"] in prior:
            duplicates.append(item["id"])
            continue
        prior[item["id"]] = item
        added.append(item)
    return {
        "schema_version": 1,
        "purpose": "evidence-backed discovery proposals, NOT new executed test outcomes",
        "source_run": run_url,
        "baseline_categories": len(cats),
        "baseline_check_definitions": len(checks),
        "candidates_total": len(prior),
        "new_candidate_count": len(added),
        "duplicates_collapsed": sorted(set(duplicates)),
        "candidates": sorted(prior.values(), key=lambda c: c["id"]),
        "automatically_added_to_production_or_rankings": False,
        "action": "Review, implement distinct tests, then rerun. Existing checks may be extended; new categories are permitted.",
    }


def batch_from_public_smoke(smoke: dict, run_url: str) -> dict:
    """One *real measured* coverage gap; zero restrictions isn't a routing failure."""
    if smoke.get("classification") != "public-road-experimental-not-legality-verified":
        raise ValueError("Not a recognized public-road smoke report")
    observations = []
    if smoke.get("node_via_forbidden_turn_pairs") == 0:
        observations.append({
            "case_id": "public-uk-smoke-restriction-coverage",
            "category_id": "NAV-008",
            "check_id": "NAV-008-A",
            "outcome": "UNKNOWN",
            "signal": "coverage_gap",
            "failure_signature": "no_node_via_forbidden_turn_pairs_in_partial_extract",
            "reproduction": "Use independently selected real UK junctions with independently verified node-via no-turn restrictions; replay same car profile and pinned map",
            "expected": "Observe legal turn restriction cases with known allowed/prohibited outcomes",
            "observed": "This bounded public road smoke imported zero node-via forbidden turn pairs; therefore no turn-legality conclusion is possible",
            "oracle": None,
            "evidence_ref": run_url,
            "new_test": "Add public real-UK no-turn and only-turn route cases, independent official/sign evidence where available, and assert legal guidance for incoming edges",
        })
    return {
        "schema_version": 1,
        "source_kind": "public_nonpersonal",
        "run_url": run_url,
        "observations": observations,
    }


def main():
    parser = argparse.ArgumentParser(description="Propose new DMN regression tests from reported anomalies")
    parser.add_argument("--input", type=Path, required=True, help="Normalized observations JSON, or public road smoke with --public-smoke")
    parser.add_argument("--public-smoke", action="store_true", help="Convert real public-road smoke coverage gaps")
    parser.add_argument("--run-url", help="Public GitHub Actions URL; required for --public-smoke outside Actions")
    parser.add_argument("--output", type=Path, default=ROOT / "results/dmn-discovery-proposals.json")
    args = parser.parse_args()
    target = args.output.resolve()
    if not target.is_relative_to((ROOT / "results").resolve()):
        raise ValueError("Output must remain in ignored results/, not auto-committed or published")
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    incoming = json.loads(args.input.read_text(encoding="utf-8"))
    if args.public_smoke:
        url = args.run_url
        if not url and os.getenv("GITHUB_RUN_ID") and os.getenv("GITHUB_REPOSITORY"):
            url = f'https://github.com/{os.environ["GITHUB_REPOSITORY"]}/actions/runs/{os.environ["GITHUB_RUN_ID"]}'
        incoming = batch_from_public_smoke(incoming, _require_text(url, "run-url"))
    report = propose(incoming, matrix)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"new_candidate_count": report["new_candidate_count"],
                      "candidates_total": report["candidates_total"],
                      "automatic_score_changes": 0}, indent=2))


if __name__ == "__main__":
    main()
