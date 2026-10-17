"""Validation and coverage counts for the planned DMN atomic tests. No real engines run here."""
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config/dmn-atomic-test-matrix.json"

def validate(data: dict) -> dict:
    if data.get("schema_version") != 1 or data.get("new_suite_execution") != "not_run":
        raise ValueError("Invalid or falsely-executed plan")
    domains = data.get("domains")
    cats = data.get("categories")
    if not isinstance(domains, list) or len(domains) != 12 or not isinstance(cats, list) or len(cats) != 72:
        raise ValueError("Expected 12 domains and 72 categories")
    names = [d.get("name") for d in domains]
    if len(set(names)) != 12 or any(not isinstance(n, str) or not n for n in names):
        raise ValueError("Invalid or duplicate domain")
    ids = set()
    counts = {n: 0 for n in names}
    for i, c in enumerate(cats, 1):
        if c.get("id") != f"NAV-{i:03d}" or c.get("group") not in counts:
            raise ValueError("Unstable category identifier or unknown group")
        if not c.get("module_boundary", "").startswith("proposed/") or not c.get("name"):
            raise ValueError("Each category needs a distinct proposed module and name")
        counts[c["group"]] += 1
        checks = c.get("checks")
        if not isinstance(checks, list) or len(checks) != 3:
            raise ValueError("Every category requires 3 named atomic checks")
        for j, item in enumerate(checks):
            cid = f'{c["id"]}-{"ABC"[j]}'
            if item.get("id") != cid or cid in ids or not item.get("assertion"):
                raise ValueError("Missing/duplicate check or unstable ID")
            if item.get("status") != "not_run" or item.get("evidence") is not None:
                raise ValueError("Do not invent test outcomes or evidence")
            if any(k in item for k in ("score", "rank", "passed", "failed")):
                raise ValueError("Unexecuted checks may not have scores or results")
            ids.add(cid)
    if any(n != 6 for n in counts.values()) or len(ids) != 216:
        raise ValueError("Every domain must have exactly six categories and 18 unique checks")
    return {"domains":len(domains),"categories":len(cats),"atomic_checks":len(ids),"tested_in_this_suite":0,"out_of_ten_ranking":None,"check_status":"planned_not_run"}

def main() -> None:
    print(json.dumps(validate(json.loads(REGISTRY.read_text(encoding="utf-8"))), indent=2))

if __name__ == "__main__":
    main()
