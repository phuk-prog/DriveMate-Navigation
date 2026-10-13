"""Opt-in local preparation of NON-PERSONAL, publicly licensed OpenStreetMap road data.

No download, network client, private GPS tracks or CI runtime input.
Requires a manually obtained public, contributor-anonymised .osm.pbf file and
the external osmium executable. Output is allowed only under ignored results/.
Converts a small bbox with all OSM object metadata removed. The existing
conservative OSM importer then validates the XML and may reject complex rules.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from map_data import Provenance, import_osm_xml
from map_data.osm_xml import MAX_INPUT_BYTES, OSMImportError

ROOT = Path(__file__).resolve().parents[1]
DATA_AREA = ROOT / "results"


def parse_bbox(value: str) -> str:
    """Return canonical bbox string, rejecting invalid/global extents."""
    try:
        coordinates = [float(token.strip()) for token in value.split(",")]
    except ValueError as exc:
        raise ValueError("Bbox requires four finite geographic coordinates") from exc
    if len(coordinates) != 4:
        raise ValueError("Bbox order: min longitude, min latitude, max longitude, max latitude")
    west, south, east, north = coordinates
    from math import isfinite
    if not all(isfinite(x) for x in coordinates):
        raise ValueError("Bbox coordinates must be finite")
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Invalid bbox boundaries")
    if east - west > 0.04 or north - south > 0.04:
        raise ValueError("Use a small public-road test area (<=0.04 degrees in each direction)")
    return ",".join(format(x, ".6f") for x in coordinates)


def validate_paths(source: Path, output: Path, results_dir: Path = DATA_AREA) -> None:
    if not source.name.endswith(".osm.pbf"):
        raise ValueError("Only an explicitly public, non-history .osm.pbf source may be used")
    if any(token in source.name.lower() for token in ("internal", "history", "private", "personal")):
        raise ValueError("Never use private or historical contributor data")
    if output.suffix != ".osm" or not output.name:
        raise ValueError("Output must be a .osm XML file")
    area = results_dir.resolve()
    target = output.resolve()
    if not target.is_relative_to(area) or target == area:
        raise ValueError("Output must be within git-ignored results/")
    if target == source.resolve():
        raise ValueError("Output cannot overwrite source")


def command_plan(source: Path, bbox: str, target: Path, scratch: Path) -> tuple[tuple[str, ...], ...]:
    bounds = parse_bbox(bbox)
    validate_paths(source, target)
    extract = scratch / "temporary-public-subset.osm.pbf"
    return (
        ("osmium", "extract", "--strategy", "complete_ways", "--bbox", bounds,
         str(source), "-o", str(extract)),
        ("osmium", "cat", str(extract), "-o", str(target),
         "-f", "osm,add_metadata=false"),
    )


def reject_object_metadata(raw: bytes) -> None:
    """Reject contributor metadata even if a conversion fails to strip it."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise OSMImportError("Converted subset is not valid XML") from exc
    for el in root.iter():
        if el.tag in ("node", "way", "relation"):
            if any(key in el.attrib for key in ("user", "uid", "changeset")):
                raise OSMImportError("Contributor metadata present: refusing public-repo workflow")


def prepare(source: Path, bbox: str, target: Path, *,
            snapshot: str, region: str,
            runner=subprocess.run) -> dict[str, object]:
    """Local-only opt-in preparation, deleting converted files on any failure."""
    validate_paths(source, target)
    if not source.is_file():
        raise ValueError("Download an approved contributor-anonymised public PBF locally first")
    if not snapshot.strip() or not region.strip():
        raise ValueError("Public source snapshot date and region are required")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError("Refusing to overwrite existing map subset")
    with tempfile.TemporaryDirectory(prefix="osm-subset-", dir=DATA_AREA) as tmp:
        commands = command_plan(source, bbox, target, Path(tmp))
        try:
            if runner is subprocess.run and shutil.which("osmium") is None:
                raise RuntimeError("Install osmium-tool to process public OSM PBF files locally")
            for command in commands:
                runner(command, check=True, timeout=600, stdout=subprocess.DEVNULL)
            if not target.is_file() or target.stat().st_size > MAX_INPUT_BYTES:
                raise OSMImportError("Subset exceeds the 6 MB prototype importer limit; choose a smaller bbox")
            raw = target.read_bytes()
            reject_object_metadata(raw)
            result = import_osm_xml(
                raw, provenance=Provenance(region, snapshot, "public-local-geofabrik-pbf",
                                           "© OpenStreetMap contributors")
            )
            return {
                "status": "prototype-import-complete",
                "does_not_prove_driving_legality": True,
                "uploaded_map_files": 0,
                "map_sha256": sha256(raw).hexdigest(),
                "nodes": result.metadata["vertices"],
                "directed_edges": result.metadata["directed_edges"],
                "prohibited_turn_pairs": result.metadata["prohibited_turn_pairs"],
            }
        except Exception:
            target.unlink(missing_ok=True)
            raise


def main() -> None:
    p = argparse.ArgumentParser(description="Local public OSM subset only; no personal journeys")
    p.add_argument("--input", required=True, type=Path, help="Locally downloaded public .osm.pbf")
    p.add_argument("--bbox", required=True, help="minLon,minLat,maxLon,maxLat of PUBLIC test roads")
    p.add_argument("--snapshot", required=True, help="Public extract's source snapshot/version")
    p.add_argument("--region", default="public test region")
    p.add_argument("--output", type=Path, default=DATA_AREA / "public-road-subset.osm")
    p.add_argument("--execute", action="store_true", help="Perform local conversion (never in CI)")
    args = p.parse_args()
    validate_paths(args.input, args.output)
    parse_bbox(args.bbox)
    if not args.execute:
        print("Validated local public-data plan. No download, conversion or upload performed.")
        print("Pass --execute to run locally after verifying source rights and region.")
    else:
        print(json.dumps(prepare(args.input, args.bbox, args.output,
                                 snapshot=args.snapshot, region=args.region), indent=2))


if __name__ == "__main__":
    main()
