"""BARRIER-001: route-level check of bollards and gates on real Greater Manchester roads.

Category 1 (map data and road graph), sibling of TURN-001 and reusing its clips,
engine runners and whole-route audit. For a frozen, pre-registered sample of real
OpenStreetMap barrier nodes lying in the middle of a car road, every engine gets the
SAME small clip of the SAME hashed snapshot and is asked for a car route from just
before the barrier to just after it, so the direct route passes through it.

Barrier groups (from the node's own tags, decided before any engine ran):

closed         bollard, block, cycle barrier... or any barrier tagged no for cars
open           any barrier explicitly open to cars (yes/permissive/designated)
untagged_gate  gate, lift gate, swing gate with no access tags (OSM: unknown)
restricted     private/destination/delivery/... (depends on who is driving)

Verdicts per engine and case (never invented, never pooled across unlike runs):

PASS                  closed: route avoids the barrier; open: route goes through it
FAIL_THROUGH_BARRIER  route drives through a closed barrier
AVOIDED_OPEN_BARRIER  route detours round (or refuses) an explicitly open barrier
THROUGH_UNCERTAIN / AVOIDED_UNCERTAIN   untagged gate or restricted: reported, not judged
SAFE_NO_ROUTE         no route (re-asked on a clip three times wider)
UNRESOLVED_SNAP       route does not start and finish on the exact test segments
ENDPOINT_WITHHELD_BY_POLICY / ENGINE_REJECTED_MAP / ERROR   as in TURN-001

Every route is also audited against every one-way and turn restriction (TURN-001
audit) and every other barrier node it crosses. A DMN control with the tested
barrier's tags removed marks DISCRIMINATING cases (the unblocked route uses the
barrier); an OSRM control run does the same as a harness check. Source OSM is not
independent legal truth.

v1.1 (harness fix before any baseline was reported): "through" means the route
CROSSES the barrier (arrives from one side and leaves on the other). v1 also counted
driving up to a barrier and turning round there, which is legal; run 39022261422
showed every OSRM and Valhalla "fail" was such a turn-round.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from benchmarks import turn001_restrictions as t1

ROOT = t1.ROOT
WORK = ROOT / "results" / "barrier001"
COHORT = ROOT / "config" / "barrier001-cohort.json"
PREPARED = ROOT / "config" / "barrier001-prepared.json"
SOURCE = ROOT / "results" / "turn001" / "gm.osm.pbf"  # pinned on data/turn001-snapshot
CONTRACT = "BARRIER-001 v1.1"
ACCESS_KEYS = ("motorcar", "motor_vehicle", "vehicle", "access")
OPEN_VALUES = {"yes", "permissive", "designated"}
RESTRICTED_VALUES = {"private", "destination", "delivery", "customers", "permit", "agricultural",
                     "forestry", "agricultural;forestry", "emergency", "official"}
BLOCKING_KINDS = {"bollard", "block", "bus_trap", "cycle_barrier", "jersey_barrier", "planter",
                  "motorcycle_barrier", "chain", "log", "debris", "fence", "wall", "rope"}
GATE_KINDS = {"gate", "lift_gate", "swing_gate", "sliding_gate"}
PASSABLE_KINDS = {"kerb", "cattle_grid", "entrance", "height_restrictor", "toll_booth",
                  "border_control", "speed_camera"}
# Frozen stratum quotas (chosen before any engine was run).
QUOTAS = {
    ("closed", "bollard"): 30, ("closed", "cycle_barrier"): 10, ("closed", "block"): 10,
    ("closed", "other"): 10, ("open", "*"): 15, ("untagged_gate", "gate"): 15,
    ("untagged_gate", "lift_gate"): 10, ("untagged_gate", "swing_gate"): 5, ("restricted", "*"): 10,
}
SEGMENT_M = 25.0  # test points sit on the first segment ending at least this far from the barrier


def barrier_class(tags: dict[str, str]) -> str | None:
    """closed / open / untagged_gate / restricted / conditional / passable / other, or None."""
    kind = tags.get("barrier")
    if not kind:
        return None
    if any(k.endswith(":conditional") for k in tags):
        return "conditional"
    value = next((tags[k] for k in ACCESS_KEYS if k in tags), None)
    if value == "no":
        return "closed"
    if value in OPEN_VALUES:
        return "open"
    if value in RESTRICTED_VALUES:
        return "restricted"
    if value is not None:
        return "other"
    if kind in BLOCKING_KINDS:
        return "closed"
    if kind in GATE_KINDS:
        return "untagged_gate"
    if kind in PASSABLE_KINDS:
        return "passable"
    return "other"


def stratum(tags: dict[str, str]) -> tuple[str, str] | None:
    group = barrier_class(tags)
    kind = tags.get("barrier", "")
    if group == "closed":
        return group, kind if kind in ("bollard", "cycle_barrier", "block") else "other"
    if group in ("open", "restricted"):
        return group, "*"
    if group == "untagged_gate" and kind in ("gate", "lift_gate", "swing_gate"):
        return group, kind
    return None


# --------------------------------------------------------------------------- cohort
_OPL_ESCAPE = re.compile(r"%([0-9a-fA-F]+)%")


def _opl_tags(field: str) -> dict[str, str]:
    out = {}
    for item in field[1:].split(",") if len(field) > 1 else ():
        k, _, v = item.partition("=")
        out[_OPL_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), k)] = \
            _OPL_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), v)
    return out


def _line_structure(ways: list[tuple[str, list[str]]], node: str) -> bool:
    """Barrier sits in the middle of one car road (or joins exactly two), 2+ segments each side."""
    if len(ways) == 1:
        refs = ways[0][1]
        i = refs.index(node)
        return refs.count(node) == 1 and 2 <= i <= len(refs) - 3
    if len(ways) == 2:
        return all(r.count(node) == 1 and node in (r[0], r[-1]) and len(r) >= 3 for _, r in ways)
    return False


def select(source: Path) -> None:
    if COHORT.exists():
        raise RuntimeError("BARRIER-001 frozen cohort exists; select a new named cohort instead of overwriting")
    WORK.mkdir(parents=True, exist_ok=True)
    nodes_opl, ways_opl, hw = WORK / "barriers.opl", WORK / "ways.opl", WORK / "hw.osm.pbf"
    subprocess.run(["osmium", "tags-filter", str(source), "n/barrier", "-R", "-O", "-o", str(nodes_opl),
                    "-f", "opl,add_metadata=false"], check=True)
    subprocess.run(["osmium", "tags-filter", str(source), "w/highway", "-O", "-o", str(hw)], check=True)
    subprocess.run(["osmium", "cat", str(hw), "-t", "way", "-O", "-o", str(ways_opl),
                    "-f", "opl,add_metadata=false"], check=True)
    barriers: dict[str, dict] = {}
    for line in nodes_opl.read_text().splitlines():
        parts = line.split(" ")
        tags = _opl_tags(next(p for p in parts if p.startswith("T")))
        lon = float(next(p for p in parts if p.startswith("x"))[1:])
        lat = float(next(p for p in parts if p.startswith("y"))[1:])
        barriers[parts[0][1:]] = {"tags": tags, "lat": lat, "lon": lon}
    on_ways: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)
    for line in ways_opl.read_text().splitlines():
        parts = line.split(" ")
        tags = _opl_tags(next((p for p in parts if p.startswith("T")), "T"))
        if not t1.Clip.drivable(tags):
            continue
        refs = [r[1:] for r in next(p for p in parts if p.startswith("N"))[1:].split(",")]
        for r in refs:
            if r in barriers:
                on_ways[r].append((parts[0][1:], refs))
    found = []
    for node, ways in on_ways.items():
        key = stratum(barriers[node]["tags"])
        if key is None or not _line_structure(ways, node):
            continue
        found.append({"node": int(node), "stratum": list(key), "tags": barriers[node]["tags"],
                      "lat": barriers[node]["lat"], "lon": barriers[node]["lon"],
                      "ways": sorted(int(w) for w, _ in ways)})
    chosen = []
    for key, quota in QUOTAS.items():
        pool = [c for c in found if tuple(c["stratum"]) == key]
        pool.sort(key=lambda c: hashlib.sha256(f"BARRIER-001:{c['node']}".encode()).hexdigest())
        chosen.extend(pool[:quota])
    COHORT.write_text(json.dumps({
        "contract": CONTRACT,
        "frozen_before_engine_runs": True,
        "selection_rule": "barrier node inside one car road (or joining two) with 2+ segments each side; "
                          "per-stratum quota, ordered by sha256('BARRIER-001:'+node_id)",
        "quotas": {"/".join(k): v for k, v in QUOTAS.items()},
        "source_snapshot": source.name,
        "source_sha256": t1.sha256_file(source),
        "barrier_nodes_in_source": len(barriers),
        "available_by_stratum": dict(sorted(Counter("/".join(c["stratum"]) for c in found).items())),
        "cases": chosen,
    }, indent=1, sort_keys=True))
    for path in (nodes_opl, ways_opl, hw):
        path.unlink()
    print(f"Frozen {len(chosen)} cases of {len(found)} candidate barriers -> {COHORT}")


# --------------------------------------------------------------------------- clips
class BarrierClip(t1.Clip):
    """TURN-001 clip plus the tags of every barrier node."""

    def __init__(self, raw: bytes):
        super().__init__(raw)
        self.barriers: dict[str, dict[str, str]] = {}
        for e in ET.fromstring(raw).iter("node"):
            tags = {t.get("k"): t.get("v") for t in e.findall("tag")}
            if "barrier" in tags:
                self.barriers[e.get("id")] = tags


def _side(clip: t1.Clip, node: str, way: str, step: int) -> list[str]:
    refs = clip.ways[way][0]
    i = refs.index(node)
    return refs[i::step] if step == 1 else refs[i::-1]


def case_geometry(case: dict, clip: BarrierClip) -> dict:
    """Origin just before and destination just after the barrier, along the same road line."""
    b = str(case["node"])
    group = case["stratum"][0]
    ways = sorted(clip.node_ways.get(b, ()), key=int)
    if b not in clip.coords or [int(w) for w in ways] != case["ways"]:
        return {"status": "LINE_CHANGED_IN_CLIP", "group": group}
    if len(ways) == 1:
        sides = [(_side(clip, b, ways[0], -1), ways[0]), (_side(clip, b, ways[0], 1), ways[0])]
    else:
        sides = [(_side(clip, b, w, 1 if clip.ways[w][0][0] == b else -1), w) for w in ways]

    def pick(side: list[str]) -> int | None:
        walked = 0.0
        for k in range(len(side) - 1):
            walked += t1.metres(clip.coords[side[k]], clip.coords[side[k + 1]])
            if k >= 1 and (walked >= SEGMENT_M or k == len(side) - 2):
                return k
        return None

    for (a_side, a_way), (c_side, c_way) in (sides, sides[::-1]):
        ka, kc = pick(a_side), pick(c_side)
        if ka is None or kc is None:
            return {"status": "LINE_TOO_SHORT", "group": group}
        direct = list(reversed(a_side[:ka + 2])) + c_side[1:kc + 2]
        steps = [(a_way, x, y) for x, y in zip(direct, direct[1:])][:ka + 1] + \
                [(c_way, x, y) for x, y in zip(direct, direct[1:])][ka + 1:]
        if not all(clip.can_travel(w, x, y) for w, x, y in steps):
            continue
        others = [n for n in direct if n != b and barrier_class(clip.barriers.get(n, {})) not in (None, "passable", "open")]
        if others:
            return {"status": "OTHER_BARRIER_ON_LINE", "group": group, "other_barriers": others}
        o_seg, d_seg = [a_side[ka + 1], a_side[ka]], [c_side[kc], c_side[kc + 1]]

        def mid(seg):
            p, q = clip.coords[seg[0]], clip.coords[seg[1]]
            return [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2]
        return {"status": "TESTABLE", "group": group, "barrier": b, "kind": case["tags"].get("barrier"),
                "origin": mid(o_seg), "destination": mid(d_seg), "origin_segment": o_seg,
                "destination_segment": d_seg, "direct_path": direct}
    return {"status": "ONE_WAY_AGAINST_LINE", "group": group}


HALF_LAT, HALF_LON = t1.HALF_LAT, t1.HALF_LON


def prepare(source: Path) -> None:
    cohort = json.loads(COHORT.read_text())
    if t1.sha256_file(source) != cohort["source_sha256"]:
        raise SystemExit("Source snapshot does not match the frozen cohort")
    out = []
    for case in cohort["cases"]:
        folder = WORK / "cases" / str(case["node"])
        folder.mkdir(parents=True, exist_ok=True)
        lat, lon = case["lat"], case["lon"]
        bbox = f"{lon-HALF_LON:.6f},{lat-HALF_LAT:.6f},{lon+HALF_LON:.6f},{lat+HALF_LAT:.6f}"
        pbf = folder / "clip.osm.pbf"
        subprocess.run(["osmium", "extract", "--overwrite", "--strategy", "complete_ways",
                        f"--bbox={bbox}", str(source), "-o", str(pbf)], check=True)
        subprocess.run(["osmium", "cat", "--overwrite", str(pbf), "-o", str(folder / "clip.osm"),
                        "-f", "osm,add_metadata=false"], check=True)
        raw = (folder / "clip.osm").read_bytes()
        out.append({"node": case["node"], "stratum": case["stratum"], "bbox": bbox,
                    "clip_sha256": hashlib.sha256(raw).hexdigest(), "clip_bytes": len(raw),
                    "geometry": case_geometry(case, BarrierClip(raw))})
    text = json.dumps(out, indent=1)
    if PREPARED.exists() and PREPARED.read_text() != text:
        raise SystemExit("Prepared clips differ from the frozen config/barrier001-prepared.json")
    PREPARED.write_text(text)
    (WORK / "prepared.json").write_text(text)
    print(Counter(r["geometry"]["status"] for r in out))


WIDE_SCALE = 3


def wide_clip(record: dict, source: Path = SOURCE) -> Path:
    """Same case on a clip WIDE_SCALE times wider (roads, restrictions and barriers)."""
    folder = WORK / "cases" / str(record["node"]) / "wide"
    if (folder / "clip.osm").exists():
        return folder
    folder.mkdir(parents=True, exist_ok=True)
    w, s, e, n = map(float, record["bbox"].split(","))
    cx, cy, hx, hy = (w + e) / 2, (s + n) / 2, (e - w) / 2 * WIDE_SCALE, (n - s) / 2 * WIDE_SCALE
    raw_pbf = folder / "all.osm.pbf"
    subprocess.run(["osmium", "extract", "--overwrite", "--strategy", "complete_ways",
                    f"--bbox={cx-hx:.6f},{cy-hy:.6f},{cx+hx:.6f},{cy+hy:.6f}", str(source), "-o", str(raw_pbf)],
                   check=True)
    subprocess.run(["osmium", "tags-filter", "--overwrite", str(raw_pbf), "w/highway", "r/type=restriction",
                    "n/barrier", "-o", str(folder / "clip.osm.pbf")], check=True)
    raw_pbf.unlink()
    subprocess.run(["osmium", "cat", "--overwrite", str(folder / "clip.osm.pbf"), "-o", str(folder / "clip.osm"),
                    "-f", "osm,add_metadata=false"], check=True)
    return folder


def without_barrier(raw: bytes, node: str) -> bytes:
    """The clip with the tested barrier node's tags removed (control)."""
    root = ET.fromstring(raw)
    for e in root.iter("node"):
        if e.get("id") == node:
            for tag in list(e.findall("tag")):
                e.remove(tag)
    return ET.tostring(root)


