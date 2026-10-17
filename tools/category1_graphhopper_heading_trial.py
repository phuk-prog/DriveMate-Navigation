"""Category 1 — diagnostic GraphHopper heading-penalty trial on predeclared TURN-001 cases.

Do not alter the published v1.3 comparison, original engine binaries,
scoring rules or DMN. Test whether changing GraphHopper's documented
soft heading penalty improves the exact-edge attachment, while keeping
all other input/adapter settings the same.

Registered selected cases before the trial:
6 start-only mismatch, 3 finish-only mismatch, 3 correct controls. These
are diagnostic cases, never a fair full-cohort engine ranking.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import time
from pathlib import Path
from urllib.error import HTTPError
from benchmarks import turn001_restrictions as t

IDS = (
    "2070895", "2070900", "4179048", "6755009", "7301773", "7336294",
    "6316748", "10182417", "11902362",
    "10372299", "10811890", "11565718",
)
START_ONLY = set(IDS[:6])
END_ONLY = set(IDS[6:9])
CONTROLS = set(IDS[9:])
ARCHIVED_SHA = "0668fce23c146158dbfaff3399d329391419e387"
SOURCE_SHA = "2a8ef8e1f2533cb009b1ce248a6bf4eaabdd47e03979e64e24cd844f3b22acba"
COHORT_SHA = "f2949a8a9aab40b7f62bc658cf92778f440ab5cdcc7ffcc755e21dc1b83c391c"
PREPARED_SHA = "8500d8f3d9cf99660fcc3267ad422134fce87cbb946fe25f6940763546707bf3"
PENALTY_SECONDS = 86400
OUTPUT = t.ROOT / "results/turn001-heading-trial"


def graphhopper_strong_heading(geom: dict, headings: tuple[int, int]):
    """The original GET route request with ONLY heading_penalty increased."""
    o, d = geom["origin"], geom["destination"]
    url = (f"http://127.0.0.1:8989/route?point={o[0]:.7f},{o[1]:.7f}"
           f"&point={d[0]:.7f},{d[1]:.7f}"
           "&profile=car&points_encoded=false&instructions=false&ch.disable=true"
           "&way_point_max_distance=0"
           f"&heading={headings[0]}&heading={headings[1]}"
           f"&heading_penalty={PENALTY_SECONDS}")
    began = time.perf_counter()
    try:
        data = t._http_json(url)
    except HTTPError as exc:
        body = json.loads(exc.read() or b"{}")
        if any("ConnectionNotFound" in str(h.get("details", "")) for h in body.get("hints", [])):
            return None, (time.perf_counter() - began) * 1000
        raise RuntimeError(f"GraphHopper HTTP {exc.code}: {body.get('message', '')[:200]}") from exc
    ms = (time.perf_counter() - began) * 1000
    return [(lat, lon) for lon, lat in data["paths"][0]["points"]["coordinates"]], ms


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--baseline-file", type=Path, required=True)
    args = p.parse_args()
    baseline = json.loads(args.baseline_file.read_text())
    expected = {"revision": ARCHIVED_SHA, "engine": "GraphHopper",
                "source_sha256": SOURCE_SHA, "cohort_sha256": COHORT_SHA,
                "prepared_sha256": PREPARED_SHA}
    for field, value in expected.items():
        assert baseline["_provenance"].get(field) == value, field
    assert t.sha256_file(t.COHORT) == COHORT_SHA
    records_raw = (t.WORK / "prepared.json").read_bytes()
    assert hashlib.sha256(records_raw).hexdigest() == PREPARED_SHA
    records = {str(r["relation"]): r for r in json.loads(records_raw)}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    t.graphhopper_query = graphhopper_strong_heading
    results = {"contract": "TURN-001 GraphHopper soft-heading preference trial v1",
               "scope": "12 predeclared archived TURN-001 base clips, diagnostic only",
               "penalty_seconds": PENALTY_SECONDS,
               "source_sha256": SOURCE_SHA,
               "cohort_sha256": COHORT_SHA,
               "prepared_sha256": PREPARED_SHA,
               "archived_revision": ARCHIVED_SHA,
               "baseline_archived_run": 39019749346,
               "cases": {}}
    for rid in IDS:
        case = records[rid]
        geom = case["geometry"]
        if geom["status"] != "TESTABLE":
            raise RuntimeError(f"Non-testable archived case {rid}")
        folder = t.WORK / "cases" / rid
        raw = (folder / "clip.osm").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == case["clip_sha256"]
        clip = t.Clip(raw)
        old = baseline[rid]
        current = t.engine_case("GraphHopper", folder, clip, geom)
        case_type = ("start_mismatch" if rid in START_ONLY else
                     "end_mismatch" if rid in END_ONLY else "correct_control")
        improved = old["verdict"] == "UNRESOLVED_SNAP" and current["verdict"] == "PASS" and current.get("route_legal") == "LEGAL"
        results["cases"][rid] = {
            "stratum": case_type,
            "base_verdict": old["verdict"],
            "base_legal": old.get("route_legal"),
            "trial_verdict": current["verdict"],
            "trial_route_legal": current.get("route_legal"),
            "trial_errors": current.get("detail"),
            "trial_violations": current.get("violations", []),
            "trial_snap_m": [current.get("start_snap_m"), current.get("end_snap_m")],
            "trial_query_ms": current.get("warm_query_ms"),
            "trial_path_nodes": current.get("nodes"),
            "legal_and_exact_edge_improvement": improved,
            "trial_path": current.get("path", []),
        }
        (OUTPUT / "results.json").write_text(json.dumps(results, sort_keys=True, indent=1))
        print(rid, case_type, "BASE", old["verdict"], "TRIAL", current["verdict"],
              current.get("route_legal", "unjudged"), flush=True)
    group = {}
    for label in ("start_mismatch", "end_mismatch", "correct_control"):
        entries = [v for v in results["cases"].values() if v["stratum"] == label]
        group[label] = {"executed": len(entries),
                        "legal_exact_edge_improved": sum(v["legal_and_exact_edge_improvement"] for v in entries),
                        "trial_pass_and_legal": sum(v["trial_verdict"] == "PASS" and v["trial_route_legal"] == "LEGAL" for v in entries),
                        "trial_fail_prohibited": sum(v["trial_verdict"] == "FAIL_PROHIBITED" for v in entries),
                        "trial_errors": sum(v["trial_verdict"] in ("ERROR", "ENGINE_REJECTED_MAP") for v in entries)}
    results["groups"] = group
    (OUTPUT / "results.json").write_text(json.dumps(results, indent=1, sort_keys=True))
    lines = ["### GraphHopper 11.1 strict-preference diagnostic on 12 frozen cases",
             "", "Comparison: GraphHopper original soft heading penalty vs 86,400s penalty, same GraphHopper binary/profile/clip.",
             "**Not a full-cohort competitor ranking or legally verified oracle.**", "",
             "| Stratum | Executed | New legal, exact-edge improvements | New legal anchored passes | New prohibited moves | Query/setup errors |",
             "|---|---:|---:|---:|---:|---:|"]
    for label, v in group.items():
        lines.append(f"| {label} | {v['executed']} | {v['legal_exact_edge_improved']} | "
                     f"{v['trial_pass_and_legal']} | {v['trial_fail_prohibited']} | {v['trial_errors']} |")
    lines += ["", "All case outcomes and OSM node paths are in the attached results.json. "
              "If no supported improvement, do not change the scoring oracle/adapter. "
              "If a safe improvement is repeatable, version a corrected adapter then run the *whole* "
              "142-case frozen cohort for DMN and every applicable reference engine."]
    (OUTPUT / "brief.md").write_text("\n".join(lines) + "\n")
    print((OUTPUT / "brief.md").read_text())
    return int(any(v["trial_errors"] for v in group.values()))


if __name__ == "__main__":
    raise SystemExit(main())
