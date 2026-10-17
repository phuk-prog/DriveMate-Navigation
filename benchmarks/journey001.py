"""JOURNEY-001 (run B1): real Greater Manchester junctions and roundabouts, four engines.

One shared run, five separately scored categories (owner-approved grouping, 17 Oct
2026; never one combined score):

5  route computation and validity  route returned, on the exact test segments, legal
6  route quality                      route length against the shortest legal anchored
                                      route any engine found for the same case
8  junction turns                     instruction at the junction: left / right / straight
9  roundabout exits                   exit number at a single-carriageway roundabout
11 route line adherence               how far the engine's drawn line strays from the
                                      roads it says it uses (DMN draws OSM nodes: n/a)

Truth comes only from the map itself (hashed OSM snapshot): the turn class from the
bearing change at the junction node, the exit number from counting ring nodes where a
car may leave, legality from the TURN-001/BARRIER-001/ACCESS-001 audits. It is
map-derived, not independent UK road law. Instructions are judged only when the
engine's route makes the intended movement at the junction; otherwise NOT_JUDGED.

Turn classes (frozen): straight below 25 degrees, left/right 60-120 degrees; junctions
in between, U-turns and junctions that are the via node of a turn restriction are not
selected. Lanes (10) and speed limits (15) are run B2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

from benchmarks import access001_route as a1
from benchmarks import barrier001_route as b1
from benchmarks import extra_engines as xe
from benchmarks import turn001_restrictions as t1

ROOT = t1.ROOT
WORK = ROOT / "results" / "journey001"
COHORT = ROOT / "config" / "journey001-cohort.json"
PREPARED = ROOT / "config" / "journey001-prepared.json"
CONTRACT = "JOURNEY-001 v1.2"
# v1.1 (owner, 17 Oct 2026): every road a car may leave by counts as a roundabout exit,
# service roads included, so the v1 "unclear minor exit" verdict is retired.
# v1.2 (owner, 17 Oct 2026): openrouteservice and BRouter added; all engines run through
# benchmarks/extra_engines.py and share its start/finish path matching fix.
STRAIGHT_MAX, TURN_MIN, TURN_MAX = 25.0, 60.0, 120.0
JUNCTION_HIGHWAYS = t1.CAR_HIGHWAYS - {"service", "living_street", "motorway", "motorway_link"}
QUOTAS = {("turn", "left"): 12, ("turn", "right"): 12, ("turn", "straight"): 12,
          ("roundabout", "exit1"): 8, ("roundabout", "exit2"): 8, ("roundabout", "exit3"): 8}
NEAR_M = 15.0  # an instruction belongs to the junction if it is placed this close to it
ROUNDABOUT_NEAR_M = 40.0


def turn_class(delta: float) -> str | None:
    d = abs(delta)
    if d < STRAIGHT_MAX:
        return "straight"
    if TURN_MIN <= d <= TURN_MAX:
        return "right" if delta > 0 else "left"
    return None


def delta_deg(p, j, q) -> float:
    return (t1.bearing(j, q) - t1.bearing(p, j) + 180) % 360 - 180


def _h(label: str) -> str:
    return hashlib.sha256(f"JOURNEY-001:{label}".encode()).hexdigest()


# --------------------------------------------------------------------------- cohort
def select(source: Path) -> None:
    if COHORT.exists():
        raise RuntimeError("JOURNEY-001 frozen cohort exists; select a new named cohort instead of overwriting")
    WORK.mkdir(parents=True, exist_ok=True)
    roads = _roads(source)
    opl = WORK / "all.opl"
    subprocess.run(["osmium", "cat", str(roads), "-O", "-o", str(opl), "-f", "opl,add_metadata=false"], check=True)
    coords, ways, via_nodes = {}, {}, set()
    for line in opl.read_text().splitlines():
        parts = line.split(" ")
        kind, oid = parts[0][0], parts[0][1:]
        if kind == "n":
            x = next(p for p in parts if p.startswith("x"))[1:]
            y = next(p for p in parts if p.startswith("y"))[1:]
            if x and y:
                coords[oid] = (float(y), float(x))
        elif kind == "w":
            tags = b1._opl_tags(next((p for p in parts if p.startswith("T")), "T"))
            if t1.Clip.drivable(tags):
                ways[oid] = ([r[1:] for r in next(p for p in parts if p.startswith("N"))[1:].split(",")], tags)
        elif kind == "r":
            members = next((p for p in parts if p.startswith("M")), "M")[1:]
            for m in members.split(",") if members else ():
                if m.startswith("n") and m.endswith("@via"):
                    via_nodes.add(m[1:].split("@")[0])
    node_ways = defaultdict(set)
    for w, (refs, _) in ways.items():
        for n in refs:
            node_ways[n].add(w)
    ring = lambda tags: tags.get("junction") in ("roundabout", "circular")  # noqa: E731
    found = []
    # junction turns: one case per node, first clean movement in sha256 order
    for node, ws in node_ways.items():
        if node in via_nodes or node not in coords or len(ws) < 2 \
                or any(ring(ways[w][1]) or ways[w][1].get("highway") not in JUNCTION_HIGHWAYS for w in ws):
            continue
        arms = []
        for w in sorted(ws):
            refs = ways[w][0]
            for i, n in enumerate(refs):
                if n == node:
                    arms += [(w, refs[j]) for j in (i - 1, i + 1) if 0 <= j < len(refs) and refs[j] in coords]
        if not 3 <= len(arms) <= 4:  # a T or crossroads (a road passing through counts as two arms)
            continue
        moves = []
        for (wa, p) in arms:
            for (wb, q) in arms:
                if wa == wb or p == q:
                    continue
                cls = turn_class(delta_deg(coords[p], coords[node], coords[q]))
                if cls:
                    moves.append((_h(f"{node}:{wa}:{p}:{wb}:{q}"), cls, wa, p, wb, q))
        if moves:
            _, cls, wa, p, wb, q = min(moves)
            found.append({"id": f"turn-{node}", "stratum": ["turn", cls], "node": int(node),
                          "lat": coords[node][0], "lon": coords[node][1],
                          "from_way": int(wa), "from_node": int(p), "to_way": int(wb), "to_node": int(q)})
    # roundabouts: single closed ring way, entry and exit spokes chosen in sha256 order
    for w, (refs, tags) in ways.items():
        if not ring(tags) or refs[0] != refs[-1] or len(refs) < 4 or any(r not in coords for r in refs):
            continue
        spokes = [n for n in refs[:-1] if len(node_ways[n]) > 1]
        if len(spokes) < 3:
            continue
        cy = sum(coords[n][0] for n in refs[:-1]) / (len(refs) - 1)
        cx = sum(coords[n][1] for n in refs[:-1]) / (len(refs) - 1)
        entry = min(spokes, key=lambda n: _h(f"{w}:{n}"))
        for k in (1, 2, 3):
            found.append({"id": f"roundabout-{w}-exit{k}", "stratum": ["roundabout", f"exit{k}"], "ring_way": int(w),
                          "entry_node": int(entry), "exit_number": k, "lat": round(cy, 7), "lon": round(cx, 7)})
    chosen = []
    for key, quota in QUOTAS.items():
        pool = sorted((c for c in found if tuple(c["stratum"]) == key), key=lambda c: _h(c["id"]))
        if key[0] == "roundabout":  # one exit number per roundabout, so cases stay independent
            used = {c["ring_way"] for c in chosen if "ring_way" in c}
            pool = [c for c in pool if c["ring_way"] not in used]
        chosen.extend(pool[:quota * 3])  # spare cases: prepare keeps the first `quota` testable ones
    COHORT.write_text(json.dumps({
        "contract": CONTRACT, "frozen_before_engine_runs": True,
        "selection_rule": "turn: node joining 3-4 car ways (no service/living street/motorway, no roundabout, "
                          "not a restriction via node), first clean movement by sha256; roundabout: single closed "
                          "ring way with 3+ spoke nodes, entry spoke by sha256; strata ordered by "
                          "sha256('JOURNEY-001:'+id), up to 3x quota drawn, prepare keeps quota testable",
        "quotas": {"/".join(k): v for k, v in QUOTAS.items()},
        "turn_classes": {"straight_below_deg": STRAIGHT_MAX, "turn_deg": [TURN_MIN, TURN_MAX]},
        "source_sha256": t1.sha256_file(source),
        "available_by_stratum": dict(sorted(Counter("/".join(c["stratum"]) for c in found).items())),
        "cases": chosen,
    }, indent=1, sort_keys=True))
    opl.unlink()
    print(f"Frozen {len(chosen)} candidate cases -> {COHORT}")


def _roads(source: Path) -> Path:
    a1.use("access001")  # shared roads file only; ACCESS-001 cohort supplies the source hash check
    return a1.roads_source(source)


# --------------------------------------------------------------------------- geometry
def _walk(clip: a1.AccessClip, way: str, junction: str, first: str, arriving: bool) -> list[str] | None:
    """Walk along `way` from the junction through `first` until APPROACH_M covered (travel order)."""
    refs = clip.ways[way][0]
    if junction not in refs or first not in refs:
        return None
    i, j = refs.index(junction), refs.index(first)
    step = 1 if j > i else -1
    walk, walked = [junction], 0.0
    while 0 <= j < len(refs) and refs[j] not in walk:
        move = (refs[j], walk[-1]) if arriving else (walk[-1], refs[j])
        if not clip.can_travel(way, *move):
            return None
        seg = t1.metres(clip.coords[walk[-1]], clip.coords[refs[j]])
        walk.append(refs[j])
        walked += seg
        if walked >= a1.APPROACH_M and seg >= a1.MIN_SEGMENT_M:
            return list(reversed(walk)) if arriving else walk
        j += step
    return None


def _mid(clip, seg):
    p, q = clip.coords[seg[0]], clip.coords[seg[1]]
    return [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2]


def _geom(clip, o_walk, d_walk, via: list[str], extra: dict) -> dict:
    o_seg, d_seg = o_walk[:2], d_walk[-2:]
    return {"status": "TESTABLE", "group": "closed", "origin": _mid(clip, o_seg), "destination": _mid(clip, d_seg),
            "origin_segment": o_seg, "destination_segment": d_seg,
            "direct_path": [*o_walk, *via, *d_walk[1:]], **extra}


def ring_exits(clip: a1.AccessClip, ring: str, entry: str) -> tuple[list[str], list[tuple[str, str, str]]]:
    """Ring nodes in travel order from the entry, and the exits passed: (ring node, way, next node)."""
    refs = clip.ways[ring][0][:-1]
    order = refs if clip.oneway(ring) != -1 else list(reversed(refs))
    i = order.index(entry)
    path = order[i:] + order[:i] + [entry]
    exits = []
    for k in range(1, len(path)):
        n, prev = path[k], path[k - 1]
        for w in clip.drivable_ways(n):
            if w == ring:
                continue
            wr = clip.ways[w][0]
            for idx, x in enumerate(wr):
                if x != n:
                    continue
                for jdx in (idx - 1, idx + 1):
                    if 0 <= jdx < len(wr) and wr[jdx] not in refs and clip.can_travel(w, n, wr[jdx]):
                        exits.append((n, w, wr[jdx]))
                        break
                else:
                    continue
                break
    return path, exits


def case_geometry(case: dict, clip: a1.AccessClip) -> dict:
    group = case["stratum"][0]
    if group == "turn":
        j, wa, p, wb, q = (str(case[k]) for k in ("node", "from_way", "from_node", "to_way", "to_node"))
        if any(w not in clip.ways for w in (wa, wb)) or j not in clip.coords:
            return {"status": "WAY_CHANGED_IN_CLIP"}
        o, d = _walk(clip, wa, j, p, True), _walk(clip, wb, j, q, False)
        if o is None or d is None:
            return {"status": "NO_LEGAL_APPROACH"}
        if set(o[:-1]) & set(d[1:]):
            return {"status": "LOOP"}
        cls = turn_class(delta_deg(clip.coords[o[-2]], clip.coords[j], clip.coords[d[1]]))
        if cls != case["stratum"][1]:
            return {"status": "CLASS_CHANGED_IN_CLIP"}
        return _geom(clip, o, d, [], {"kind": "turn", "expected": cls, "junction": j})
    ring, entry, k = str(case["ring_way"]), str(case["entry_node"]), case["exit_number"]
    if ring not in clip.ways or entry not in clip.ways[ring][0]:
        return {"status": "WAY_CHANGED_IN_CLIP"}
    path, exits = ring_exits(clip, ring, entry)
    exits = [e for e in exits if e[0] != entry]
    if len(exits) < k + 1:  # the chosen exit must not be the last one (U-turn round the ring)
        return {"status": "TOO_FEW_EXITS"}
    x, xw, xn = exits[k - 1]
    entries = [w for w in clip.drivable_ways(entry) if w != ring]
    o = next((walk for w in entries for wr in [clip.ways[w][0]] for idx, n in enumerate(wr) if n == entry
              for jdx in (idx - 1, idx + 1) if 0 <= jdx < len(wr) and wr[jdx] not in path
              for walk in [_walk(clip, w, entry, wr[jdx], True)] if walk), None)
    d = _walk(clip, xw, x, xn, False)
    if o is None or d is None:
        return {"status": "NO_LEGAL_APPROACH"}
    via = path[1:path.index(x) + 1]  # ring nodes after the entry, up to and including the exit node
    return _geom(clip, o, d, via, {"kind": "roundabout", "expected": k, "ring": ring, "entry": entry,
                                   "exit_node": x, "ring_nodes": path[:-1]})


def prepare(source: Path) -> None:
    cohort = json.loads(COHORT.read_text())
    a1.roads_source(source)
    out, testable = [], Counter()
    for case in cohort["cases"]:
        key = tuple(case["stratum"])
        record = {"id": case["id"], "stratum": case["stratum"]}
        if testable[key] >= QUOTAS[key]:
            out.append({**record, "geometry": {"status": "BEYOND_QUOTA"}})
            continue
        folder = WORK / "cases" / case["id"]
        bbox = a1.bbox_around(case["lat"], case["lon"])
        raw = _cut(folder, bbox)
        geom = case_geometry(case, a1.AccessClip(raw))
        out.append({**record, "bbox": bbox, "clip_sha256": hashlib.sha256(raw).hexdigest(), "geometry": geom})
        subprocess.run(["rm", "-rf", str(folder)], check=True)
        testable[key] += geom["status"] == "TESTABLE"
        print(case["id"], geom["status"], flush=True)
    text = json.dumps(out, indent=1)
    if PREPARED.exists() and PREPARED.read_text() != text:
        raise SystemExit("Prepared clips differ from the frozen config/journey001-prepared.json")
    PREPARED.write_text(text)
    print(Counter(r["geometry"]["status"] for r in out), dict(testable))


def _cut(folder: Path, bbox: str) -> bytes:
    saved, a1.WORK = a1.WORK, WORK
    try:
        return a1.cut(folder, bbox)
    finally:
        a1.WORK = saved


def case_clip(record: dict) -> bytes:
    folder = WORK / "cases" / record["id"]
    raw = (folder / "clip.osm").read_bytes() if (folder / "clip.osm").exists() else _cut(folder, record["bbox"])
    if hashlib.sha256(raw).hexdigest() != record["clip_sha256"]:
        raise RuntimeError(f"JOURNEY-001 {record['id']}: clip bytes differ from the frozen hash")
    return raw


# --------------------------------------------------------------------------- engines
def engine_case(engine: str, folder: Path, clip, geom: dict) -> dict:
    """One reference engine built on this case's clip, asked once with instructions."""
    result = xe.route(engine, folder, clip, geom)
    if isinstance(result, dict):
        return result
    return _judged(clip, geom, *result)


