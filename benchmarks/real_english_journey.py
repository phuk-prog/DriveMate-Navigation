"""End-to-end DriveMate journey replay using independently sourced real English roads.

The *map network* is genuine dated public OSM geometry. GPS fixes are GENERATED
in-memory from that geometry and are not real sensor observations or user drives.
The integrated journey calls the compiled DriveMate native routing engine through
navigation_core.journey, with existing GPS matching/recovery/roundabout/guidance.
No competitor whole-navigation scores are manufactured.
"""
import argparse
import json
import math
import os
from pathlib import Path
from statistics import median

from benchmarks.real_english_speed import road_cases
from engine.reconciled import prepare_navigation
from gps.matching import Fix
from gps.recovery import RecoveringGpsJourney
from guidance.timing import InstructionScheduler
from map_data import Provenance, import_osm_xml

# Never persist generated latitude/longitude or observations, even public-only.
SAMPLE_ORIGIN_EPOCH = 1791892800.0  # deterministic synthetic receipt clock
ROUTE_FRACTION = 500000


def sample_fractions(segment_length_m):
    """Continuous sample positions with <=6 metre gaps on any OSM segment."""
    if not math.isfinite(segment_length_m) or segment_length_m <= 0:
        raise ValueError("Positive segment length required")
    steps = max(12, int(math.ceil(segment_length_m / 6.0)))
    return tuple(i / steps for i in range(1, steps))


def short_destination_ambiguity(length_m, diagnostics, reached):
    """Do not score an unresolvable short goal as a navigation failure."""
    return (not reached and length_m <= 8.0 and len(diagnostics) >= 3
            and all(item["match_status"] == "ambiguous"
                    for item in diagnostics[-3:]))


