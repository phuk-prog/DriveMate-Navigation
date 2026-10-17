"""Execute frozen analytical controls for ROUTE-004 selected-edge coverage."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path

from benchmarks.real_map_legality_baseline import selected_edge_forward_traversal

FIXTURE = Path(__file__).parent / "fixtures" / "route004-selected-edge-controls.json"


def execute(fixture: Path = FIXTURE) -> dict:
    raw = fixture.read_bytes()
    contract = json.loads(raw)
    rows = []
    for case in contract["cases"]:
        actual = selected_edge_forward_traversal(
            case["points"], contract["allowed_start"], contract["allowed_end"])
        expected = case["expected_selected_forward"]
        rows.append({"case_id": case["id"], "expected_selected_forward": expected,
                     "actual_selected_forward": actual,
                     "outcome": "PASS" if actual == expected else "FAIL"})
    return {
        "test_id": contract["test_id"],
        "classification": contract["classification"],
        "fixture_sha256": sha256(raw).hexdigest(),
        "run_sha": os.getenv("GITHUB_SHA"),
        "historical_route004_rescored": False,
        "passed": sum(row["outcome"] == "PASS" for row in rows),
        "failed": sum(row["outcome"] == "FAIL" for row in rows),
        "total": len(rows),
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.fixture)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
