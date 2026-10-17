"""Category 1 final scorecard: reproducible, provenance-checked existing evidence.

Reads already-completed public research Action summary artifacts ONLY. The
cohorts are deliberately INDEPENDENT: no blended overall engine leaderboard.
This is an audit of Category 1 execution and outstanding ground-truth gaps,
not a fresh engine test, final UK safety certificate or authorization to drive.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

EXPECTED = {
    "map001": 39018620653,
    "turn001": 39019749346,
    "barrier001": 39029643326,
    "endpoint": 39028874337,
    "heading": 39029550716,
}
TURN_MAP_SHA = "2a8ef8e1f2533cb009b1ce248a6bf4eaabdd47e03979e64e24cd844f3b22acba"
TURN_COHORT_SHA = "f2949a8a9aab40b7f62bc658cf92778f440ab5cdcc7ffcc755e21dc1b83c391c"
MAP_MAN_SHA = "34438baa7a28c55958cd5ba7ac3909a551c51197911963364d27a26eefe8973a"
ENGINES = ("DMN", "OSRM", "Valhalla", "GraphHopper")


def load(directory: Path, name: str) -> dict:
    path = directory / name
    if not path.is_file():
        raise ValueError(f"Required archived score not available: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def checked(p: Path) -> dict:
    m = load(p / "map001", "map001-category1-closure.json")
    native = load(p / "map001", "map001-native-six-region-summary.json")
    masks = load(p / "map001", "map001-native-turn-barrier.json")
    binary = load(p / "map001", "map001-additional-profiles/scorecard.json")
    turn = load(p / "turn001", "summary.json")
    barrier = load(p / "barrier001", "summary.json")
    endpoint = load(p / "endpoint", "summary.json")
    trial = load(p / "heading", "results.json")

    assert m["trial"] == "MAP-001-CATEGORY-1-CLOSURE"
    assert m["basis"] == "ARCHIVED_PUBLIC_OSM_NOT_INDEPENDENT_ROAD_LAW"
    assert m["all_120_cases_accounted_for"] is True
    assert m["independent_legality_pass"] == 0
    assert m["navigation_behavior_changed"] is False
    assert m["source_segment_comparisons"] == 980
    assert len(m["source_access_cases"]) == 120
    assert Counter(x["verdict"] for x in m["source_access_cases"]) == {
        "PASS": 79, "SAFE_WITHHELD": 41}
    assert len(m["source_versions"]) == 6
    assert next(a for a in m["source_versions"] if a["area"] == "manchester")["sha256"] == MAP_MAN_SHA
    assert native["trial"] == "MAP-001-NATIVE-SIX-REGION-1"
    assert native["partial_common_native_ways"] == 78
    assert native["total_original_source_ways"] == 120
    assert native["total_comparable_segment_checks"] == 714
    assert native["full_category_1_multi_engine_ranking"] is None
    assert native["independent_road_law"] is False
    assert native["native_turn_legality"] == "UNSUPPORTED_AUTOCOST_CONTEXT_NOT_EVALUATED"
    assert len(native["regional_results"]) == 6
    ranks = {e["engine"]: e for e in native["partial_native_access_ranking"]}
    assert set(ranks) == {"DMN ★", "Valhalla 3.9.1"}
    assert all(v["pass"] == 78 and v["fail"] == 0 and v["total"] == 78
               for v in ranks.values())
    assert masks["source_restrictions_checked"] == 26
    assert masks["barrier_ways_checked"] == 9
    assert masks["source_node_barriers_checked"] == 11
    assert masks["fully_equivalent_native_turn_policy"] is False
    assert masks["fully_equivalent_node_barrier_traversal"] is False
    assert binary["common_complete_case_count"] == 8
    assert binary["full_category_1_ranking"] is None

    assert turn["contract"] == "TURN-001 v1.3"
    assert turn["cohort_sha256"] == TURN_COHORT_SHA
    assert turn["source_sha256"] == TURN_MAP_SHA
    assert turn["cases_frozen"] == 169 and turn["testable_cases"] == 142
    assert turn["discriminating_cases"] == 129
    assert set(turn["engines"]) == set(ENGINES)
    assert all(x["executed"] == 142 for x in turn["engines"].values())
    tdmn = turn["engines"]["DMN"]
    assert tdmn["pass_and_route_legal"] == 131
    assert tdmn["all_testable"] == {
        "PASS": 131, "SAFE_NO_ROUTE": 5, "ENDPOINT_WITHHELD_BY_POLICY": 6}
    assert not tdmn["fail_cases"] and not tdmn["other_rule_violations"]
    assert not tdmn["no_route_but_legal_route_exists"]

    assert barrier["contract"] == "BARRIER-001 v1.2"
    assert barrier["source_sha256"] == TURN_MAP_SHA
    assert barrier["cases_frozen"] == 110
    assert barrier["testable_cases"] == 94
    assert barrier["discriminating_cases"] == 92
    assert barrier["testable_by_group"] == {
        "closed": 47, "open": 14, "restricted": 8, "untagged_gate": 25}
    assert set(barrier["engines"]) == set(ENGINES)
    assert all(e["executed"] == 94 for e in barrier["engines"].values())
    bdmn = barrier["engines"]["DMN"]
    assert bdmn["pass_and_route_legal"] == 46
    assert not bdmn["fail_cases"] and not bdmn["other_rule_violations"]
    assert not bdmn["no_route_but_known_access_legal_route_exists"]
    assert len(bdmn["no_route_with_only_uncertain_access_alternatives"]) == 2
    assert len(bdmn["no_route_but_legal_route_exists"]) == 2

    assert endpoint["historical_run"] == EXPECTED["turn001"]
    assert endpoint["source_sha256"] == TURN_MAP_SHA
    gh = endpoint["engines"]["GraphHopper"]
    assert gh["offtarget_count"] == 67
    assert gh["diagnostic_counts"]["anchored_proxy_comparable"] == 54
    assert gh["diagnostic_counts"]["start_differ_only"] == 41
    assert gh["diagnostic_counts"]["end_differ_only"] == 11
    assert gh["diagnostic_counts"]["both_differ"] == 2
    assert trial["baseline_archived_run"] == EXPECTED["turn001"]
    assert trial["source_sha256"] == TURN_MAP_SHA
    assert trial["cohort_sha256"] == TURN_COHORT_SHA
    assert trial["penalty_seconds"] == 86400
    assert len(trial["cases"]) == 12
    assert trial["groups"]["start_mismatch"]["legal_exact_edge_improved"] == 0
    assert trial["groups"]["end_mismatch"]["legal_exact_edge_improved"] == 0
    assert trial["groups"]["correct_control"]["trial_pass_and_legal"] == 3

    # Cohort-local rankings only. Do not rank graph source agreement beside
    # turn/barrier route proxies, or compare query latencies across different scopes.
    def ranked(s):
        rows = [{ "engine": k, "legal_passes": s["engines"][k]["pass_and_route_legal"],
                  "tested": s["testable_cases"],
                  "invalid_prohibited_moves": len(s["engines"][k]["fail_cases"]),
                  "other_rule_violations": len(s["engines"][k]["other_rule_violations"]),
                  "by_verdict": s["engines"][k]["all_testable"] if "all_testable" in s["engines"][k]
                    else s["engines"][k]["by_group"]}
                for k in ENGINES]
        return sorted(rows, key=lambda x: (-x["legal_passes"], x["invalid_prohibited_moves"],
                                            x["other_rule_violations"], x["engine"]))
    return {
        "contract": "CATEGORY-1-FINAL-EVIDENCE-1",
        "objective": "Engine-only Category 1 — source facts and named route-level map legality proxies",
        "sources": {n: {"run": run, "url":
             f"https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/{run}"}
             for n, run in EXPECTED.items()},
        "independent_current_uk_road_law_verified": False,
        "no_registration_performed": True,
        "android_app_modified": False,
        "navigation_behaviour_modified_in_this_batch": False,
        "full_category_winner": None,
        "speed_ranking": None,
        "scope_distinctions": [
            "MAP001 120 ways/980 segments are OSM-source edge/access agreement, not independently signed road truth",
            "MAP001 native common 78 ways/714 segments is a partial DMN vs Valhalla graph-access ranking only",
            "TURN001 142 junction restrictions are a distinct map-based route output ranking for 4 engines",
            "BARRIER001 61 judged of 94 testable barriers are distinct route-based barrier outcomes for 4 engines",
            "Historical 67 GraphHopper wrong-segment starts/ends are BASE-CLIP; published final TURN001 reports 68",
            "A stronger GraphHopper 86,400s heading penalty fixed zero of nine wrong-segment diagnostic cases",
            "Unknown gate access, dynamic conditions, native full-turn policy and independent sign/TRO truth remain unverified",
        ],
        "map001_source": {
            "regions": 6, "selected_ways": 120, "source_edges_compared": 980,
            "source_pass": 79, "safe_withheld": 41, "wrong_judged_source_facts": 0},
        "map001_native": {
            "selected_ways": 120, "common_binary_ways": 78,
            "source_segments_compared": 714, "partial_tied_rank": native["partial_native_access_ranking"],
            "source_restrictions_inspected": 26, "barrier_ways": 9, "barrier_nodes": 11,
            "full_turn_policy_verified": False},
        "binary_public_profile": {
            "cases_common": 8, "full_category_rank": None},
        "turn001": {"frozen_relations": 169, "testable": 142,
                    "map_based_route_rank": ranked(turn),
                    "dmn_unverified_no_routes": 5, "dmn_car_closed_endpoints": 6},
        "barrier001": {"frozen_barriers": 110, "testable": 94, "judged": 61,
                       "map_based_route_rank": ranked(barrier),
                       "dmn_uncertain_gate_alternatives": 2,
                       "dmn_known_access_missed_alternatives": 0},
        "graphhopper_heading_trial": {
            "cases": 12, "previously_offtarget": 9,
            "legality_compliant_endpoint_fixes": 0,
            "control_passes": 3,
            "decision": "NO_FIX_JUSTIFIED; unchanged external engine and benchmark contract"},
        "remaining_withheld_reasons": [
            "5 frozen TURN001 no-routes diagnosed on OSM, not independently law-verified",
            "30 endpoints through unknown/private gates in BARRIER001, owner context unresolved",
            "Closed-barrier approach/turnaround lacks verified real-world feasibility case",
            "No complete equivalent motorcar turn/access native graph interface for every external engine",
            "Live legal orders/signage and some conditional access require unavailable/nonregistration evidence",
        ],
        "category1_research_checks": "EXECUTED",
        "category1_full_independent_road_truth": "NOT_VERIFIED",
        "category2_started": False,
    }


def md(r: dict) -> str:
    lines = [
        "# DMN Category 1 — compiled, frozen evidence scorecard",
        "",
        "**Status: engineering research run; NOT independently verified UK road legality.**",
        "",
        f"Historical GitHub evidence: " + ", ".join(
            f"[{n.upper()}]({s['url']})" for n,s in r["sources"].items()) + ".",
        "",
        "| Separate measurement | Engine | Supported result | Notes |",
        "|---|---|---:|---|",
        "| 120-way OSM source audit | DMN ★ | 79/120 PASS | 41 safe withheld; 980 source-segment checks |",
        "| Native car-access common subset | DMN ★ | 78/78 PASS | 714 directed segments |",
        "| Native car-access common subset | Valhalla 3.9.1 | 78/78 PASS | Same 714 segments |",
    ]
    for category, label, denominator in (("turn001", "Turn-restriction route output", "142"),
                                         ("barrier001", "Barrier route output", "61 judged")):
        for row in r[category]["map_based_route_rank"]:
            lines.append(f"| {label} | {row['engine']} | {row['legal_passes']}/{denominator} | "
                         f"Map-derived; not independent UK legal sign proof |")
    lines += [
        "", f"**Endpoint candidate:** {r['graphhopper_heading_trial']['legality_compliant_endpoint_fixes']} "
        "of nine off-target trial cases repaired; 3 of 3 baseline controls remain correct.",
        "",
        "**Caveat:** These tables do not form one category-wide engine ranking. "
        "The source-way audit, native access subset and route-level tests have different contracts and denominators.",
        "Neither a navigation runtime/app readiness judgement nor a timing leaderboard is made.",
        "",
        "## Unresolved evidence, left diagnosed rather than guessed",
        ""
    ]
    lines.extend(f"- {s}" for s in r["remaining_withheld_reasons"])
    lines += ["", "Source-code/build decisions: original per-test results retained; "
              "no accounts, API credentials, other-category trials, app changes or APK builds.",
              "Any future engine behavioural fix requires genuine evidence plus full frozen "
              "comparator and safety-regression reruns.",""]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--evidence-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, default=Path("results/category1-final"))
    args = p.parse_args()
    r = checked(args.evidence_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "scorecard.json").write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
    (args.output_dir / "scorecard.md").write_text(md(r))
    print(md(r))


if __name__ == "__main__":
    main()
