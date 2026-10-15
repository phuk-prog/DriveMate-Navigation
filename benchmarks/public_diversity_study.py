"""One controlled public-OSM route-choice study across two fixed UK road areas.

This is research on a pinned open-map snapshot, NOT a legality, ETA, driver GPS,
lane, or real-time traffic oracle. The caller supplies a predownloaded public
Geofabrik PBF; no service credentials, personal journeys or phone identifiers.
Area selection is independent of any driver's origin/destination.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.public_uk_probe import check_public_graph
from map_data.osm_xml import OSMImportError
from tools.public_osm_extract import DATA_AREA, prepare

# Small, fixed PUBLIC Manchester & Stockport road-study boxes. No user position.
# Source- and time-pinned; validate extraction completeness separately.
PUBLIC_AREAS = (
    ("manchester-centre-public-roads", "-2.251000,53.476000,-2.240000,53.487000"),
    ("stockport-public-road-corridor", "-2.192000,53.404000,-2.181000,53.415000"),
)


def study_public_road_diversity(source: Path, *, snapshot: str,
                                result_dir: Path = DATA_AREA,
                                candidates=PUBLIC_AREAS,
                                preparer=prepare,
                                checker=check_public_graph,
                                samples: int = 8) -> dict[str, object]:
    if not source.name.endswith(".osm.pbf") or not source.is_file():
        raise ValueError("A predownloaded, nonpersonal public OSM PBF is required")
    if not isinstance(snapshot, str) or not snapshot.strip():
        raise ValueError("Source snapshot must be supplied")
    if not isinstance(samples, int) or not 1 <= samples <= 50:
        raise ValueError("Bound sample count to 1..50")
    if not candidates or len(candidates) > 3:
        raise ValueError("Use at most three independent bounded public road areas")
    result_dir = result_dir.resolve()
    if not result_dir.is_relative_to(DATA_AREA.resolve()):
        raise ValueError("Ephemeral map data must remain under git-ignored results/")
    result_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for i, (name, bounds) in enumerate(candidates):
        if not isinstance(name, str) or not name or not isinstance(bounds, str):
            raise ValueError("Invalid public area entry")
        temporary = result_dir / f"dmn-public-diversity-{i}.osm"
        if temporary.exists():
            raise ValueError("Refusing to overwrite a previous map extract")
        try:
            prepared = preparer(source, bounds, temporary,
                                snapshot=snapshot, region=name)
            # Reuse the exact source-map preference and Dijkstra/A* checks.
            report = checker(temporary.read_bytes(), snapshot=snapshot,
                             region=name, samples=samples)
            records.append({
                "area": name,
                "status": "graph_research_executed",
                "prepared_map_sha256": prepared["map_sha256"],
                "map_graph": report,
            })
        except OSMImportError as exc:
            # Unsupported map conditions are not silently marked usable.
            records.append({"area": name, "status": "unsupported_extract",
                            "reason": str(exc)})
        finally:
            temporary.unlink(missing_ok=True)
    usable = [r for r in records if r["status"] == "graph_research_executed"]
    distinct = [r for r in usable if r["map_graph"][
        "route_preference_discriminating_coverage"] == "MAP_DIVERGENCE_OBSERVED"]
    return {
        "classification": "UK-public-map-preference-topology-research",
        "source_snapshot": snapshot,
        "areas_attempted": len(records),
        "areas_graph_tested": len(usable),
        "areas_unsupported": len(records) - len(usable),
        "areas_with_fastest_shortest_path_diversity": len(distinct),
        "comparison_coverage": "MAP_DIVERGENCE_OBSERVED" if distinct else "INSUFFICIENT",
        "independently_verified_legal_movements": False,
        "real_time_traffic_tested": False,
        "external_navigation_engines_run": 0,
        "source_attribution": "© OpenStreetMap contributors; research usage subject to ODbL",
        "areas": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Public UK research route preference diversity")
    parser.add_argument("--pbf", type=Path, required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--samples", type=int, default=8)
    args = parser.parse_args()
    print(json.dumps(study_public_road_diversity(
        args.pbf, snapshot=args.snapshot, samples=args.samples), indent=2))


if __name__ == "__main__":
    main()
