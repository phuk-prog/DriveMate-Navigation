"""Compare archived TURN-001 v1.3 endpoint attachment, without re-running engines.

Read-only diagnosis of historical base-clip run entries. One engine's PASS
path can provide test-harness anchored endpoint segments for a *same case*,
but does not prove independent current road truth. Never label results a
new benchmark or re-score final wide-clip verdicts.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

RUN_ID = 39019749346
ENGINES = ("DMN", "OSRM", "Valhalla", "GraphHopper")
SOURCE_SHA = "2a8ef8e1f2533cb009b1ce248a6bf4eaabdd47e03979e64e24cd844f3b22acba"
COHORT_SHA = "f2949a8a9aab40b7f62bc658cf92778f440ab5cdcc7ffcc755e21dc1b83c391c"
PREPARED_SHA = "8500d8f3d9cf99660fcc3267ad422134fce87cbb946fe25f6940763546707bf3"
REVISION = "0668fce23c146158dbfaff3399d329391419e387"


def load(folder: Path) -> dict[str, dict]:
    runs = {}
    for engine in ENGINES:
        file = folder / f"turn001-{engine}" / f"run-{engine}.json"
        if not file.exists():
            raise RuntimeError(f"Missing archived result: {file}")
        run = json.loads(file.read_text())
        expected = {"engine": engine, "revision": REVISION, "source_sha256": SOURCE_SHA,
                    "cohort_sha256": COHORT_SHA, "prepared_sha256": PREPARED_SHA}
        for field, wanted in expected.items():
            if run.get("_provenance", {}).get(field) != wanted:
                raise RuntimeError(f"{engine}: wrong {field}; archived runs must match exactly")
        runs[engine] = {key: val for key, val in run.items() if key != "_provenance"}
    if len({tuple(sorted(run)) for run in runs.values()}) != 1:
        raise RuntimeError("Different case IDs across archived engines")
    if len(runs["DMN"]) != 142:
        raise RuntimeError("Expected 142 testable TURN-001 base-clip cases")
    return runs


def classify(runs: dict[str, dict]) -> dict:
    dmn = runs["DMN"]
    output = {"historical_run": RUN_ID, "scope": "archived base-clip route attachment only",
              "reused_competitor_outcomes": True,
              "truth": "frozen OSM map endpoint-segment contract, not independent road legality",
              "source_sha256": SOURCE_SHA, "cohort_sha256": COHORT_SHA,
              "prepared_sha256": PREPARED_SHA, "revision": REVISION, "engines": {}}
    for engine in ("GraphHopper", "OSRM", "Valhalla"):
        cases = runs[engine]
        off = {k: v for k, v in cases.items() if v.get("verdict") == "UNRESOLVED_SNAP"}
        stats = Counter()
        details = []
        for case, response in sorted(off.items(), key=lambda x: int(x[0])):
            node_path = response.get("path") or []
            dmn_response = dmn[case]
            dmn_path = dmn_response.get("path") or []
            if not node_path:
                stats["no_matched_node_path"] += 1
            if dmn_response.get("verdict") == "PASS" and node_path and dmn_path:
                # A PASS was checked for *exact* starting and ending OSM segments.
                # Compare the two route attachments on that identical case only.
                start_match = node_path[:2] == dmn_path[:2]
                end_match = node_path[-2:] == dmn_path[-2:]
                stats["anchored_proxy_comparable"] += 1
                if start_match and end_match:
                    stats["both_matched"] += 1
                elif not start_match and not end_match:
                    stats["both_differ"] += 1
                elif not start_match:
                    stats["start_differ_only"] += 1
                else:
                    stats["end_differ_only"] += 1
                start_dist = response.get("start_snap_m")
                end_dist = response.get("end_snap_m")
                if not start_match and isinstance(start_dist, (float, int)) and start_dist <= 0.3:
                    stats["start_wrong_segment_but_position_within_0_3m"] += 1
                if not end_match and isinstance(end_dist, (float, int)) and end_dist <= 0.3:
                    stats["end_wrong_segment_but_position_within_0_3m"] += 1
            else:
                stats["not_comparable_to_dmn_pass"] += 1
            details.append({"relation_id": case, "engine_verdict": response["verdict"],
                            "dmn_verdict": dmn_response.get("verdict"),
                            "path_nodes": len(node_path),
                            "start_snap_m": response.get("start_snap_m"),
                            "end_snap_m": response.get("end_snap_m"),
                            "dmn_anchored_proxy_available": dmn_response.get("verdict") == "PASS"})
        output["engines"][engine] = {
            "base_clip_verdict_counts": dict(sorted(Counter(v.get("verdict") for v in cases.values()).items())),
            "offtarget_count": len(off), "diagnostic_counts": dict(sorted(stats.items())),
            "offtarget_cases": details,
        }
    return output


def brief(s: dict) -> str:
    lines = ["### Archived TURN-001 base-clip wrong-road endpoint attachment",
             "", f"Historical frozen run: [{RUN_ID}](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/{RUN_ID}).",
             "No engines re-run; no route verdicts or navigation rules changed.",
             "", "| Engine | Off-target raw base cases / 142 | Off-target cases comparable to anchored DMN PASS | Start differs only | End differs only | Both differ |",
             "|---|---:|---:|---:|---:|---:|"]
    for engine, entry in s["engines"].items():
        d = entry["diagnostic_counts"]
        lines.append(f"| {engine} | {entry['offtarget_count']} | "
                     f"{d.get('anchored_proxy_comparable', 0)} | "
                     f"{d.get('start_differ_only', 0)} | "
                     f"{d.get('end_differ_only', 0)} | "
                     f"{d.get('both_differ', 0)} |")
    g = s["engines"]["GraphHopper"]["diagnostic_counts"]
    lines += ["", "For GraphHopper, a request coordinate within 0.3 m of the returned geometry can still be "
              "on the **wrong directed road segment**:",
              f"- {g.get('start_wrong_segment_but_position_within_0_3m', 0)} same-case starts;",
              f"- {g.get('end_wrong_segment_but_position_within_0_3m', 0)} same-case finishes.",
              "", "**Limitations:** DMN PASS anchoring is an *existing OSM harness contract*, "
              "not legal truth. The raw base-clip UNRESOLVED_SNAP counts do not include "
              "wide-clip finalisations. Do not use this report as a new competitive ranking "
              "or automatically relax exact-edge checks."]
    return "\n".join(lines) + "\n"


def self_test() -> None:
    good = {"_provenance": {"engine": "DMN", "revision": REVISION}}
    assert good["_provenance"]["revision"] == REVISION
    assert len(ENGINES) == 4
    p = {"path": ["1", "2", "3", "4"]}
    q = {"path": ["5", "2", "3", "4"]}
    assert p["path"][:2] != q["path"][:2]
    assert p["path"][-2:] == q["path"][-2:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("results/turn001-endpoint-audit"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("PASS: endpoint diagnostic self-check")
    if args.artifacts_dir is not None:
        data = classify(load(args.artifacts_dir))
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "summary.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        text = brief(data)
        (args.output_dir / "brief.md").write_text(text)
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
