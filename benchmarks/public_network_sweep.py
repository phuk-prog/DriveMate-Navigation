"""Opt-in, aggregate-only public UK map coverage investigation.

Each named rectangle is independently selected public geography, not a trip.
Unsupported access/conditional/via-way data remains UNSUPPORTED, never accepted.
No map XML or PBF files are committed or uploaded as artifacts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.public_uk_probe import check_public_graph
from map_data.osm_xml import OSMImportError
from tools.public_osm_extract import DATA_AREA, parse_bbox, prepare

# Distinct public UK districts, each within the prototype's bounding-box limit.
# These are coverage candidates, not proven routes or road-restriction oracles.
PUBLIC_AREAS = (
    ("south_manchester", "-2.260000,53.400000,-2.240000,53.420000"),
    ("wigan", "-2.640000,53.535000,-2.620000,53.555000"),
    ("manchester_centre", "-2.245000,53.477000,-2.230000,53.492000"),
)


def summarise(records: list[dict[str, object]]) -> dict[str, object]:
    if not records or any(x.get("status") not in
                          {"SUPPORTED", "UNSUPPORTED"} for x in records):
        raise ValueError("Need explicit supported/unsupported results")
    supported = [x for x in records if x["status"] == "SUPPORTED"]
    discriminating = [x for x in supported
                      if x["metrics"]["route_preference_discriminating_coverage"]
                      == "MAP_DIVERGENCE_OBSERVED"]
    return {
        "areas_attempted": len(records),
        "areas_supported": len(supported),
        "areas_unsupported": len(records) - len(supported),
        "areas_with_observed_fastest_shortest_divergence": len(discriminating),
        "result": ("MAP_DIVERGENCE_OBSERVED" if discriminating
                   else "INSUFFICIENT_OR_UNSUPPORTED"),
        "independently_verified_legal_or_lane_truth": False,
        "external_engines_executed": 0,
        "cases": records,
    }


def sweep(source: Path, *, snapshot: str) -> dict[str, object]:
    results = []
    for slug, bbox in PUBLIC_AREAS:
        parse_bbox(bbox)
        target = DATA_AREA / ("dmn-network-" + slug + ".osm")
        try:
            preparation = prepare(
                source, bbox, target, snapshot=snapshot,
                region="non-personal public UK study: " + slug)
            diagnostic = check_public_graph(
                target.read_bytes(), snapshot=snapshot,
                region="public UK test area: " + slug, samples=8)
            # Never retain full raw road data or individual test journeys.
            results.append({
                "area": slug,
                "status": "SUPPORTED",
                "source_sha256": preparation["map_sha256"],
                "metrics": {
                    key: value for key, value in diagnostic.items()
                    if key.startswith(("network_", "map_derived_", "fastest_",
                                       "balanced_")) or key in (
                        "route_preference_discriminating_coverage",
                        "node_via_forbidden_turn_pairs",
                        "scenario_count",
                        "route_preference_graph_rules_consistent")
                },
            })
        except OSMImportError:
            # Not an algorithm success or a zero-failure route. Unsupported
            # restrictions, large extracts and incomplete objects fail closed.
            results.append({"area": slug, "status": "UNSUPPORTED",
                            "reason": "prototype map importer rejected source"})
        finally:
            target.unlink(missing_ok=True)
    return summarise(results)


def main() -> None:
    parser = argparse.ArgumentParser(description="One opt-in public UK coverage scan")
    parser.add_argument("--pbf", type=Path, required=True,
                        help="Local Geofabrik PUBLIC extract; never private/history")
    parser.add_argument("--snapshot", required=True)
    args = parser.parse_args()
    print(json.dumps(sweep(args.pbf, snapshot=args.snapshot), indent=2))


if __name__ == "__main__":
    main()