# --------------------------------------------------------------------------- verdicts
def crosses(nodes: list[str], node: str) -> bool:
    """The route passes over `node`: different neighbours before and after it."""
    return any(nodes[i - 1] != nodes[i + 1] for i in range(1, len(nodes) - 1) if nodes[i] == node)


def audit_barriers(clip: BarrierClip, nodes: list[str], tested: str) -> dict:
    closed, uncertain = [], []
    for n in dict.fromkeys(nodes[1:-1]):
        if n == tested or n not in clip.barriers or not crosses(nodes, n):
            continue
        group = barrier_class(clip.barriers[n])
        if group == "closed":
            closed.append(f"barrier:{n}:{clip.barriers[n]['barrier']}")
        elif group in ("untagged_gate", "restricted", "conditional", "other"):
            uncertain.append(f"barrier:{n}:{clip.barriers[n]['barrier']}:{group}")
    return {"other_closed_barriers": closed, "other_uncertain_barriers": uncertain}


def verdict(clip: BarrierClip, geom: dict, nodes: list[str] | None, error: str | None = None) -> dict:
    if error == "ENDPOINT_WITHHELD":
        return {"verdict": "ENDPOINT_WITHHELD_BY_POLICY"}
    if error is not None:
        return {"verdict": "ERROR", "detail": error[:300]}
    if nodes is None:
        return {"verdict": "SAFE_NO_ROUTE"}
    b = geom["barrier"]
    through = crosses(nodes, b)
    rules = t1.audit_route(clip, nodes)
    extra = {"nodes": len(nodes), "path": nodes, "through_barrier": through, **rules,
             **audit_barriers(clip, nodes, b)}
    if extra["other_closed_barriers"]:
        extra["route_legal"] = "ILLEGAL"
        extra["violations"] = sorted(extra["violations"] + extra["other_closed_barriers"])
    anchored = nodes[:2] == list(geom["origin_segment"]) and nodes[-2:] == list(geom["destination_segment"])
    group = geom["group"]
    if group == "closed" and through:
        return {"verdict": "FAIL_THROUGH_BARRIER", **extra}
    if not anchored:
        return {"verdict": "UNRESOLVED_SNAP", **extra}
    if group == "closed":
        return {"verdict": "PASS", **extra}
    if group == "open":
        return {"verdict": "PASS" if through else "AVOIDED_OPEN_BARRIER", **extra}
    return {"verdict": "THROUGH_UNCERTAIN" if through else "AVOIDED_UNCERTAIN", **extra}


