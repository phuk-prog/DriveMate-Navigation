"""Find route-distance disagreements in retained ROUTE-004 evidence.

This is an evidence audit, not a fresh engine execution or a correctness rank.
Distance disagreement cannot establish legality or optimality without comparable
route geometry and an independent oracle.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
from statistics import median

SPREAD_REVIEW_RATIO = 1.20


def diagnose(source: Path) -> dict:
    raw = source.read_bytes()
    report = json.loads(raw)
    if report.get("test_id") != "ROUTE-004" or not isinstance(report.get("results"), list):
        raise ValueError("Expected retained ROUTE-004 evidence")
    by_case = defaultdict(list)
    for engine in report["results"]:
        name = engine.get("engine")
        if not name:
            raise ValueError("Engine identity missing")
        for case in engine.get("cases", []):
            distance = case.get("distance_m")
            if case.get("outcome") == "PASS" and isinstance(distance, (int, float)) and distance > 0:
                by_case[case["case_id"]].append({"engine": name, "distance_m": distance})
    rows = []
    for case_id in sorted(by_case):
        values = by_case[case_id]
        if len(values) < 3:
            continue
        distances = [item["distance_m"] for item in values]
        spread = max(distances) / min(distances)
        if spread < SPREAD_REVIEW_RATIO:
            continue
        rows.append({
            "case_id": case_id,
            "status": "UNRESOLVED_ROUTE_QUALITY_DIVERGENCE",
            "minimum_distance_m": min(distances),
            "median_distance_m": median(distances),
            "maximum_distance_m": max(distances),
            "max_to_min_ratio": spread,
            "engine_distances": sorted(values, key=lambda item: (item["distance_m"], item["engine"])),
            "reason": "No retained comparable geometry or independent fastest-legal-route oracle",
            "competitor_consensus_is_truth": False,
        })
    return {
        "test_id": "ROUTE-004-QUALITY-DIAGNOSTIC-1",
        "classification": "retained-evidence diagnostic; not a fresh engine execution or ranking",
        "source_evidence_sha256": sha256(raw).hexdigest(),
        "spread_review_ratio": SPREAD_REVIEW_RATIO,
        "quality_ranking": "NOT_JUDGED",
        "historical_route004_rescored": False,
        "review_case_count": len(rows),
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = diagnose(args.source)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
