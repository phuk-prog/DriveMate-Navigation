"""Load synthetic test networks only. Real imports must include provenance."""
from __future__ import annotations

import json
from pathlib import Path
from engine import RoadEdge, RoadGraph


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic-junction.json"


def load_fixture(path: Path = FIXTURE) -> tuple[RoadGraph, str, str, tuple[str, ...]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("classification") != "synthetic":
        raise ValueError("Prototype fixtures must be explicitly synthetic")
    edges = [RoadEdge(**data) for data in raw["edges"]]
    graph = RoadGraph(raw["vertices"], edges, raw["prohibited_turns"])
    return graph, raw["start"], raw["end"], tuple(raw["expected_edge_ids"])