def no_route_verdict(geom: dict, entry: dict) -> dict:
    """An explicitly open barrier that leaves no route is over-cautious, not safe."""
    if geom["group"] == "open" and entry.get("verdict") == "SAFE_NO_ROUTE":
        return {**entry, "verdict": "AVOIDED_OPEN_BARRIER", "no_route": True}
    return entry


# --------------------------------------------------------------------------- runs
ENGINES = ("DMN", "OSRM", "GraphHopper", "Valhalla")


def _provenance(engine: str) -> dict:
    frozen = json.loads(COHORT.read_text())
    if not frozen.get("frozen_before_engine_runs") or not frozen.get("source_sha256"):
        raise RuntimeError("BARRIER-001 source cohort is not frozen")
    return {"schema": 1, "engine": engine, "revision": t1._revision(),
            "cohort_sha256": t1.sha256_file(COHORT), "source_sha256": frozen["source_sha256"],
            "prepared_sha256": t1.sha256_file(PREPARED), "runner_sha256": t1.sha256_file(Path(__file__))}


def _dmn(raw: bytes, geom: dict) -> tuple[list[str] | None, str | None, str | None]:
    return t1.dmn_route(raw, geom)


def run(engine: str, *, control: bool = False, only: set[str] | None = None) -> None:
    prepared = json.loads(PREPARED.read_text())
    name = f"{engine}-control" if control else engine
    out = WORK / f"run-{name}.json"
    results: dict = {"_provenance": _provenance(name)}
    for record in prepared:
        node, geom = str(record["node"]), record["geometry"]
        if geom["status"] != "TESTABLE" or (only and node not in only):
            continue
        folder = WORK / "cases" / node
        raw = (folder / "clip.osm").read_bytes()
        if hashlib.sha256(raw).hexdigest() != record["clip_sha256"]:
            raise RuntimeError(f"BARRIER-001 {node}: prepared clip bytes changed")
        clip = BarrierClip(raw)
        entry: dict = {"clip_sha256": record["clip_sha256"]}
        if engine == "DMN":
            began = time.perf_counter()
            nodes, error, rejected = _dmn(raw, geom)
            entry["ms_import_and_route"] = round((time.perf_counter() - began) * 1000, 1)
            entry.update({"verdict": "ENGINE_REJECTED_MAP", "detail": rejected[:300]} if rejected
                         else verdict(clip, geom, nodes, error))
            c_nodes, _, c_rejected = _dmn(without_barrier(raw, node), geom)
            entry["control_without_barrier"] = ("REJECTED" if c_rejected else "NO_ROUTE" if c_nodes is None else
                                                "USES_BARRIER" if crosses(c_nodes, node) else "AVOIDS_BARRIER")
        elif control:
            ctrl = WORK / "control" / node
            ctrl.mkdir(parents=True, exist_ok=True)
            craw = without_barrier(raw, node)
            (ctrl / "clip.osm").write_bytes(craw)
            subprocess.run(["osmium", "cat", "--overwrite", str(ctrl / "clip.osm"), "-o", str(ctrl / "clip.osm.pbf")],
                           check=True)
            entry.update(t1.engine_case(engine, ctrl, BarrierClip(craw), geom, judge=verdict))
            # judged against the real barrier: driving through it is what the control should show
            entry["through_barrier"] = crosses(entry.get("path", []), node)
        else:
            entry.update(t1.engine_case(engine, folder, clip, geom, judge=verdict))
        if entry.get("verdict") == "SAFE_NO_ROUTE" and not control:
            wide = wide_clip(record)
            wraw = (wide / "clip.osm").read_bytes()
            wclip = BarrierClip(wraw)
            if engine == "DMN":
                nodes, error, rejected = _dmn(wraw, geom)
                wide_entry = ({"verdict": "ENGINE_REJECTED_MAP", "detail": rejected[:300]} if rejected
                              else verdict(wclip, geom, nodes, error))
            else:
                wide_entry = t1.engine_case(engine, wide, wclip, geom, judge=verdict)
            entry["wide_clip"] = {"scale": WIDE_SCALE, "clip_sha256": hashlib.sha256(wraw).hexdigest(), **wide_entry}
        results[node] = entry
        out.write_text(json.dumps(results, indent=1, sort_keys=True))
        print(node, entry.get("verdict"), entry.get("detail", "")[:100], flush=True)


