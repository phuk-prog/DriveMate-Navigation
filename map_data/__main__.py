"""Inspect an OSM XML file locally; prints only aggregate provenance and statistics."""
import argparse
import json
from pathlib import Path
from .osm_xml import Provenance, import_osm_xml


def main() -> None:
    p = argparse.ArgumentParser(description="OSM XML prototype import (no GPX/driver recordings)")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--region", required=True)
    p.add_argument("--snapshot", required=True, help="Source snapshot date or version")
    p.add_argument("--source", default="local-OSM-XML")
    p.add_argument("--attribution", default="© OpenStreetMap contributors")
    a = p.parse_args()
    result = import_osm_xml(a.input.read_bytes(), provenance=Provenance(a.region, a.snapshot, a.source, a.attribution))
    print(json.dumps(result.metadata, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