def _judged(clip, geom: dict, points, steps, ms: float) -> dict:
    if points is None:
        return {**judge_route(clip, geom, None), "warm_query_ms": round(ms, 1)}
    nodes, snaps = xe.engine_path(clip, geom, points)
    return {**judge_route(clip, geom, nodes), **snaps, "warm_query_ms": round(ms, 1),
            "instruction": instruction_at(geom, steps), "line": line_adherence(clip, nodes, points)}


def dmn_case(raw: bytes, clip, geom: dict) -> dict:
    """DMN route plus its principal maneuvers for the junction movement only."""
    from engine import RouteNotFound, shortest_route
    from engine.maneuvers import principal_maneuvers
    from map_data import OSMImportError, Provenance, import_osm_xml
    began = time.perf_counter()
    try:
        imported = import_osm_xml(raw, provenance=Provenance(
            region="Greater Manchester (JOURNEY-001 clip)", snapshot="openstreetmap.fr north_west 7332146",
            source="OpenStreetMap", attribution="© OpenStreetMap contributors, ODbL"))
    except OSMImportError as exc:
        return {"route": "ENGINE_REJECTED_MAP", "detail": str(exc)[:300]}
    graph = imported.graph
    by_pair = {(e.source, e.target): e for e in graph.edges.values()}
    start = by_pair.get(tuple(f"osm:{n}" for n in geom["origin_segment"]))
    finish = by_pair.get(tuple(f"osm:{n}" for n in geom["destination_segment"]))
    if start is None or finish is None or "prohibited" in (start.access, finish.access):
        return {"route": "ENDPOINT_WITHHELD_BY_POLICY"}
    try:
        route = shortest_route(graph, start.target, finish.target, incoming_edge_id=start.edge_id,
                               destination_edge_id=finish.edge_id, endpoint_uncertain_access=True)
    except RouteNotFound:
        return {**judge_route(clip, geom, None), "ms_import_and_route": round((time.perf_counter() - began) * 1000, 1)}
    ms = round((time.perf_counter() - began) * 1000, 1)
    edges = [start.edge_id, *route.edge_ids]
    nodes = [start.source.removeprefix("osm:")] + [graph.edges[e].target.removeprefix("osm:") for e in edges]
    nodes = [n for i, n in enumerate(nodes) if i == 0 or nodes[i - 1] != n]
    out = {**judge_route(clip, geom, nodes), "ms_import_and_route": ms, "line": {"status": "NOT_APPLICABLE_NODE_PATH"}}
    if not makes_movement(geom, nodes):
        out["instruction"] = {"verdict": "NOT_JUDGED_ROUTE_DIFFERS"}
        return out
    # the maneuver is computed on the movement's own edges, so it belongs to this junction
    seq = geom["direct_path"]
    lo = seq.index(geom["entry"] if geom["kind"] == "roundabout" else geom["junction"]) - 1
    hi = seq.index(geom["exit_node"]) + 1 if geom["kind"] == "roundabout" else seq.index(geom["junction"]) + 1
    sub = [by_pair[(f"osm:{x}", f"osm:{y}")].edge_id for x, y in zip(seq[lo:hi], seq[lo + 1:hi + 1])]
    ring = [e.edge_id for e in graph.edges.values() if e.edge_id.split(":")[1] == geom.get("ring")]
    try:
        mans = principal_maneuvers(graph, imported.coordinates, sub, ring)
        step = mans[-1] if mans else {"kind": "straight"}
        out["instruction"] = judge_instruction(geom, {"kind": step["kind"], "exit": step.get("exit")})
    except ValueError as exc:
        out["instruction"] = {"verdict": "REFUSED", "detail": str(exc)[:200]}
    return out


