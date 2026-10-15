"""Same-map, same-endpoints navigation-engine routing response comparison.

A route response and HTTP latency do NOT demonstrate current legal-turn, GPS,
roundabout or full navigation correctness. The real OSM road GPS journey
cohort is reported separately; no simulated competitor GPS outcomes.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

# DMN open work and test target

ROUTE_TARGET = 100
WORK = (
    ("DMN-01", "critical", "observed blocker", "Support UK conditional and complex turn restrictions; expand rejected map areas"),
    ("DMN-02", "critical", "unverified legality", "Check actual UK legal road movements against independent ground truth"),
    ("DMN-03", "high", "observed GPS", "Resolve GPS ambiguity at junctions without guessing turns"),
    ("DMN-04", "high", "observed arrival", "Confirm destinations on very short adjacent road segments"),
    ("DMN-05", "high", "comparison gap", "Run equivalent real-road GPS traces on DMN and comparator matching interfaces"),
    ("DMN-06", "high", "comparison gap", "Verify real roundabout exits, junction decisions and lane restrictions"),
    ("DMN-07", "high", "comparison gap", "Measure same-route wrong-turn, rerouting and signal recovery outcomes"),
    ("DMN-08", "high", "phone validation", "Test offline map updates, Android speed, RAM, battery and reliability"),
    ("DMN-09", "medium", "phone validation", "Test spoken instruction timing and Bluetooth ducking"),
    ("DMN-10", "medium", "legal review", "Validate licences, map-data attribution and commercial redistribution"),
    ("DMN-11", "medium", "integration", "Select verified components, then approve integration into existing phone app"),
    ("DMN-12", "medium", "test expansion", "Run 100 same-map UK routes on all four mandatory runnable engines"),
)
PRIORITY = {"critical":0, "high":1, "medium":2}
MANDATORY_ROUTING = ("drivemate-native-cpp", "graphhopper", "osrm-mld", "osrm-ch")


def work_progress(route_count, repeats, engines, gps):
    """Count engineering workstreams separately from failed GPS fix samples.

    The expanded 100-route response benchmark is complete only when DMN,
    GraphHopper and both OSRM variants fully respond to exactly the same
    per-case endpoint workload. No other phone, safety or legality gate is
    marked resolved merely because route speed samples were collected.
    """
    benchmark_done = (route_count == ROUTE_TARGET and repeats >= 10
                      and all(name in engines and engines[name]["complete"]
                              and engines[name]["valid_routes"] == ROUTE_TARGET
                              for name in MANDATORY_ROUTING))
    items = [{"id":item_id, "priority":priority, "kind":kind, "task":task,
              "status":"completed" if item_id=="DMN-12" and benchmark_done else "open"}
             for item_id,priority,kind,task in WORK]
    items.sort(key=lambda r:(r["status"]!="open",PRIORITY[r["priority"]],r["id"]))
    return {"total":len(items),
            "remaining":sum(r["status"]=="open" for r in items),
            "completed":sum(r["status"]=="completed" for r in items),
            "open_by_priority":{p:sum(r["status"]=="open" and r["priority"]==p for r in items)
                                for p in PRIORITY},
            "items":items, "counting_rule":"distinct workstreams, not unresolved journeys or per-fix GPS events"}


ROUTE_CATEGORY = "real-English-roads-warm-http-speed"
JOURNEY_CATEGORY = "DriveMate-native-full-GPS-journey-replay-on-real-English-roads"


def analyse(speed, journey):
    if speed.get("category") != ROUTE_CATEGORY or journey.get("category") != JOURNEY_CATEGORY:
        raise ValueError("Different types of research evidence")
    for field in ("source_snapshot", "source_xml_sha256", "cohort_sha256"):
        if not speed.get(field) or speed.get(field) != journey.get(field):
            raise ValueError("Map/route cohort mismatch: "+field)
    case_ids = speed.get("cases", [])
    rows = journey.get("cases", [])
    if (not isinstance(case_ids, list) or len(case_ids) < 8 or
            len(set(case_ids)) != len(case_ids) or
            not isinstance(rows, list) or [r.get("case") for r in rows] != case_ids):
        raise ValueError("Case order/coverage differs between engines and DMN GPS journey")
    if journey.get("scenario_count") != len(case_ids):
        raise ValueError("Journey case count mismatched")
    count = len(case_ids)
    repeats = speed.get("repeats")
    if type(repeats) is not int or repeats < 3:
        raise ValueError("Missing repeated warm measurement design")
    engines = {}
    for engine, stats in speed.get("implementations", {}).items():
        samples = speed.get("samples", {}).get(engine, [])
        failures = speed.get("failures", {}).get(engine, [])
        if not isinstance(samples, list) or not isinstance(failures, list):
            raise ValueError("Invalid engine measurement ledger")
        counts = Counter()
        seen = set()
        for sample in samples:
            key = (sample.get("case"), sample.get("repeat"))
            if (key[0] not in case_ids or type(key[1]) is not int or
                    not 0 <= key[1] < repeats or key in seen):
                raise ValueError("Missing, extra or repeated route response")
            if not isinstance(sample.get("milliseconds"), (int, float)) or not math.isfinite(sample["milliseconds"]) or sample["milliseconds"] <= 0:
                raise ValueError("Invalid response duration")
            seen.add(key)
            counts[key[0]] += 1
        if (stats.get("passed_requests") != len(samples) or
                stats.get("total_requests") != repeats*count):
            raise ValueError("Aggregate request count does not match per-case evidence")
        complete = len(samples) == repeats*count and not failures
        if stats.get("complete") is not complete:
            raise ValueError("Unsupported claim of complete engine measurement")
        p95 = stats.get("p95_ms")
        if complete and (not isinstance(p95, (int, float)) or
                         not math.isfinite(p95) or p95 <= 0):
            raise ValueError("Invalid p95 for completed engine")
        valid_routes = sum(counts[c] == repeats and not any(f.get("case") == c for f in failures)
                           for c in case_ids)
        engines[engine] = {
            "valid_requests": len(samples), "expected_requests": count*repeats,
            "valid_routes": valid_routes, "route_cases": count,
            "request_failures": len(failures), "complete": complete,
            "p95_warm_local_http_ms": p95 if complete else None,
            "failed_case_ids": sorted({f.get("case") for f in failures if f.get("case") in case_ids}),
            "per_case_valid_requests": {c: counts[c] for c in case_ids},
            "independent_UK_turn_legality_verified": False
        }
    eligible = sorted((k for k in engines if engines[k]["complete"]),
                      key=lambda k: (engines[k]["p95_warm_local_http_ms"], k))
    ranks = [{"rank": rank, "engine": key, "p95_ms": engines[key]["p95_warm_local_http_ms"]}
             for rank, key in enumerate(eligible, 1)]
    jcounts=Counter(r.get("status") for r in rows)
    if (set(jcounts)-{"pass","fail","unresolved"} or
            any(journey.get(s)!=jcounts[s] for s in ("pass","fail","unresolved"))):
        raise ValueError("Contradictory full GPS journey case ledger")
    work = work_progress(count,repeats,engines,jcounts)
    return {
        "project": "DMN",
        "real_road_route_target": ROUTE_TARGET,
        "real_road_routes_checked": count,
        "real_road_routes_remaining": max(0,ROUTE_TARGET-count),
        "outstanding_work": work,
        "outstanding_gps_journeys": jcounts["unresolved"]+jcounts["fail"],
        "scope": "same-real-English-public-OSM-routing-response-comparison",
        "source_snapshot": speed["source_snapshot"],
        "map_sha256": speed["source_xml_sha256"],
        "case_cohort_sha256": speed["cohort_sha256"],
        "cases": count, "repeats_per_case": repeats,
        "warmups": speed.get("warmups"),
        "route_cohorts": speed.get("route_cohorts", {}),
        "engines": engines,
        "routing_latency_ranking_only": ranks,
        "actual_legal_routing_ranking": None,
        "complete_navigation_ranking": None,
        "dmn_simulated_gps_on_same_real_roads": {
            "passed": jcounts["pass"],"failed": jcounts["fail"],
            "unresolved": jcounts["unresolved"],
            "arrivals_confirmed": journey.get("arrivals_confirmed"),
            "uncertain_junction_holds": journey.get("uncertain_junction_holds"),
            "unsafe_instruction_opportunities": journey.get("speech_during_uncertain_junction"),
            "competitor_streamed_GPS_tested": False,
            "per_case": [{"case":r["case"],"cohort":r.get("cohort"),
                          "status":r["status"],"issues":r.get("issues",[]),
                          "components":r.get("components",{})} for r in rows]
        },
        "priority_improvements": [
            "1. Independent UK access/turn legality oracle per real-road junction",
            "2. Compare exact real-road trace matching (batch against batch, streaming separately)",
            "3. Resolve DMN junction/short-link GPS uncertainty without unsafe guessing",
            "4. Verified roundabout and lane movements, illegal turns and wrong-exit recovery",
            "5. Recorded device GPS; Android offline, battery, memory, audio and licensing",
            "6. Select component implementations for existing DriveMate app after approval"
        ],
        "limits": [
            "Public real OSM road geometry; no independently observed legal access.",
            "Identical source-map snapshot and coordinate endpoints; profiles/cost models may differ.",
            "Valid returned endpoints and finite geometry are NOT proof of a legal road sequence.",
            "The DMN same-route journey uses simulated sensor fixes and Python guidance; it is not the Android app.",
            "External engines did not execute equivalent streaming GPS/guidance journeys here.",
            "OSRM CH and MLD are two modes of one engine, not separate products.",
            "Only completed engines are ranked for p95 local HTTP response speed."
        ]
    }


def markdown(report):
    lines = ["# DMN — same real-road comparison", "",
             f"OSM snapshot {report['source_snapshot']}; {report['cases']} matched routes, "
             f"{report['warmups']} warmups, {report['repeats_per_case']} measured requests per route.", "",
             "**Ranking applies only to endpoint/geometry-validated warm HTTP response time. "
             "It is not a navigation accuracy, legality or phone-app ranking.**", "",
             "| Speed rank | Engine/configuration | Valid requests | Complete routes | p95 local HTTP |",
             "|---:|---|---:|---:|---:|"]
    ranked={r["engine"]:r["rank"] for r in report["routing_latency_ranking_only"]}
    for e in list(ranked)+[e for e in report["engines"] if e not in ranked]:
        r=report["engines"][e];pos=ranked.get(e,"Unranked")
        ms=("--" if r["p95_warm_local_http_ms"] is None else f"{r['p95_warm_local_http_ms']:.3f} ms")
        lines.append(f"| {pos} | {e} | {r['valid_requests']}/{r['expected_requests']} | "
                     f"{r['valid_routes']}/{r['route_cases']} | {ms} |")
    work=report["outstanding_work"]
    lines.extend(["",
        "## Tests and issues still left", "",
        f"- Real UK route scenarios checked: **{report['real_road_routes_checked']}/{report['real_road_route_target']}**; "
        f"**{report['real_road_routes_remaining']} remaining** toward the 100-route expansion.",
        f"- Engineering / validation workstreams: **{work['remaining']}/{work['total']} open** "
        f"(critical {work['open_by_priority']['critical']}, high {work['open_by_priority']['high']}, "
        f"medium {work['open_by_priority']['medium']}).",
        f"- DMN complete GPS journeys still requiring resolution: **{report['outstanding_gps_journeys']}/{report['cases']}**. "
        "Counted separately from the workstream backlog.",
        "", "### Outstanding work, sorted by priority", "",
        "| Priority | ID | Issue / remaining validation | Status |",
        "|---|---|---|---|"])
    for item in work["items"]:
        lines.append(f"| {item['priority']} | {item['id']} | {item['task']} | {item['status']} |")
    j=report["dmn_simulated_gps_on_same_real_roads"]
    lines.extend(["","## DMN simulated GPS replay on these same public-road routes","",
                  "| Measurement | Value |","|---|---:|",
                  f"| Confirmed destination arrivals | {j['arrivals_confirmed']}/{report['cases']} |",
                  f"| Fully accepted journeys | {j['passed']}/{report['cases']} |",
                  f"| Unresolved journeys | {j['unresolved']}/{report['cases']} |",
                  f"| Uncertain junction holds | {j['uncertain_junction_holds']} |",
                  f"| Unsafe instructions during held positions | {j['unsafe_instruction_opportunities']} |",
                  "","Reference engines have **no equivalent live-GPS-controller result here**. "
                  "Do not treat their routing speed as proof of GPS, lanes or guidance.","",
                  "## Priority improvements before integration into existing DriveMate app",""])
    lines.extend("- "+x for x in report["priority_improvements"])
    lines.extend(["","Never copy unsupported engine code. Continue independent UK movement validation, "
                  "GPS matching comparisons and safety gates; integrate only after specific user approval.",""])
    return "\n".join(lines)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--speed", type=Path, required=True)
    p.add_argument("--journey", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, default=Path("results/real-england"))
    a=p.parse_args()
    if not a.output_dir.resolve().is_relative_to(Path("results").resolve()):
        p.error("Output must be under ignored results/")
    report=analyse(json.loads(a.speed.read_text()),json.loads(a.journey.read_text()))
    a.output_dir.mkdir(parents=True,exist_ok=True)
    (a.output_dir/"dmn-real-road-comparison.json").write_text(json.dumps(report,indent=2)+"\n")
    (a.output_dir/"DMN_REAL_ROAD_SCORECARD.md").write_text(markdown(report))
    print(json.dumps({"case_count":report["cases"],"routing_latency_ranking":
                      [x["engine"] for x in report["routing_latency_ranking_only"]],
                      "complete_navigation_ranking":report["complete_navigation_ranking"],
                      "journeys_unresolved":report["dmn_simulated_gps_on_same_real_roads"]["unresolved"]}))


if __name__ == "__main__":
    main()
