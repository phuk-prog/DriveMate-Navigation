"""DMN research outcomes for selecting navigation technology for existing DriveMate Android app.

Never confuse a C++ benchmark, simulated GPS controller or an untested feature
with an Android-ready component.
"""
import argparse
import json
import math
from pathlib import Path

COMPONENTS = ("native_routing", "gps_matching", "rerouting", "junctions",
              "roundabouts", "instruction_events", "arrival")
OUTCOMES = ("pass", "fail", "unresolved", "not_exercised", "exercised_unverified")
PHONE_GATES = ("uk_legal_turn_ground_truth", "real_device_gps_and_recovery",
               "roundabout_lane_and_junction_evidence", "audio_bluetooth_delivery",
               "android_memory_battery_speed_and_offline_maps",
               "licence_ownership_redistribution", "existing_app_integration")


def decide(journey=None, speed=None):
    counts = {key: {state: 0 for state in OUTCOMES} for key in COMPONENTS}
    totals = {"pass": 0, "fail": 0, "unresolved": 0}
    case_count = 0
    if journey is not None:
        if journey.get("category") != "DriveMate-native-full-GPS-journey-replay-on-real-English-roads":
            raise ValueError("Unexpected journey evidence type")
        rows = journey.get("cases")
        if not isinstance(rows, list) or not rows or len(rows) != journey.get("scenario_count"):
            raise ValueError("Missing or mismatched journey case ledger")
        case_count = len(rows)
        for item in rows:
            status = item.get("status")
            if status not in totals:
                raise ValueError("Invalid journey status")
            totals[status] += 1
            for key in COMPONENTS:
                result = item.get("components", {}).get(key, "not_exercised")
                if result not in OUTCOMES:
                    raise ValueError("Invalid component status")
                counts[key][result] += 1
        if any(journey.get(name) != total for name, total in totals.items()):
            raise ValueError("Aggregate journey totals do not match cases")
        for key in COMPONENTS:
            counts[key]["attempted"] = case_count - counts[key]["not_exercised"]
            counts[key]["total"] = case_count
    else:
        for key in COMPONENTS:
            counts[key]["attempted"] = 0
            counts[key]["total"] = 0

    eligible, excluded = [], []
    if speed is not None:
        if speed.get("category") != "real-English-roads-warm-http-speed":
            raise ValueError("Unexpected speed evidence type")
        if journey is not None and journey.get("source_snapshot") != speed.get("source_snapshot"):
            raise ValueError("Cannot combine different public map snapshots")
        for engine, stats in speed.get("implementations", {}).items():
            measured, total, p95 = (stats.get("passed_requests"), stats.get("total_requests"),
                                    stats.get("p95_ms"))
            if (stats.get("complete") is True and isinstance(measured, int)
                    and isinstance(total, int) and measured == total and total > 0
                    and isinstance(p95, (int, float)) and not isinstance(p95, bool)
                    and math.isfinite(p95) and p95 > 0):
                eligible.append({"engine": engine, "p95_ms": p95,
                                 "passed_requests": measured, "total_requests": total})
            else:
                excluded.append({"engine": engine, "reason": "incomplete_or_not_tested"})
        eligible.sort(key=lambda x: (x["p95_ms"], x["engine"]))
        for position, x in enumerate(eligible, 1):
            x["routing_speed_rank_only"] = position

    return {"project": "DMN", "full_name": "DriveMate Navigation",
            "purpose": "research_compare_improve_and_select_for_existing_DriveMate_Android_app",
            "standalone_app_required": False, "production_app_modified": False,
            "journey_evidence": {"status": ("measured" if journey is not None else "not_tested"),
                                 "total": case_count, **totals, "components": counts,
                                 "source_snapshot": journey.get("source_snapshot") if journey else None},
            "speed_evidence": {"status": ("measured" if speed is not None else "not_tested"),
                               "scope": "host_warm_http_routing_latency_not_full_navigation",
                               "eligible": eligible, "excluded": excluded,
                               "overall_navigation_winner": None},
            "phone_decision": "PENDING_EVIDENCE_AND_USER_APPROVAL",
            "component_choice": {key: "undecided" for key in COMPONENTS},
            "phone_gates": {gate: "not_verified" for gate in PHONE_GATES},
            "next_test": "Independent junction/short road GPS matching ground truth and replay"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journey", type=Path)
    ap.add_argument("--speed", type=Path)
    ap.add_argument("--output", type=Path, default=Path("results/dmn-phone-decision.json"))
    args = ap.parse_args()
    if not args.output.resolve().is_relative_to(Path("results").resolve()):
        ap.error("Keep evidence in untracked results directory")
    def read(path):
        return json.loads(path.read_text()) if path is not None and path.is_file() else None
    report = decide(read(args.journey), read(args.speed))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"project": "DMN", "phone_decision": report["phone_decision"],
                      "journey": report["journey_evidence"]["status"],
                      "full_passed": report["journey_evidence"]["pass"],
                      "full_unresolved": report["journey_evidence"]["unresolved"],
                      "speed_engines_tested": len(report["speed_evidence"]["eligible"])}))


if __name__ == "__main__":
    main()