def replay_case(prepared, name, source, target):
    row = {"case": name, "source_type": "public_map_node",
           "fix_source": "simulated_from_public_OSM_geometry",
           "routing_backend": "compiled_cpp_via_native_adapter",
           "components": {
               "native_routing": "not_exercised",
               "gps_matching": "not_exercised",
               "rerouting": "not_exercised",
               "junctions": "not_exercised",
               "roundabouts": "not_exercised",
               "instruction_events": "not_exercised",
               "arrival": "not_exercised",
           }, "observations": 0, "recognized_matches": 0,
           "guidance_frames": 0, "instruction_events": 0,
           "wrong_road_matches": 0,
           "near_junction_other_road_matches": 0,
           "uncertain_junction_holds": 0,
           "speech_during_uncertain_junction": 0,
           "destination_diagnostics": [],
           "issues": [], "status": "unresolved"}
    # This executes the compiled router (not Python research search).
    route = prepared.route(source, target, backend="portable")
    edges = route.edge_ids
    if not edges or any(prepared.source_edges[a].target != prepared.source_edges[b].source
                        for a, b in zip(edges, edges[1:])):
        row["issues"].append("native_route_discontinuous_or_empty")
        row["components"]["native_routing"] = "fail"
        row["status"] = "fail"
        return row
    row["components"]["native_routing"] = "pass"
    row["road_segments"] = len(edges)
    row["route_metres"] = round(route.length_m, 1)
    row["unverified_access_segments"] = len(route.unverified_access_edges)
    last_edge = edges[-1]
    row["destination_segment_length_m"] = round(
        math.hypot((prepared.coordinates[prepared.source_edges[last_edge].target][0] -
                    prepared.coordinates[prepared.source_edges[last_edge].source][0]) * 111195,
                   (prepared.coordinates[prepared.source_edges[last_edge].target][1] -
                    prepared.coordinates[prepared.source_edges[last_edge].source][1]) * 111195 *
                   math.cos(math.radians(prepared.coordinates[prepared.source_edges[last_edge].source][0]))), 2)
    # A destination is an observed position along the final original road.
    tracker = RecoveringGpsJourney(prepared, last_edge, ROUTE_FRACTION)
    guide = InstructionScheduler(tracker, "public_"+name.replace("-", "_"))
    # Keep a physically possible, steady in-memory driver trace with no jitter.
    clock = SAMPLE_ORIGIN_EPOCH
    acquired = False
    reached = False
    prior = None
    last_status = None
    errors = []
    for edge_index, road in enumerate(edges):
        segment = tracker.matcher.segments[road]
        graph_edge = prepared.source_edges[road]
        a, b = prepared.coordinates[graph_edge.source], prepared.coordinates[graph_edge.target]
        fractions = sample_fractions(segment.length)
        for q in fractions:
            # All positions are deterministic test input, never captured GPS.
            lat = a[0] + q * (b[0]-a[0])
            lon = a[1] + q * (b[1]-a[1])
            if prior is not None:
                # Each sample is 1s apart. Mark implausible jumps as test
                # setup unsupported, not as GPS matcher faults.
                distance = math.hypot((lat-prior[0])*111195,
                           (lon-prior[1])*111195*math.cos(math.radians(lat)))
                if distance > 20.0:
                    row["issues"].append("fixture_sample_spacing_gt_20m")
                    row["status"] = "unresolved"
                    return row
            prior = (lat,lon)
            clock += 1.0
            fix = Fix(lat, lon, clock, 1.0, 9.0, segment.bearing, 5.0)
            try:
                update = tracker.observe(fix, clock)
                frame = guide.poll(clock)
            except (AssertionError, KeyError, ValueError, OverflowError) as exc:
                errors.append(type(exc).__name__+": "+str(exc)[:105])
                break
            row["observations"] += 1
            last_status = update.status
            if update.match and update.match.junction_held:
                row["uncertain_junction_holds"] += 1
                # The navigation engine can retain history and its route,
                # but this uncertain positioning must not trigger speech.
                if update.guidance_available or frame.pending:
                    row["speech_during_uncertain_junction"] += 1
            if edge_index == len(edges)-1:
                snap = tracker.snapshot
                row["destination_diagnostics"].append({
                    "sample_fraction": round(q, 4),
                    "match_status": update.match.status if update.match else None,
                    "recovery_status": update.status,
                    "match_on_expected_road": bool(update.match and update.match.road == road),
                    "trusted_position_on_final_road": bool(snap and snap.position.edge ==
                                                         prepared.edge_ids[last_edge]),
                    "trusted_fraction": snap.position.fraction if snap else None,
                    "journey_status": snap.status if snap else None,
                    "instruction_status": frame.status,
                })
                row["destination_diagnostics"] = row["destination_diagnostics"][-16:]
            if update.match and update.match.status == "matched":
                row["recognized_matches"] += 1
                if update.match.road != road:
                    # Near a junction the real OSM edges share physical
                    # endpoints: a mathematically valid cross-snap may be
                    # indistinguishable from one direction to another.
                    # Retain it as UNCERTAIN rather than manufacture a fail.
                    along_to_node = min(q, 1.0-q) * segment.length
                    if along_to_node <= max(8.0, 2.0*fix.accuracy_m):
                        row["near_junction_other_road_matches"] += 1
                    else:
                        row["wrong_road_matches"] += 1
            if tracker.snapshot and tracker.snapshot.status in ("navigating", "arrived"):
                acquired = True
            if tracker.guidance_available(clock):
                row["guidance_frames"] += 1
            if frame.pending:
                if guide.acknowledge(frame.pending.event_id, clock):
                    row["instruction_events"] += 1
            if tracker.snapshot and tracker.snapshot.status == "arrived":
                reached = True
                break
        if errors or reached:
            break
    goal_ambiguous = short_destination_ambiguity(
        row["destination_segment_length_m"],
        row["destination_diagnostics"], reached)
    row["components"]["gps_matching"] = (
        "fail" if row["wrong_road_matches"] else
        "unresolved" if row["near_junction_other_road_matches"]
        else "pass" if row["recognized_matches"] >= 3 else "unresolved")
    row["components"]["arrival"] = (
        "pass" if reached else
        "unresolved" if goal_ambiguous else
        "fail" if acquired and not errors else "unresolved")
    row["components"]["junctions"] = "exercised_unverified" if row["guidance_frames"] else "not_exercised"
    row["components"]["instruction_events"] = (
        "exercised_unverified" if row["instruction_events"] else "not_exercised")
    row["issues"].extend(errors)
    if row["speech_during_uncertain_junction"]:
        row["issues"].append("unsafe_instruction_available_during_junction_hold")
    if row["wrong_road_matches"]:
        row["issues"].append("gps_matched_different_directed_road_far_from_junction")
    if row["near_junction_other_road_matches"]:
        row["issues"].append("gps_matched_other_road_near_junction_unverified")
    if not acquired:
        row["issues"].append("gps_never_acquired_trusted_route")
    if not reached:
        row["issues"].append("destination_not_confirmed")
    if goal_ambiguous:
        row["issues"].append("short_destination_spur_gps_indistinguishable")
    row["final_recovery_status"] = last_status
    # Explicit route topology can have no junction or roundabout. Never
    # score an unexercised subsystem as a success.
    row["status"] = "fail" if errors or row["wrong_road_matches"] or row["speech_during_uncertain_junction"] or (acquired and not reached and not goal_ambiguous) else (
        "pass" if reached and acquired and row["recognized_matches"] >= 3
        and not row["near_junction_other_road_matches"]
        else "unresolved")
    return row