# --------------------------------------------------------------------------- judging
def judge_route(clip, geom: dict, nodes: list[str] | None) -> dict:
    if nodes is None:
        return {"route": "NO_ROUTE"}
    rules = t1.audit_route(clip, nodes)
    extra = {**b1.audit_barriers(clip, nodes, ""), **a1.audit_roads(clip, nodes, "")}
    breaks = extra["other_closed_barriers"] + extra["other_closed_roads"]
    legal = "ILLEGAL" if breaks else rules["route_legal"]
    anchored = nodes[:2] == list(geom["origin_segment"]) and nodes[-2:] == list(geom["destination_segment"])
    length = sum(t1.metres(clip.coords[x], clip.coords[y]) for x, y in zip(nodes, nodes[1:])
                 if x in clip.coords and y in clip.coords)
    return {"route": "VALID" if anchored and legal == "LEGAL" else "ILLEGAL" if legal == "ILLEGAL" else
            "OFF_TARGET" if not anchored else "CONDITIONAL", "path": nodes, "length_m": round(length, 1),
            "violations": sorted(rules["violations"] + breaks), "follows_movement": makes_movement(geom, nodes)}


def makes_movement(geom: dict, nodes: list[str]) -> bool:
    """The route drives the intended movement through the junction (or round the ring)."""
    seq = geom["direct_path"]
    lo = seq.index(geom["entry"] if geom["kind"] == "roundabout" else geom["junction"]) - 1
    hi = seq.index(geom["exit_node"] if geom["kind"] == "roundabout" else geom["junction"]) + 1
    core = seq[lo:hi + 1]  # the road piece before, the junction (or ring) and the piece after
    return any(nodes[i:i + len(core)] == core for i in range(len(nodes) - len(core) + 1))


