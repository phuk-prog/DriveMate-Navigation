"""Read-only TURN-001 investigation for five unresolved Greater Manchester junctions.

This is a bounded MAP-DERIVED topology diagnostic, not an independent traffic-law
oracle. No routing-engine code, frozen test contract, or verdict is altered.
It explores all node/way-attributed directed arcs, not just DMN's search algorithm.
Via-way and conditional rules are explicitly not certified by this diagnostic.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

from benchmarks import turn001_restrictions as t

IDS = ("10558420", "13613008", "16644804", "4853555", "7615778")
OUTPUT = t.ROOT / "results" / "turn001-no-route5"
MAX_STATES = 400_000


def rules_by_node(clip: t.Clip, exclude: str | None = None) -> tuple[dict, dict]:
    rules = defaultdict(list)
    gaps = Counter()
    for rid, (tags, members) in clip.relations.items():
        if rid == exclude or not t._applies_to_cars(tags):
            continue
        if any(k.endswith(":conditional") for k in tags):
            gaps["conditional_not_applied"] += 1
            continue
        rule = t._rule(tags) or ""
        if not rule.startswith(("no_", "only_")):
            gaps["other_restriction_value"] += 1
            continue
        frm = [r for typ, r, role in members if role == "from" and typ == "way"]
        to = [r for typ, r, role in members if role == "to" and typ == "way"]
        via = [r for typ, r, role in members if role == "via" and typ == "node"]
        via_w = [r for typ, r, role in members if role == "via" and typ == "way"]
        if via_w or len(via) != 1 or len(frm) != 1 or len(to) != 1:
            gaps["complex_relation_not_applied"] += 1
            continue
        rules[via[0]].append((rid, rule, frm[0], to[0]))
    return rules, dict(gaps)


def blocked(rules: dict, prev: str, at: str, nxt: str, in_way: str, out_way: str) -> bool:
    for _, rule, frm, to in rules.get(at, ()):
        if in_way != frm:
            continue
        # Mirror the TURN-001 node audit's same-way U-turn semantics.
        match = (nxt == prev) if to == frm else out_way == to
        if rule.startswith("no_") and match or rule.startswith("only_") and not match:
            return True
    return False


def explore(clip: t.Clip, geom: dict, *, enforce_access: bool, enforce_turns: bool,
            exclude_relation: str | None = None) -> dict:
    adjacency = defaultdict(list)
    ways_used = 0
    for wid, (refs, tags) in clip.ways.items():
        if tags.get("highway") not in t.CAR_HIGHWAYS or tags.get("area") == "yes":
            continue
        if enforce_access and not clip.drivable(tags):
            continue
        ways_used += 1
        for a, b in zip(refs, refs[1:]):
            if a not in clip.coords or b not in clip.coords:
                continue
            if clip.can_travel(wid, a, b):
                adjacency[a].append((b, wid))
            if clip.can_travel(wid, b, a):
                adjacency[b].append((a, wid))
    origin = tuple(geom["origin_segment"])
    dest = tuple(geom["destination_segment"])
    start_way, finish_way = geom["from_way"], geom["exit_way"]
    if (origin[1], start_way) not in adjacency[origin[0]]:
        return {"found": False, "reason": "start_segment_not_car_traversable",
                "ways_considered": ways_used}
    if (dest[1], finish_way) not in adjacency[dest[0]]:
        return {"found": False, "reason": "destination_segment_not_car_traversable",
                "ways_considered": ways_used}

    rules, gaps = rules_by_node(clip, exclude_relation) if enforce_turns else ({}, {})
    start = (origin[0], origin[1], start_way)
    queue = deque([start])
    parent = {start: None}
    target = None
    while queue:
        prev, at, way = state = queue.popleft()
        if (prev, at, way) == (dest[0], dest[1], finish_way):
            target = state
            break
        for nxt, other_way in adjacency[at]:
            nxtstate = (at, nxt, other_way)
            if nxtstate in parent:
                continue
            if enforce_turns and blocked(rules, prev, at, nxt, way, other_way):
                continue
            parent[nxtstate] = state
            if len(parent) >= MAX_STATES:
                return {"found": None, "reason": "state_limit",
                        "states": len(parent), "unjudged_relations": gaps}
            queue.append(nxtstate)
    out = {"found": target is not None, "states": len(parent),
           "ways_considered": ways_used, "unjudged_relations": gaps}
    if target:
        steps = []
        while target is not None:
            steps.append(target)
            target = parent[target]
        steps.reverse()
        nodes = [steps[0][0]] + [s[1] for s in steps]
        audit = t.audit_route(clip, nodes)
        out.update({"path_nodes": len(nodes), "route_audit": audit,
                    "path_start": nodes[:6], "path_end": nodes[-6:]})
    return out


def main() -> int:
    prepared_path = t.WORK / "prepared.json"
    cohort_path = t.COHORT
    cohort = json.loads(cohort_path.read_text())
    prepared_bytes = prepared_path.read_bytes()
    expected_prepared = "8500d8f3d9cf99660fcc3267ad422134fce87cbb946fe25f6940763546707bf3"
    expected_cohort = "f2949a8a9aab40b7f62bc658cf92778f440ab5cdcc7ffcc755e21dc1b83c391c"
    if hashlib.sha256(prepared_bytes).hexdigest() != expected_prepared:
        raise SystemExit("Frozen prepared.json SHA mismatch")
    if t.sha256_file(cohort_path) != expected_cohort:
        raise SystemExit("Frozen cohort SHA mismatch")
    if cohort.get("source_sha256") != "2a8ef8e1f2533cb009b1ce248a6bf4eaabdd47e03979e64e24cd844f3b22acba":
        raise SystemExit("Frozen source SHA mismatch")
    prepared = {str(v["relation"]): v for v in json.loads(prepared_bytes)}
    relations = {str(c["relation"]): c for c in cohort["cases"]}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    findings = {}
    for rid in IDS:
        rec = prepared[rid]
        geom = rec["geometry"]
        assert geom["status"] == "TESTABLE", (rid, geom["status"])
        raw = (t.WORK / "cases" / rid / "clip.osm").read_bytes()
        if hashlib.sha256(raw).hexdigest() != rec["clip_sha256"]:
            raise RuntimeError(f"{rid}: clip SHA mismatch")
        clip = t.Clip(raw)
        via = [str(r) for typ, r, role in relations[rid]["members"] if role == "via" and typ == "n"]
        v = via[0]
        selected = {}
        for role, way in (("from", geom["from_way"]), ("finish", geom["exit_way"])):
            tags = clip.ways[way][1]
            selected[role] = {"way": way, "name": tags.get("name"),
                              "highway": tags.get("highway"), "oneway": tags.get("oneway"),
                              "access": {k: tags[k] for k in ("motorcar", "motor_vehicle", "vehicle", "access") if k in tags}}
        for label, access, restrictions, excluded in (
            ("permissive_without_turn_rules", False, False, None),
            ("permissive_with_via_node_rules", False, True, None),
            ("strict_with_via_node_rules", True, True, None),
            ("strict_without_tested_relation", True, True, rid),
        ):
            selected[label] = explore(clip, geom, enforce_access=access,
                                      enforce_turns=restrictions, exclude_relation=excluded)
        findings[rid] = {"restriction": relations[rid]["tags"], "members": relations[rid]["members"],
                         "via_node": v, "via_location": clip.coords.get(v),
                         "origin": geom["origin"], "destination": geom["destination"],
                         "start_and_finish": selected,
                         "barrier_nodes_present": sum(1 for e in __import__("xml.etree.ElementTree", fromlist=["ElementTree"]).fromstring(raw).iter("node")
                                                      if any(tg.get("k") == "barrier" for tg in e.findall("tag")))}
        compact = {k: selected[k].get("found") for k in selected if k not in ("from", "finish")}
        print(rid, relations[rid]["tags"].get("restriction"), compact, flush=True)

    record = {"contract": "TURN-001 NO-ROUTE-5 focused graph review v1",
              "limitations": ["map-derived only; does not prove UK legal rights",
                              "base clips only; archived engine retests already used 3x wider clips",
                              "via-way and conditional restrictions are not applied by graph diagnostic",
                              "barriers, gate access conditions and practical turn-round space are not adjudicated",
                              "no native reference engine rerun; original 2026-10-17 CI artifacts are historical"],
              "source_sha256": cohort["source_sha256"],
              "cohort_sha256": expected_cohort, "prepared_sha256": expected_prepared, "cases": findings}
    (OUTPUT / "summary.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    with (OUTPUT / "brief.md").open("w") as f:
        f.write("### TURN-001: five unresolved junctions (map-derived diagnostic)\n\n")
        f.write("| Relation | Rule | One-way topology only | All highways + via-node bans | Car-access + via-node bans | Remove tested relation |\n")
        f.write("|---|---|---|---|---|---|\n")
        for rid, row in findings.items():
            d = row["start_and_finish"]
            def status(key):
                obj = d[key]
                return "reachable" if obj["found"] is True else "not reachable" if obj["found"] is False else "unresolved (limit)"
            f.write(f"| {rid} | {row['restriction'].get('restriction')} | "
                    f"{status('permissive_without_turn_rules')} | {status('permissive_with_via_node_rules')} | "
                    f"{status('strict_with_via_node_rules')} | {status('strict_without_tested_relation')} |\n")
        f.write("\n**Not proof of road legality.** OSM snapshot is not an independent"
                " sign/TRO/physical-layout oracle. Via-way/conditional restrictions,"
                " barrier passability and actual turnaround geometry need separate verification.\n")
    print((OUTPUT / "brief.md").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
