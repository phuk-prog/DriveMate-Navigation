"""Verify a fresh, real-public-OSM DMN preference study against the pinned archive.

IDs alone are not an audit: previously a changed cost, profile selection or
partial study could retain the same hash of case IDs. This gate checks the
entire sanitized map-only case record and every experiment denominator.
Never serializes source nodes, coordinates, GPS fixes or personal journeys.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.uk_preference_case_register import validate_case_register

ARCHIVE_SCHEMA = "DMN-PUBLIC-UK-PREFERENCE-COMPARISON-v1"
# (current bounded-study output, permanent audited archive field)
COUNTERS = (
    ("neighborhoods_prepared", "areas_attempted"),
    ("neighborhoods_with_checked_rules", "areas_with_mapped_restrictions_checked"),
    ("unsupported_or_incomplete_neighborhoods", "areas_unsupported"),
    ("map_rule_pairs_checked", "mapped_restriction_pairs_checked"),
    ("detours_found_in_bounded_real_road_graph", "mapped_restriction_detours_found"),
    ("neighborhood_comparison_pairs_checked", "route_preference_pairs_checked"),
    ("neighborhood_pairs_with_multiple_routes", "route_preference_pairs_with_alternates"),
    ("neighborhood_fastest_shortest_divergences", "fastest_shortest_distinct_paths"),
    ("neighborhood_distinct_balanced_cases", "balanced_distinct_from_both"),
    ("case_register_count", "case_register_count"),
    ("case_register_sha256", "case_register_sha256"),
    ("source_snapshot", "source_snapshot"),
    ("restriction_source_sha256", "restriction_source_sha256"),
)


def verify_archived_replay(actual: dict, archive: dict) -> dict[str, object]:
    """Fail closed if even one stored path fingerprint or source count drifts.

    A verified replay means only that the *same provisional public-map
    experiment* was reproduced, not that any route is legal, safe or faster
    in live UK traffic.
    """
    if not isinstance(actual, dict) or not isinstance(archive, dict):
        raise ValueError("Expected bounded study and archive JSON objects")
    if archive.get("schema") != ARCHIVE_SCHEMA:
        raise AssertionError("Unknown archive schema")
    if (actual.get("case_register_integrity_validated") is not True or
            actual.get("case_register_all_cases_have_unknown_legality") is not True):
        raise AssertionError("Fresh study did not validate its unverified map cases")
    if (actual.get("independent_road_legality_verified") is not False or
            actual.get("external_engines_executed") not in (0, 1) or
            archive.get("independently_verified_current_road_law") is not False or
            archive.get("competitor_routes_executed") != 0 or
            archive.get("live_traffic_observed") is not False):
        raise AssertionError("Cannot replay a source-only archive as verified road truth")
    for observed, expected in COUNTERS:
        if observed not in actual or expected not in archive:
            raise AssertionError("Required pinned-map evidence field missing")
        if actual[observed] != archive[expected]:
            raise AssertionError("Pinned-map replay differs in " + observed)
    live_cases = actual.get("discriminating_case_register")
    saved_cases = archive.get("cases")
    if not isinstance(live_cases, list) or not isinstance(saved_cases, list):
        raise AssertionError("Missing sanitized case records")
    expected_count = archive["case_register_count"]
    saved = validate_case_register(saved_cases, expected_count=expected_count)
    live = validate_case_register(live_cases, expected_count=expected_count)
    if saved["case_register_sha256"] != archive["case_register_sha256"]:
        raise AssertionError("Permanent archive case identity checksum drift")
    if live["case_register_sha256"] != actual["case_register_sha256"]:
        raise AssertionError("Fresh case identity checksum drift")
    if live_cases != saved_cases:
        # Full-field, order-sensitive replay, not only stable case IDs.
        raise AssertionError("Pinned-map route fingerprints or estimated costs drifted")
    if actual["neighborhood_fastest_shortest_divergences"] != len(live_cases):
        raise AssertionError("Unaccounted preference divergences")
    engines = actual["external_engines_executed"]
    comparison = actual.get("osrm_case_comparison")
    if engines == 1:
        from benchmarks.uk_osrm_case_comparison import validate_osrm_case_results
        if not isinstance(comparison, dict):
            raise AssertionError("OSRM execution needs complete paired evidence")
        checked = validate_osrm_case_results(
            live_cases, comparison.get("case_results"), snapshot=archive["source_snapshot"])
        if checked != comparison:
            raise AssertionError("OSRM report contains inconsistent aggregate counts")
    elif comparison is not None:
        raise AssertionError("Unexecuted OSRM cannot claim paired observations")
    return {
        "classification": "reproduced-map-only-evidence-not-road-legality",
        "replay_matches_pinned_archive": True,
        "source_snapshot": archive["source_snapshot"],
        "matched_cases": len(live_cases),
        "matched_route_preference_pairs": actual["neighborhood_comparison_pairs_checked"],
        "matched_distinct_fastest_shortest": actual["neighborhood_fastest_shortest_divergences"],
        "case_register_sha256": live["case_register_sha256"],
        "independent_uk_road_legality_verified": False,
        "external_competitors_executed": engines,
        "paired_osrm_cases": len(live_cases) if engines else 0,
        "navigation_quality_score": None,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Compare live bounded public UK map data to pinned, sanitized archive")
    p.add_argument("--actual", type=Path, required=True)
    p.add_argument("--archive", type=Path, required=True)
    a = p.parse_args()
    if a.actual.stat().st_size > 1_000_000 or a.archive.stat().st_size > 1_000_000:
        raise ValueError("Refusing oversized unreviewed study evidence")
    actual = json.loads(a.actual.read_text(encoding="utf-8"))
    archive = json.loads(a.archive.read_text(encoding="utf-8"))
    print(json.dumps(verify_archived_replay(actual, archive), indent=2))


if __name__ == "__main__":
    main()