def judge_instruction(geom: dict, step: dict | None) -> dict:
    if step is None:
        return {"verdict": "MISSING"}
    if geom["kind"] == "roundabout":
        if step["kind"] != "roundabout":
            return {"verdict": "WRONG", "said": step}
        return {"verdict": "CORRECT" if step.get("exit") == geom["expected"] else "WRONG", "said": step}
    # Turn (60-120 degrees): the instruction must name the right side ("slight" still names it).
    # Straight on (under 25 degrees): no instruction, straight/continue, or a slight/keep cue.
    ok = step["kind"] == geom["expected"] or (geom["expected"] == "straight" and step.get("slight")
                                              and step["kind"] in ("left", "right"))
    return {"verdict": "CORRECT" if ok else "WRONG", "said": step}


def instruction_at(geom: dict, steps: list[dict]) -> dict:
    """The engine's instruction for this junction; a straight-on movement may have none."""
    if geom["kind"] == "roundabout":
        near = [s for s in steps if s["kind"] == "roundabout"]
        return judge_instruction(geom, near[0] if near else None)
    j = tuple(geom["junction_at"]) if "junction_at" in geom else None
    near = [s for s in steps if j and t1.metres(tuple(s["at"]), j) <= NEAR_M]
    if not near:
        return judge_instruction(geom, {"kind": "straight", "implicit": True} if geom["expected"] == "straight"
                                 else None)
    return judge_instruction(geom, near[0])


