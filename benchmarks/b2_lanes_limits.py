"""Run B2: LANES-001 (category 10) and LIMITS-001 (category 15), scored separately.

Owner-approved grouping (17 Oct 2026): one shared run, each test its own frozen
cases, verdicts and ranking, no combined score. DMN is the engine under test; the
reference engines only appear where their route answers expose the detail (lanes:
OSRM; speed limits: OSRM, GraphHopper). Others are NOT_AVAILABLE, never a fail.

Truth comes only from the hashed OSM snapshot's own tags, read by this file's own
small parser (independent of DMN's): map-derived, not verified road paint or law.

LANES-001  junction movement (left / right / straight, classes as JOURNEY-001) whose
           approach road carries clean directional turn:lanes (only left, through,
           right arrows; no unmarked, slight, sharp or merge lanes). Expected lanes:
           those whose arrows include the movement. Verdict: CORRECT (same lanes),
           WRONG, NOT_GIVEN, NOT_JUDGED_ROUTE_DIFFERS.
LIMITS-001 road way travelled end to end. Kinds: one limit of 20/30/40/50/60/70 mph;
           different limits per direction; no limit mapped. Expected: the mapped
           limit for the direction travelled, or "unknown" when none is mapped.
           Verdict: CORRECT (within 2 km/h), WRONG, NOT_GIVEN, GUESSED (a number
           where none is mapped), NOT_JUDGED_ROUTE_DIFFERS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from benchmarks import access001_route as a1
from benchmarks import barrier001_route as b1
from benchmarks import extra_engines as xe
from benchmarks import journey001 as j1
from benchmarks import turn001_restrictions as t1

ROOT = t1.ROOT
TESTS = {"lanes001": "LANES-001 v1", "limits001": "LIMITS-001 v1"}
TEST = "lanes001"
ENGINES = ("DMN", "OSRM", "GraphHopper")
MPH = re.compile(r"^(\d{1,3}) mph$")
LIMIT_KINDS = ("mph20", "mph30", "mph40", "mph50", "mph60", "mph70", "directional", "none_mapped")
QUOTA = {"lanes001": 12, "limits001": 10}
CLEAN_TOKENS = {"left", "through", "right"}
TOKEN = {"left": "left", "right": "right", "straight": "through"}


def work() -> Path:
    return ROOT / "results" / TEST


def cohort() -> Path:
    return ROOT / "config" / f"{TEST}-cohort.json"


def prepared() -> Path:
    return ROOT / "config" / f"{TEST}-prepared.json"


def _h(label: str) -> str:
    return hashlib.sha256(f"{TESTS[TEST].split()[0]}:{label}".encode()).hexdigest()


# --------------------------------------------------------------------------- truth parsers
def mph_kph(value: str | None) -> float | None:
    m = MPH.match(value or "")
    return round(int(m.group(1)) * 1.609344, 2) if m else None


def limit_kind(tags: dict[str, str]) -> str | None:
    if not t1.Clip.drivable(tags) or tags.get("junction") in ("roundabout", "circular") \
            or tags.get("highway", "").startswith("motorway") or any("conditional" in k for k in tags):
        return None
    keys = [k for k in tags if k.startswith("maxspeed")]
    if not keys:
        return "none_mapped"
    fwd, bwd = tags.get("maxspeed:forward"), tags.get("maxspeed:backward")
    if fwd and bwd and set(keys) <= {"maxspeed:forward", "maxspeed:backward", "maxspeed:type"}:
        return "directional" if mph_kph(fwd) and mph_kph(bwd) and fwd != bwd else None
    if set(keys) - {"maxspeed", "maxspeed:type"}:
        return None
    m = MPH.match(tags.get("maxspeed", ""))
    return f"mph{m.group(1)}" if m and f"mph{m.group(1)}" in LIMIT_KINDS else None


def expected_limit(tags: dict[str, str], direction: str) -> float | None:
    return mph_kph(tags.get(f"maxspeed:{direction}", tags.get("maxspeed")))


def lane_key(tags: dict[str, str], forward: bool) -> str | None:
    if f"turn:lanes:{'forward' if forward else 'backward'}" in tags:
        return f"turn:lanes:{'forward' if forward else 'backward'}"
    if forward and tags.get("oneway") in ("yes", "1", "true") and "turn:lanes" in tags:
        return "turn:lanes"
    return None


def clean_lanes(value: str) -> list[set[str]] | None:
    lanes = [set(t.strip() for t in lane.split(";")) for lane in value.split("|")]
    if not 2 <= len(lanes) <= 6 or any(not lane or not lane <= CLEAN_TOKENS for lane in lanes):
        return None
    return lanes


# --------------------------------------------------------------------------- cohort
def select(source: Path) -> None:
    if cohort().exists():
        raise RuntimeError(f"{TESTS[TEST]} frozen cohort exists; select a new named cohort instead of overwriting")
    w = work()
    w.mkdir(parents=True, exist_ok=True)
    roads = j1._roads(source)
    opl = w / "all.opl"
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
    for wid, (refs, _) in ways.items():
        for n in refs:
            node_ways[n].add(wid)
    found = []
    if TEST == "limits001":
        for wid, (refs, tags) in ways.items():
            kind = limit_kind(tags)
            if kind is None or len(refs) < 2 or refs[0] == refs[-1] or len(set(refs)) != len(refs) \
                    or any(r not in coords for r in refs):
                continue
            length = sum(t1.metres(coords[a], coords[b]) for a, b in zip(refs, refs[1:]))
            if not a1.MIN_WAY_M <= length <= a1.MAX_WAY_M or len(node_ways[refs[0]]) < 2 or len(node_ways[refs[-1]]) < 2:
                continue
            mid = [coords[r] for r in refs]
            found.append({"id": f"limit-{wid}", "stratum": ["limit", kind], "way": int(wid),
                          "refs": [int(r) for r in refs], "tags": {k: v for k, v in tags.items() if "maxspeed" in k},
                          "lat": round(sum(p[0] for p in mid) / len(mid), 7),
                          "lon": round(sum(p[1] for p in mid) / len(mid), 7)})
    else:
        for node, ws in node_ways.items():
            if node in via_nodes or node not in coords or len(ws) < 2 or any(
                    ways[x][1].get("junction") in ("roundabout", "circular") for x in ws):
                continue
            moves = []
            for wa in sorted(ws):
                ra, ta = ways[wa]
                for i, n in enumerate(ra):
                    if n != node:
                        continue
                    for jdx in (i - 1, i + 1):
                        if not 0 <= jdx < len(ra) or ra[jdx] not in coords:
                            continue
                        key = lane_key(ta, forward=jdx < i)  # arriving along the way's own order
                        lanes = clean_lanes(ta[key]) if key else None
                        if not lanes:
                            continue
                        for wb in sorted(ws):
                            rb = ways[wb][0]
                            for k, m in enumerate(rb):
                                if m != node:
                                    continue
                                for q in (rb[k - 1] if k else None, rb[k + 1] if k + 1 < len(rb) else None):
                                    if q is None or q not in coords or (wb == wa and q == ra[jdx]):
                                        continue
                                    cls = j1.turn_class(j1.delta_deg(coords[ra[jdx]], coords[node], coords[q]))
                                    if cls and any(TOKEN[cls] in lane for lane in lanes):
                                        expected = [x + 1 for x, lane in enumerate(lanes) if TOKEN[cls] in lane]
                                        moves.append((_h(f"{node}:{wa}:{ra[jdx]}:{wb}:{q}"), cls, wa, ra[jdx], wb, q,
                                                      key, ta[key], expected))
            if moves:
                _, cls, wa, p, wb, q, key, value, expected = min(moves)
                found.append({"id": f"lanes-{node}", "stratum": ["lanes", cls], "node": int(node),
                              "lat": coords[node][0], "lon": coords[node][1], "from_way": int(wa),
                              "from_node": int(p), "to_way": int(wb), "to_node": int(q), "lane_tag": key,
                              "lane_value": value, "expected_lanes": expected})
    kinds = LIMIT_KINDS if TEST == "limits001" else ("left", "right", "straight")
    chosen = []
    for kind in kinds:
        pool = sorted((c for c in found if c["stratum"][1] == kind), key=lambda c: _h(c["id"]))
        chosen.extend(pool[:QUOTA[TEST] * 3])
    cohort().write_text(json.dumps({
        "contract": TESTS[TEST], "frozen_before_engine_runs": True, "source_sha256": t1.sha256_file(source),
        "quota_per_kind": QUOTA[TEST],
        "available_by_kind": dict(sorted(Counter(c["stratum"][1] for c in found).items())), "cases": chosen,
    }, indent=1, sort_keys=True))
    opl.unlink()
    print(f"Frozen {len(chosen)} candidate cases -> {cohort()}")


def case_geometry(case: dict, clip) -> dict:
    if TEST == "limits001":
        g = a1.case_geometry({**case, "stratum": ["closed", case["stratum"][1]]}, clip)
        if g["status"] != "TESTABLE":
            return g
        refs = [str(r) for r in case["refs"]]
        direction = "forward" if g["way_nodes"] == refs else "backward"
        return {**g, "direction": direction, "expected_kph": expected_limit(case["tags"], direction)}
    g = j1.case_geometry({**case, "stratum": ["turn", case["stratum"][1]]}, clip)
    return {**g, "expected_lanes": case["expected_lanes"], "lane_tag": case["lane_tag"]} \
        if g["status"] == "TESTABLE" else g


def prepare(source: Path) -> None:
    data = json.loads(cohort().read_text())
    a1.roads_source(source)
    out, testable = [], Counter()
    for case in data["cases"]:
        kind = case["stratum"][1]
        record = {"id": case["id"], "stratum": case["stratum"]}
        if testable[kind] >= QUOTA[TEST]:
            out.append({**record, "geometry": {"status": "BEYOND_QUOTA"}})
            continue
        folder = work() / "cases" / case["id"]
        bbox = a1.bbox_around(case["lat"], case["lon"])
        raw = _cut(folder, bbox)
        geom = case_geometry(case, a1.AccessClip(raw))
        out.append({**record, "bbox": bbox, "clip_sha256": hashlib.sha256(raw).hexdigest(), "geometry": geom})
        subprocess.run(["rm", "-rf", str(folder)], check=True)
        testable[kind] += geom["status"] == "TESTABLE"
        print(case["id"], geom["status"], flush=True)
    text = json.dumps(out, indent=1)
    if prepared().exists() and prepared().read_text() != text:
        raise SystemExit(f"Prepared clips differ from the frozen {prepared().name}")
    prepared().write_text(text)
    print(Counter(r["geometry"]["status"] for r in out), dict(testable))


def _cut(folder: Path, bbox: str) -> bytes:
    saved, a1.WORK = a1.WORK, work()
    try:
        return a1.cut(folder, bbox)
    finally:
        a1.WORK = saved


def case_clip(record: dict) -> bytes:
    folder = work() / "cases" / record["id"]
    raw = (folder / "clip.osm").read_bytes() if (folder / "clip.osm").exists() else _cut(folder, record["bbox"])
    if hashlib.sha256(raw).hexdigest() != record["clip_sha256"]:
        raise RuntimeError(f"{TESTS[TEST]} {record['id']}: clip bytes differ from the frozen hash")
    return raw


# --------------------------------------------------------------------------- verdicts
def judge_limit(geom: dict, reported: float | None, used: bool) -> dict:
    if not used:
        return {"verdict": "NOT_JUDGED_ROUTE_DIFFERS"}
    expected = geom["expected_kph"]
    if expected is None:
        return {"verdict": "CORRECT" if reported is None else "GUESSED", "reported_kph": reported}
    if reported is None:
        return {"verdict": "NOT_GIVEN"}
    return {"verdict": "CORRECT" if abs(reported - expected) <= 2.0 else "WRONG", "reported_kph": round(reported, 1)}


def judge_lanes(geom: dict, lanes: list[int] | None, follows: bool) -> dict:
    if not follows:
        return {"verdict": "NOT_JUDGED_ROUTE_DIFFERS"}
    if not lanes:
        return {"verdict": "NOT_GIVEN"}
    return {"verdict": "CORRECT" if sorted(lanes) == sorted(geom["expected_lanes"]) else "WRONG", "said": lanes}


def limit_on_way(clip, geom: dict, points, limits) -> tuple[float | None, bool]:
    """The limit an engine reports along the tested way (most common over its segments)."""
    way = [clip.coords[n] for n in geom["way_nodes"]]
    segs = list(zip(way, way[1:]))
    values = []
    for k, value in enumerate(limits or []):
        if k + 1 >= len(points):
            break
        mid = ((points[k][0] + points[k + 1][0]) / 2, (points[k][1] + points[k + 1][1]) / 2)
        if min(j1._seg_dist(mid, a, b) for a, b in segs) <= 2.0:
            values.append(None if value is None else round(value, 1))
    if not values:
        return None, False
    return Counter(values).most_common(1)[0][0], True


def dmn_case(raw: bytes, clip, geom: dict) -> dict:
    from engine import RouteNotFound, shortest_route
    from engine.maneuvers import principal_maneuvers
    from map_data import OSMImportError, Provenance, import_osm_xml
    from map_data.lane_evidence import mapped_lanes_for, parse_turn_lanes
    from map_data.speed_evidence import speed_limit_from_tags
    try:
        imported = import_osm_xml(raw, provenance=Provenance(
            region="Greater Manchester (run B2 clip)", snapshot="openstreetmap.fr north_west 7332146",
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
        return {"route": "NO_ROUTE"}
    edges = [graph.edges[e] for e in (start.edge_id, *route.edge_ids)]
    nodes = [edges[0].source.removeprefix("osm:")] + [e.target.removeprefix("osm:") for e in edges]
    out = {"route": "ROUTED", "path": nodes}
    if TEST == "limits001":
        way = geom["way"]
        on_way = [e for e in edges if e.edge_id.split(":")[1] == way]
        if not on_way:
            out["result"] = judge_limit(geom, None, False)
            return out
        direction = "forward" if on_way[0].edge_id.endswith(":f") else "backward"
        ev = speed_limit_from_tags(clip.ways[way][1], direction=direction)
        out["result"] = judge_limit(geom, ev.kph if ev.status == "MAPPED_ONLY" else None, True)
        return out
    if not j1.makes_movement(geom, nodes):
        out["result"] = judge_lanes(geom, None, False)
        return out
    junction = f"osm:{geom['junction']}"
    i = next(k for k, e in enumerate(edges) if e.target == junction)
    into, onward = edges[i], edges[i + 1]
    try:
        mans = principal_maneuvers(graph, imported.coordinates, [into.edge_id, onward.edge_id], [])
    except ValueError:
        mans = None
    token = None if mans is None else TOKEN[mans[-1]["kind"]] if mans and mans[-1]["kind"] in TOKEN else \
        "through" if mans == [] else None
    way, direction = into.edge_id.split(":")[1], "forward" if into.edge_id.endswith(":f") else "backward"
    lanes = list(mapped_lanes_for(parse_turn_lanes(clip.ways[way][1], direction=direction), token)) if token else []
    out["result"] = judge_lanes(geom, lanes, True)
    return out


def engine_case(engine: str, folder: Path, clip, geom: dict) -> dict:
    result = xe.route_details(engine, folder, clip, geom)
    if isinstance(result, dict):
        return result
    points, details, ms = result
    if points is None:
        return {"route": "NO_ROUTE", "warm_query_ms": round(ms, 1)}
    nodes, _ = xe.engine_path(clip, geom, points)
    out = {"route": "ROUTED", "path": nodes, "warm_query_ms": round(ms, 1)}
    if TEST == "limits001":
        value, used = limit_on_way(clip, geom, points, details.get("segment_limits_kph"))
        out["result"] = judge_limit(geom, value, used and a1.uses_way(nodes, geom["way_nodes"]))
        return out
    if details.get("lanes") is None:
        out["result"] = {"verdict": "NOT_AVAILABLE"}
        return out
    j = clip.coords[geom["junction"]]
    near = [ln for ln in details["lanes"] if t1.metres(tuple(ln["at"]), j) <= j1.NEAR_M]
    out["result"] = judge_lanes(geom, near[0]["valid"] if near else None, j1.makes_movement(geom, nodes))
    return out


# --------------------------------------------------------------------------- runs
def _provenance(engine: str) -> dict:
    return {"schema": 1, "engine": engine, "revision": t1._revision(), "cohort_sha256": t1.sha256_file(cohort()),
            "prepared_sha256": t1.sha256_file(prepared()), "runner_sha256": t1.sha256_file(Path(__file__))}


def run(engine: str, only: set[str] | None = None) -> None:
    out_file = work() / f"run-{engine}.json"
    work().mkdir(parents=True, exist_ok=True)
    results: dict = {"_provenance": _provenance(engine)}
    for record in json.loads(prepared().read_text()):
        geom = record["geometry"]
        if geom["status"] != "TESTABLE" or (only and record["id"] not in only):
            continue
        raw = case_clip(record)
        clip = a1.AccessClip(raw)
        folder = work() / "cases" / record["id"]
        entry = dmn_case(raw, clip, geom) if engine == "DMN" else engine_case(engine, folder, clip, geom)
        results[record["id"]] = entry
        out_file.write_text(json.dumps(results, indent=1, sort_keys=True))
        subprocess.run(["rm", "-rf", str(folder)], check=False)
        print(record["id"], entry.get("route"), entry.get("result", {}).get("verdict"), flush=True)


def score() -> None:
    recs = {r["id"]: r for r in json.loads(prepared().read_text())}
    testable = [i for i, r in recs.items() if r["geometry"]["status"] == "TESTABLE"]
    summary = {"contract": TESTS[TEST], "revision": t1._revision(), "prepared_sha256": t1.sha256_file(prepared()),
               "testable_by_kind": dict(sorted(Counter(recs[i]["stratum"][1] for i in testable).items())),
               "truth": "OpenStreetMap tags in the hashed snapshot; not verified road paint or legal limits",
               "engines": {}}
    for engine in ENGINES:
        path = work() / f"run-{engine}.json"
        if not path.exists():
            continue
        res = json.loads(path.read_text())
        if res.get("_provenance") != _provenance(engine):
            raise RuntimeError(f"{TESTS[TEST]} {engine}: stale/unprovenanced result")
        verdicts = {i: res[i].get("result", {}).get("verdict", res[i].get("route")) for i in testable if i in res}
        by_kind = defaultdict(Counter)
        for i, v in verdicts.items():
            by_kind[recs[i]["stratum"][1]][v] += 1
        judged = [v for v in verdicts.values() if v in ("CORRECT", "WRONG", "NOT_GIVEN", "GUESSED")]
        summary["engines"][engine] = {
            "correct": sum(v == "CORRECT" for v in judged), "judged": len(judged),
            "wrong": sorted(i for i, v in verdicts.items() if v in ("WRONG", "GUESSED")),
            "not_given": sorted(i for i, v in verdicts.items() if v == "NOT_GIVEN"),
            "by_kind": {k: dict(c) for k, c in sorted(by_kind.items())}}
    for engine in ("Valhalla", "openrouteservice", "BRouter"):
        summary["engines"][engine] = {"status": "NOT_AVAILABLE: no lanes/limits in its route answer"}
    (work() / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))


def brief() -> int:
    s = json.loads((work() / "summary.json").read_text())
    lines = [f"{s['contract']} @ {s['revision'][:12]}: testable {s['testable_by_kind']}"]
    for e, v in s["engines"].items():
        lines.append(f"- {e}: " + (v["status"] if "status" in v else
                                   f"correct {v['correct']}/{v['judged']}; wrong {len(v['wrong'])}; "
                                   f"not given {len(v['not_given'])}; by kind {v['by_kind']}"))
    dmn = s["engines"].get("DMN", {})
    bad = [f"DMN gave a wrong answer in {len(dmn['wrong'])} case(s)"] if dmn.get("wrong") else []
    lines.append("RESULT: " + ("; ".join(bad) if bad else "OK") + " (scored separately; no total)")
    print("\n".join(lines))
    return 0  # a wrong DMN answer is a finding to report, not a broken harness


def main() -> int:
    global TEST
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", choices=sorted(TESTS), required=True)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ("select", "prepare"):
        sub.add_parser(cmd).add_argument("--source", type=Path, default=a1.SOURCE)
    rp = sub.add_parser("run")
    rp.add_argument("--engine", choices=ENGINES, required=True)
    rp.add_argument("--only", nargs="*")
    sub.add_parser("score")
    sub.add_parser("brief")
    args = parser.parse_args()
    TEST = args.test
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
