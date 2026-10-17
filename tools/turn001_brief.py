"""Short TURN-001 summary (a few lines) so people and agents need not read logs.

Reads results/turn001/summary.json (from `turn001_restrictions score`) and, if
present, run-OSRM-control.json. Exits 1 when DMN takes a banned movement or
breaks any other mapped rule, or when the harness check misses violations.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

WORK = Path(__file__).resolve().parents[1] / "results" / "turn001"


def main() -> int:
    summary = json.loads((WORK / "summary.json").read_text())
    lines = [f"TURN-001 {summary['contract']} @ {summary['revision'][:12]}: "
             f"{summary['testable_cases']} testable, {summary['discriminating_cases']} discriminating"]
    for name, e in summary["engines"].items():
        verdicts = ", ".join(f"{k} {v}" for k, v in sorted(e["all_testable"].items()))
        lines.append(f"- {name}: {verdicts}; legal routes {e['pass_and_route_legal']}; "
                     f"rule breaks {len(e['other_rule_violations'])}; "
                     f"no-route though legal route exists {len(e['no_route_but_legal_route_exists'])}; "
                     f"median query {e['warm_query_ms_median']} ms")
    bad = []
    dmn = summary["engines"].get("DMN", {})
    if dmn.get("fail_cases") or dmn.get("other_rule_violations"):
        bad.append("DMN broke a mapped rule")
    control = WORK / "run-OSRM-control.json"
    if control.exists():
        runs = {k: v for k, v in json.loads(control.read_text()).items() if not k.startswith("_")}
        dmn_run = json.loads((WORK / "run-DMN.json").read_text())
        disc = [k for k in runs if dmn_run.get(k, {}).get("control_without_relation") == "USES_MOVEMENT"]
        caught = Counter(runs[k]["verdict"] for k in disc)
        lines.append(f"- harness check (OSRM without the tested rule, discriminating cases): {dict(caught)}")
        if disc and caught.get("FAIL_PROHIBITED", 0) == 0:
            bad.append("harness check caught no violations")
    lines.append("RESULT: " + ("; ".join(bad) if bad else "OK"))
    print("\n".join(lines))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