def _seg_dist(p, a, b) -> float:
    """Metres from point p to segment a-b (local flat approximation)."""
    kx = 111_320 * math.cos(math.radians(p[0]))
    ax, ay, bx, by = (a[1] - p[1]) * kx, (a[0] - p[0]) * 111_320, (b[1] - p[1]) * kx, (b[0] - p[0]) * 111_320
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
    return math.hypot(ax + t * dx, ay + t * dy)


def line_adherence(clip, nodes: list[str], points) -> dict:
    """How far the drawn line strays from the road segments of the route's own node path."""
    segs = [(clip.coords[x], clip.coords[y]) for x, y in zip(nodes, nodes[1:]) if x in clip.coords and y in clip.coords]
    if not segs or not points:
        return {"status": "NOT_JUDGED"}
    worst = max(min(_seg_dist(tuple(p), a, b) for a, b in segs) for p in points)
    return {"status": "MEASURED", "max_off_road_m": round(worst, 2)}


# --------------------------------------------------------------------------- runs
ENGINES = ("DMN", *xe.ENGINES)


def _provenance(engine: str) -> dict:
    frozen = json.loads(COHORT.read_text())
    return {"schema": 1, "engine": engine, "revision": t1._revision(), "cohort_sha256": t1.sha256_file(COHORT),
            "source_sha256": frozen["source_sha256"], "prepared_sha256": t1.sha256_file(PREPARED),
            "runner_sha256": t1.sha256_file(Path(__file__))}