def final(geom: dict, entry: dict) -> dict:
    if entry.get("verdict") == "SAFE_NO_ROUTE" and "wide_clip" in entry:
        entry = {**entry["wide_clip"], "base_clip_verdict": "SAFE_NO_ROUTE"}
    return no_route_verdict(geom, entry)


def _ms(values: list[float]) -> dict:
    if not values:
        return {"median": None, "p95": None, "samples": 0}
    xs = sorted(values)
    return {"median": round(statistics.median(xs), 1), "p95": xs[min(len(xs) - 1, round(0.95 * (len(xs) - 1)))],
            "samples": len(xs)}


def score() -> None:
    prepared = {str(r["node"]): r for r in json.loads(PREPARED.read_text())}
    runs = {e: json.loads((WORK / f"run-{e}.json").read_text()) for e in ENGINES if (WORK / f"run-{e}.json").exists()}
    for name, record in runs.items():
        if record.get("_provenance") != _provenance(name):
            raise RuntimeError(f"BARRIER-001 {name}: stale/unprovenanced result")
    testable = [n for n, r in prepared.items() if r["geometry"]["status"] == "TESTABLE"]
    dmn = runs.get("DMN", {})
    discriminating = [n for n in testable if dmn.get(n, {}).get("control_without_barrier") == "USES_BARRIER"]
    finals = {e: {n: final(prepared[n]["geometry"], r[n]) for n in testable if n in r} for e, r in runs.items()}

    def legal_pass(e, n):
        f = finals[e].get(n, {})
        return f.get("verdict") == "PASS" and f.get("route_legal") == "LEGAL"
    summary = {
        "contract": CONTRACT, "revision": t1._revision(), "cohort_sha256": t1.sha256_file(COHORT),
        "prepared_sha256": t1.sha256_file(PREPARED),
        "source_sha256": json.loads(COHORT.read_text())["source_sha256"],
        "cases_frozen": len(prepared),
        "geometry_status": dict(Counter(r["geometry"]["status"] for r in prepared.values())),
        "testable_by_group": dict(Counter(prepared[n]["geometry"]["group"] for n in testable)),
        "testable_cases": len(testable), "discriminating_cases": len(discriminating),
        "truth": "OpenStreetMap barrier tags in the hashed snapshot; not independent UK legal truth",
        "engines": {},
    }
    for name, res in finals.items():
        by_group: dict[str, Counter] = defaultdict(Counter)
        for n, f in res.items():
            by_group[prepared[n]["geometry"]["group"]][f["verdict"]] += 1
        ms_key = "ms_import_and_route" if name == "DMN" else "warm_query_ms"
        summary["engines"][name] = {
            "by_group": {g: dict(c) for g, c in sorted(by_group.items())},
            "discriminating": dict(Counter(res[n]["verdict"] for n in discriminating if n in res)),
            "pass_and_route_legal": sum(1 for n in res if legal_pass(name, n)),
            "fail_cases": sorted(n for n, f in res.items() if f["verdict"] == "FAIL_THROUGH_BARRIER"),
            "avoided_open_cases": sorted(n for n, f in res.items() if f["verdict"] == "AVOIDED_OPEN_BARRIER"),
            "other_rule_violations": {n: f["violations"] for n, f in res.items() if f.get("route_legal") == "ILLEGAL"
                                      and f["verdict"] != "FAIL_THROUGH_BARRIER"},
            "no_route_but_legal_route_exists": {
                n: sorted(e for e in finals if legal_pass(e, n)) for n, f in res.items()
                if f["verdict"] == "SAFE_NO_ROUTE" and any(legal_pass(e, n) for e in finals)},
            "endpoint_withheld": sorted(n for n, f in res.items() if f["verdict"] == "ENDPOINT_WITHHELD_BY_POLICY"),
            "query_ms": _ms([runs[name][n][ms_key] for n in testable if runs[name].get(n, {}).get(ms_key) is not None]),
            "executed": len(res),
        }
    (WORK / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
    print(json.dumps(summary, indent=1)[:3000])


def brief() -> int:
    """A few lines for the job page; exit 1 if DMN drives through a closed barrier."""
    s = json.loads((WORK / "summary.json").read_text())
    lines = [f"{s['contract']} @ {s['revision'][:12]}: {s['testable_cases']} testable "
             f"{s['testable_by_group']}, {s['discriminating_cases']} discriminating"]
    for name, e in s["engines"].items():
        groups = "; ".join(f"{g}: " + ", ".join(f"{k} {v}" for k, v in sorted(c.items()))
                           for g, c in e["by_group"].items())
        lines.append(f"- {name}: {groups} | legal passes {e['pass_and_route_legal']}; "
                     f"other rule breaks {len(e['other_rule_violations'])}; "
                     f"no-route though legal route exists {len(e['no_route_but_legal_route_exists'])}; "
                     f"median {e['query_ms']['median']} ms")
    bad = []
    if s["engines"].get("DMN", {}).get("fail_cases"):
        bad.append("DMN drove through a closed barrier")
    control = WORK / "run-OSRM-control.json"
    if control.exists():
        ctrl = {k: v for k, v in json.loads(control.read_text()).items() if not k.startswith("_")}
        dmn = json.loads((WORK / "run-DMN.json").read_text())
        disc = [k for k in ctrl if dmn.get(k, {}).get("control_without_barrier") == "USES_BARRIER"]
        through = sum(1 for k in disc if ctrl[k].get("through_barrier"))
        lines.append(f"- harness check (OSRM with the tested barrier removed): goes through it in {through} "
                     f"of {len(disc)} discriminating cases")
        if disc and through == 0:
            bad.append("harness check: control never drove through the removed barrier")
    lines.append("RESULT: " + ("; ".join(bad) if bad else "OK"))
    print("\n".join(lines))
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ("select", "prepare"):
        sub.add_parser(cmd).add_argument("--source", type=Path, default=SOURCE)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--engine", choices=ENGINES, required=True)
    run_parser.add_argument("--control", action="store_true", help="remove the tested barrier (harness check)")
    run_parser.add_argument("--only", nargs="*")
    sub.add_parser("score")
    sub.add_parser("brief")
    args = parser.parse_args()
    if args.cmd == "select":
        select(args.source)
    elif args.cmd == "prepare":
        prepare(args.source)
    elif args.cmd == "run":
        run(args.engine, control=args.control, only=set(args.only or ()) or None)
    elif args.cmd == "score":
        score()
    else:
        return brief()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