def execute(raw, snapshot, maximum):
    imported = import_osm_xml(raw, provenance=Provenance(
        "Greater Manchester, England", snapshot,
        "Geofabrik historic public OSM PBF",
        "© OpenStreetMap contributors (ODbL 1.0)"))
    prepared = prepare_navigation(imported.graph, imported.coordinates)
    if prepared.timed_restrictions:
        raise ValueError("Native timed routing not supported: real-road journey test cannot ignore restrictions")
    cases = road_cases(prepared, imported.graph, maximum=maximum)
    if len(cases) < 5:
        raise ValueError("No eligible real-road route corpus; never substitute synthetic geometry")
    rows = []
    for c in cases:
        try:
            result = replay_case(prepared, c["id"], c["source"], c["target"])
        except (AssertionError, KeyError, ValueError, OSError, OverflowError) as exc:
            result = {"case": c["id"], "status": "unresolved",
                      "issues": ["scenario_setup_or_engine_error: "+type(exc).__name__+
                                 ": "+str(exc)[:120]], "components": {}}
        rows.append(result)
    count = lambda value: sum(r["status"] == value for r in rows)
    components = {name: {status: sum(r.get("components", {}).get(name) == status for r in rows)
                          for status in ("pass", "fail", "unresolved", "not_exercised",
                                         "exercised_unverified")}
                  for name in ("native_routing", "gps_matching", "rerouting", "junctions",
                               "roundabouts", "instruction_events", "arrival")}
    return {"component_scorecard": components,
            "category": "DriveMate-native-full-GPS-journey-replay-on-real-English-roads",
            "source_snapshot": snapshot,
            "region": os.environ.get("ENGLAND_BBOX_NAME", "unlabelled"),
            "geometry": "real public English OSM road network",
            "gps_data": "deterministic simulated observations, NOT actual device GPS",
            "real_sensor_validation": False, "voice_delivery_validation": False,
            "external_full_journey_comparison": False,
            "scenario_count": len(rows),
            "arrivals_confirmed": components["arrival"]["pass"],
            "verified_native_routes": components["native_routing"]["pass"],
            "far_from_junction_wrong_matches": sum(r.get("wrong_road_matches", 0) for r in rows),
            "uncertain_junction_holds": sum(r.get("uncertain_junction_holds", 0) for r in rows),
            "speech_during_uncertain_junction": sum(r.get("speech_during_uncertain_junction", 0) for r in rows),
            "pass": count("pass"),
            "fail": count("fail"), "unresolved": count("unresolved"),
            "cases": rows,
            "limitations": [
                "Candidate locations are generated from OSM rather than measured by a real device.",
                "No independent observed legal-turn/roundabout/lane oracle for these roads.",
                "Native route backend exercises compiled C++, guidance/GPS remain Python research modules.",
                "A simple route may never exercise roundabout, junction, GPS loss or rerouting logic.",
                "Journey pass indicates a controlled simulated acquisition and arrival, not real driving readiness.",
                "Junction-proximity map matching to another directed edge is unresolved, not an automatic failure or a pass.",
                "Unsupported or uncertain outcomes are counted, never converted to passes.",
                "No personal routes or recorded user location included in output."
            ]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--cases", type=int, default=8)
    args = parser.parse_args()
    if not 5 <= args.cases <= 20:
        parser.error("Case count must be between 5 and 20")
    if not args.input.resolve().is_relative_to(Path("results").resolve()):
        parser.error("Map must remain inside ignored results/ directory")
    raw = args.input.read_bytes()
    report = execute(raw, args.snapshot, args.cases)
    output = Path("results/real-england")
    output.mkdir(exist_ok=True, parents=True)
    (output / "journeys.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k: report[k] for k in ("category", "scenario_count",
          "verified_native_routes", "arrivals_confirmed",
          "far_from_junction_wrong_matches", "uncertain_junction_holds",
          "speech_during_uncertain_junction",
          "pass", "fail", "unresolved", "region")}))
    if report["fail"] or report["unresolved"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