def run(engine: str, only: set[str] | None = None) -> None:
    prepared = json.loads(PREPARED.read_text())
    out = WORK / f"run-{engine}.json"
    WORK.mkdir(parents=True, exist_ok=True)
    results: dict = {"_provenance": _provenance(engine)}
    for record in prepared:
        geom = record["geometry"]
        if geom["status"] != "TESTABLE" or (only and record["id"] not in only):
            continue
        raw = case_clip(record)
        clip = a1.AccessClip(raw)
        if geom["kind"] == "turn":
            geom = {**geom, "junction_at": clip.coords[geom["junction"]]}
        folder = WORK / "cases" / record["id"]
        entry = dmn_case(raw, clip, geom) if engine == "DMN" else engine_case(engine, folder, clip, geom)
        results[record["id"]] = entry
        out.write_text(json.dumps(results, indent=1, sort_keys=True))
        subprocess.run(["rm", "-rf", str(folder)], check=False)
        print(record["id"], entry.get("route"), entry.get("instruction", {}).get("verdict"), flush=True)


def score() -> None:
    prepared = {r["id"]: r for r in json.loads(PREPARED.read_text())}
    runs = {e: json.loads((WORK / f"run-{e}.json").read_text()) for e in ENGINES if (WORK / f"run-{e}.json").exists()}
    for name, record in runs.items():
        if record.get("_provenance") != _provenance(name):
            raise RuntimeError(f"JOURNEY-001 {name}: stale/unprovenanced result")
    testable = [i for i, r in prepared.items() if r["geometry"]["status"] == "TESTABLE"]
    shortest = {}
    for i in testable:
        lengths = [r[i]["length_m"] for r in runs.values() if r.get(i, {}).get("route") == "VALID"]
        shortest[i] = min(lengths) if lengths else None
    summary = {"contract": CONTRACT, "revision": t1._revision(), "prepared_sha256": t1.sha256_file(PREPARED),
               "testable_by_stratum": dict(sorted(Counter("/".join(prepared[i]["stratum"]) for i in testable).items())),
               "truth": "OpenStreetMap geometry and tags in the hashed snapshot; not independent UK road law",
               "categories": {}}
    cats = summary["categories"]
    for name, res in runs.items():
        cases = {i: res[i] for i in testable if i in res}
        ratios = [c["length_m"] / shortest[i] for i, c in cases.items() if c.get("route") == "VALID" and shortest[i]]
        ms_key = "ms_import_and_route" if name == "DMN" else "warm_query_ms"
        cats.setdefault("5_route_validity", {})[name] = dict(Counter(c.get("route") for c in cases.values()))
        cats.setdefault("6_route_quality", {})[name] = {
            "valid_routes": len(ratios), "median_length_vs_shortest": round(statistics.median(ratios), 3) if ratios else None,
            "longer_than_1_2x_shortest": sorted(i for i, c in cases.items() if c.get("route") == "VALID"
                                                 and shortest[i] and c["length_m"] > 1.2 * shortest[i])}
        for cat, kind in (("8_junction_turns", "turn"), ("9_roundabout_exits", "roundabout")):
            judged = {i: c.get("instruction", {}).get("verdict", "NOT_JUDGED_NO_ROUTE")
                      if c.get("route") == "VALID" and c.get("follows_movement") else "NOT_JUDGED_ROUTE_DIFFERS"
                      for i, c in cases.items() if prepared[i]["geometry"]["kind"] == kind}
            by = defaultdict(Counter)
            for i, v in judged.items():
                by[prepared[i]["stratum"][1]][v] += 1
            cats.setdefault(cat, {})[name] = {"by_kind": {k: dict(c) for k, c in sorted(by.items())},
                                              "correct": sum(v == "CORRECT" for v in judged.values()),
                                              "judged": sum(v in ("CORRECT", "WRONG", "MISSING", "REFUSED")
                                                            for v in judged.values()),
                                              "wrong_cases": {i: cases[i]["instruction"] for i, v in judged.items()
                                                              if v in ("WRONG", "MISSING", "REFUSED")}}
        offs = [c["line"]["max_off_road_m"] for c in cases.values() if c.get("line", {}).get("status") == "MEASURED"]
        cats.setdefault("11_route_line", {})[name] = (
            {"status": "NOT_APPLICABLE_NODE_PATH"} if name == "DMN" else
            {"measured": len(offs), "median_max_off_road_m": round(statistics.median(offs), 2) if offs else None,
             "cases_over_5m": sum(o > 5 for o in offs)})
        cats.setdefault("timing_not_ranked", {})[name] = b1._ms([c[ms_key] for c in cases.values() if c.get(ms_key)])
    (WORK / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))


def brief() -> int:
    s = json.loads((WORK / "summary.json").read_text())
    lines = [f"{s['contract']} @ {s['revision'][:12]}: testable {s['testable_by_stratum']}"]
    c = s["categories"]
    lines.append("5 valid routes: " + "; ".join(f"{e} {v.get('VALID', 0)}/{sum(v.values())}"
                                                for e, v in c["5_route_validity"].items()))
    lines.append("6 length vs shortest (median; >1.2x): " + "; ".join(
        f"{e} {v['median_length_vs_shortest']}, {len(v['longer_than_1_2x_shortest'])}" for e, v in c["6_route_quality"].items()))
    for cat in ("8_junction_turns", "9_roundabout_exits"):
        lines.append(f"{cat.replace('_', ' ')} correct/judged: " + "; ".join(
            f"{e} {v['correct']}/{v['judged']}" for e, v in c[cat].items()))
    lines.append("11 line max off road (median m; cases >5 m): " + "; ".join(
        f"{e} " + ("n/a (node path)" if v.get("status") else f"{v['median_max_off_road_m']}, {v['cases_over_5m']}")
        for e, v in c["11_route_line"].items()))
    illegal = {e: v.get("ILLEGAL", 0) for e, v in c["5_route_validity"].items()}
    bad = ["DMN returned an illegal route"] if illegal.get("DMN") else []
    lines.append("RESULT: " + ("; ".join(bad) if bad else "OK") + " (each category scored separately; no total)")
    print("\n".join(lines))
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ("select", "prepare"):
        sub.add_parser(cmd).add_argument("--source", type=Path, default=a1.SOURCE)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--engine", choices=ENGINES, required=True)
    run_parser.add_argument("--only", nargs="*")
    sub.add_parser("score")
    sub.add_parser("brief")
    args = parser.parse_args()
    if args.cmd == "select":
        select(args.source)
    elif args.cmd == "prepare":
        prepare(args.source)
    elif args.cmd == "run":
        run(args.engine, set(args.only or ()) or None)
    elif args.cmd == "score":
        score()
    else:
        return brief()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
