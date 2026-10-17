"""Run D: quick targeted checks, categories 7, 14, 17, 18 and 21, DMN + 6 reference engines.

Owner-approved grouping (17 Oct 2026): the checks share set-up, each category keeps its
own frozen cases, rules, verdicts and ranking; never one combined score. Every case
reuses a frozen JOURNEY-001 clip (hash-checked); nothing is reused from earlier runs.

7  SPEED-001     route calculation time, warm, on one machine, all engines in turn.
                 Scope A: localhost HTTP round trip (DMN behind a small local server
                 like the others; OsmAnd has no server, so it is not in scope A).
                 Scope B: in-process route call after the map is loaded (DMN, OsmAnd).
                 Map import/build time is setup: recorded, never ranked.
21 ADAPTER-001   comparison integrity of the harness itself, per engine: repeated
                 answers identical, start/finish at the requested points, drawn line
                 readable as OSM roads, DMN's server answer equal to its direct call.
14 CLOSURE-001   a road on the journey is closed (access=no written into the same
                 clip for every engine); the route must not use it and should find
                 the detour. DMN is also asked through its live-closure input
                 (blocked_edges on the open map), which must give the same route.
17 MAPDAMAGE-001 damaged map files (cut short, bytes changed, no roads), then the good
                 map again. DMN is fed through its offline package store (checks a
                 SHA-256 manifest); DMN's update/rollback is DMN-only.
18 BADREQ-001    bad requests on a good map: same start and finish, an unreachable
                 destination, a destination outside the map, an impossible latitude,
                 then a normal request again (still alive, same answer).

Truth is map-derived from the hashed OSM snapshot (not independent UK road law).
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import os
import re
import shutil
import socket
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from benchmarks import access001_route as a1
from benchmarks import barrier001_route as b1
from benchmarks import extra_engines as xe
from benchmarks import journey001 as j1
from benchmarks import turn001_restrictions as t1

ROOT = t1.ROOT
WORK = ROOT / "results" / "rund"
PREPARED = ROOT / "config" / "rund-prepared.json"
CONTRACT = "RUN-D v1"
ENGINES = ("DMN", *xe.ENGINES)
SPEED_PER_STRATUM, CLOSURE_PER_STRATUM, ROBUST_CASES = 3, 4, 3
REPEATS = 10  # timed queries after one warm-up query
DEST_RING_M = (700.0, 1300.0)  # closure journeys: destination this far from the junction
MAX_DETOUR_RATIO = 3.0
ISLAND_CLEAR_M = 150.0  # unreachable destination: no road of the origin's network this close
SUBSTITUTE_M = 25.0  # a route ending this far from the asked destination went somewhere else
SAME_POINT_MAX_M = 50.0
DMN_PORT = 8091
QUERY_TIMEOUT_S = 30


def _h(label: str) -> str:
    return hashlib.sha256(f"RUN-D:{label}".encode()).hexdigest()


# --------------------------------------------------------------------------- map helpers
def directed_edges(clip: a1.AccessClip, restricted_too: bool = False) -> dict[str, list[tuple[str, str, float]]]:
    """node -> [(next node, way, metres)] over car roads, one-way aware, no closed barriers.

    restricted_too: also private/destination-style roads (only roads closed to cars are left out)."""
    closed = {n for n, tags in clip.barriers.items() if b1.barrier_class(tags) == "closed"}
    out: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
    for way, (refs, tags) in clip.ways.items():
        if not clip.drivable(tags) and not (restricted_too and clip.no_car.get(way, ("",))[0] == "restricted"):
            continue
        for a, b in zip(refs, refs[1:]):
            if a not in clip.coords or b not in clip.coords or a in closed or b in closed:
                continue
            m = t1.metres(clip.coords[a], clip.coords[b])
            if clip.can_travel(way, a, b):
                out[a].append((b, way, m))
            if clip.can_travel(way, b, a):
                out[b].append((a, way, m))
    return out


def shortest(graph, start: str, goal: str, skip_way: str | None = None) -> tuple[float, list[str], list[str]] | None:
    """Length-shortest node path (turn restrictions ignored: used to choose cases only)."""
    best, prev, todo = {start: 0.0}, {}, [(0.0, start)]
    while todo:
        d, n = heapq.heappop(todo)
        if n == goal:
            nodes, ways = [n], []
            while n in prev:
                n, w = prev[n]
                nodes.append(n)
                ways.append(w)
            return d, nodes[::-1], ways[::-1]
        if d > best[n]:
            continue
        for m, w, length in graph.get(n, ()):
            if w == skip_way:
                continue
            if d + length < best.get(m, math.inf):
                best[m], prev[m] = d + length, (n, w)
                heapq.heappush(todo, (d + length, m))
    return None


def close_way(raw: bytes, way: str) -> bytes:
    """The same clip with one way closed to all traffic (access=no, overriding keys removed)."""
    text = raw.decode()
    m = re.search(rf'<way id="{way}"[^>]*>(.*?)</way>', text, re.S)
    if m is None:
        raise RuntimeError(f"way {way} not in clip")
    body = re.sub(r'\s*<tag k="(access|vehicle|motor_vehicle|motorcar|oneway)[^"]*" v="[^"]*"/>', "", m.group(1))
    body = body.rstrip() + '\n    <tag k="access" v="no"/>\n  '
    return (text[:m.start(1)] + body + text[m.end(1):]).encode()


def write_pbf(folder: Path, raw: bytes) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "clip.osm").write_bytes(raw)
    subprocess.run(["osmium", "cat", "--overwrite", str(folder / "clip.osm"), "-o", str(folder / "clip.osm.pbf")],
                   check=True, capture_output=True)


def judge(clip: a1.AccessClip, geom: dict, nodes: list[str] | None, closed_way: str | None = None,
          closed_refs: list[str] | None = None) -> dict:
    """Route verdict on `clip`; closed_way: that road counts as closed (it is closed in `clip`);
    closed_refs: only report whether the route uses that road (the open map of a closure case)."""
    if nodes is None:
        return {"route": "NO_ROUTE"}
    rules = t1.audit_route(clip, nodes)
    extra = {**b1.audit_barriers(clip, nodes, ""), **a1.audit_roads(clip, nodes, "")}
    breaks = extra["other_closed_barriers"] + extra["other_closed_roads"]
    anchored = nodes[:2] == list(geom["origin_segment"]) and nodes[-2:] == list(geom["destination_segment"])
    length = sum(t1.metres(clip.coords[x], clip.coords[y]) for x, y in zip(nodes, nodes[1:])
                 if x in clip.coords and y in clip.coords)
    out = {"path": nodes, "length_m": round(length, 1), "violations": sorted(rules["violations"] + breaks)}
    if closed_way is not None or closed_refs is not None:
        out["uses_closed_road"] = a1.uses_way(nodes, closed_refs or clip.ways[closed_way][0])
    legal = "ILLEGAL" if breaks or out.get("uses_closed_road") else rules["route_legal"]
    out["route"] = ("VALID" if anchored and legal == "LEGAL" else "ILLEGAL" if legal == "ILLEGAL" else
                    "OFF_TARGET" if not anchored else "CONDITIONAL")
    return out


# --------------------------------------------------------------------------- prepare (frozen)
def _testable() -> list[dict]:
    return [r for r in json.loads(j1.PREPARED.read_text()) if r["geometry"]["status"] == "TESTABLE"]


def _first(records: list[dict], per: int) -> list[dict]:
    seen, out = Counter(), []
    for r in records:
        key = "/".join(r["stratum"])
        if seen[key] < per:
            out.append(r)
            seen[key] += 1
    return out


def closure_journey(record: dict, raw: bytes) -> dict:
    clip = a1.AccessClip(raw)
    geom = record["geometry"]
    graph = directed_edges(clip)
    o_seg = list(geom["origin_segment"])
    o_way = next((w for w in clip.drivable_ways(o_seg[0]) if a1.uses_way(o_seg, clip.ways[w][0])), None)
    centre = clip.coords[geom.get("junction") or geom.get("entry")]
    candidates = []
    for way, (refs, tags) in clip.ways.items():
        if not clip.drivable(tags) or tags.get("junction") in ("roundabout", "circular"):
            continue
        for a, b in zip(refs, refs[1:]):
            if a not in clip.coords or b not in clip.coords:
                continue
            seg_m = t1.metres(clip.coords[a], clip.coords[b])
            mid = ((clip.coords[a][0] + clip.coords[b][0]) / 2, (clip.coords[a][1] + clip.coords[b][1]) / 2)
            if seg_m < a1.MIN_SEGMENT_M or not DEST_RING_M[0] <= t1.metres(mid, centre) <= DEST_RING_M[1]:
                continue
            for x, y in ((a, b), (b, a)):
                if clip.can_travel(way, x, y):
                    candidates.append((_h(f"{record['id']}:{way}:{x}:{y}"), way, x, y, mid))
    for _, d_way, x, y, mid in sorted(candidates)[:60]:
        base = shortest(graph, o_seg[1], x)
        if base is None:
            continue
        length, nodes, ways = base
        nodes, ways = [o_seg[0], *nodes, y], [o_way, *ways, d_way]
        eligible = [w for w in dict.fromkeys(ways) if w not in (o_way, d_way)
                    and clip.ways[w][1].get("junction") not in ("roundabout", "circular")]
        if not eligible:
            continue
        # the way carrying the middle of the journey (or the nearest eligible one to it)
        acc, mids = 0.0, {}
        for (p, q), w in zip(zip(nodes, nodes[1:]), ways):
            mids.setdefault(w, acc)
            acc += t1.metres(clip.coords[p], clip.coords[q])
        closed = min(eligible, key=lambda w: (abs(mids[w] - acc / 2), w))
        detour = shortest(graph, o_seg[1], x, skip_way=closed)
        if detour is None or detour[0] > MAX_DETOUR_RATIO * length:
            continue
        closed_raw = close_way(raw, closed)
        return {"status": "TESTABLE", "origin": geom["origin"], "origin_segment": o_seg,
                "destination": [round(mid[0], 7), round(mid[1], 7)], "destination_segment": [x, y],
                "closed_way": closed, "closed_highway": clip.ways[closed][1].get("highway"),
                "map_shortest_m": round(length + t1.metres(clip.coords[x], clip.coords[y]), 1),
                "map_detour_m": round(detour[0] + t1.metres(clip.coords[x], clip.coords[y]), 1),
                "closed_clip_sha256": hashlib.sha256(closed_raw).hexdigest()}
    return {"status": "NO_SUITABLE_JOURNEY"}


def island_destination(record: dict, raw: bytes) -> dict | None:
    """A car road segment the origin cannot reach by any road (private ones included), well clear
    of the origin's network."""
    clip = a1.AccessClip(raw)
    graph = directed_edges(clip, restricted_too=True)
    undirected = defaultdict(set)
    for a, outs in graph.items():
        for b, _, _ in outs:
            undirected[a].add(b)
            undirected[b].add(a)
    start = record["geometry"]["origin_segment"][1]
    main, todo = {start}, [start]
    while todo:
        for m in undirected[todo.pop()]:
            if m not in main:
                main.add(m)
                todo.append(m)
    main_pts = [clip.coords[n] for n in main]
    found = []
    for a, outs in graph.items():
        if a in main:
            continue
        for b, way, m in outs:
            if b not in main and m >= a1.MIN_SEGMENT_M:
                found.append((_h(f"island:{record['id']}:{way}:{a}:{b}"), way, a, b))
    for _, way, a, b in sorted(found)[:200]:
        mid = ((clip.coords[a][0] + clip.coords[b][0]) / 2, (clip.coords[a][1] + clip.coords[b][1]) / 2)
        near = min((t1.metres(mid, p) for p in main_pts if abs(p[0] - mid[0]) < 0.01 and abs(p[1] - mid[1]) < 0.02),
                   default=math.inf)
        if near >= ISLAND_CLEAR_M:
            return {"destination": [round(mid[0], 7), round(mid[1], 7)], "destination_segment": [a, b],
                    "way": way, "clear_of_origin_network_m": round(near, 1)}
    return None


def prepare() -> None:
    testable = _testable()
    closure = _first(testable, CLOSURE_PER_STRATUM)
    robust = []
    for r in testable:  # first cases (prepared order) that also have an unreachable island destination
        if len(robust) == ROBUST_CASES:
            break
        island = island_destination(r, j1.case_clip(r))
        if island:
            robust.append({"id": r["id"], "island": island})
        print("robust", r["id"], bool(island), flush=True)
    journeys = []
    for r in closure:
        journeys.append({"id": r["id"], "journey": closure_journey(r, j1.case_clip(r))})
        print("closure", r["id"], journeys[-1]["journey"]["status"], flush=True)
        subprocess.run(["rm", "-rf", str(j1.WORK / "cases" / r["id"])], check=False)
    ok = [r for r, j in zip(closure, journeys) if j["journey"]["status"] == "TESTABLE"]
    speed = _first(ok, SPEED_PER_STRATUM)
    out = {"contract": CONTRACT, "frozen_before_engine_runs": True,
           "journey001_prepared_sha256": t1.sha256_file(j1.PREPARED),
           "rules": {"speed": f"the first {SPEED_PER_STRATUM} closure journeys per stratum on the OPEN map, 1 warm-up "
                              f"+ {REPEATS} timed identical queries per engine, engines rotated per case, one machine",
                     "closure": f"first {CLOSURE_PER_STRATUM} testable cases per stratum; destination: first car "
                                f"segment by sha256 {DEST_RING_M[0]:.0f}-{DEST_RING_M[1]:.0f} m from the junction "
                                "with a map path; closed way: the non-roundabout way carrying the middle of the "
                                f"length-shortest map path (not the start or finish way), detour <= "
                                f"{MAX_DETOUR_RATIO}x; closed by access=no in the clip given to every engine",
                     "robust": f"first {ROBUST_CASES} testable cases with a car road the origin cannot reach "
                               f">= {ISLAND_CLEAR_M:.0f} m from the origin's road network"},
           "speed": [r["id"] for r in speed], "closure": journeys, "robust": robust}
    text = json.dumps(out, indent=1, sort_keys=True)
    if PREPARED.exists() and PREPARED.read_text() != text:
        raise SystemExit("Prepared Run D cases differ from the frozen config/rund-prepared.json")
    PREPARED.write_text(text)
    print(Counter(j["journey"]["status"] for j in journeys), len(robust))


# --------------------------------------------------------------------------- DMN
class DMNMap:
    """One imported clip: route between test segments, optionally with closed (blocked) roads."""

    def __init__(self, raw: bytes):
        from map_data import Provenance, import_osm_xml
        began = time.perf_counter()
        self.imported = import_osm_xml(raw, provenance=Provenance(
            region="Greater Manchester (Run D clip)", snapshot="openstreetmap.fr north_west 7332146",
            source="OpenStreetMap", attribution="© OpenStreetMap contributors, ODbL"))
        self.import_ms = (time.perf_counter() - began) * 1000
        self.graph = self.imported.graph
        self.by_pair = {(e.source, e.target): e for e in self.graph.edges.values()}

    def route(self, o_seg, d_seg, blocked_way: str | None = None, maneuvers: bool = True) -> dict:
        from engine import RouteNotFound, shortest_route
        from engine.maneuvers import principal_maneuvers
        start = self.by_pair.get(tuple(f"osm:{n}" for n in o_seg))
        finish = self.by_pair.get(tuple(f"osm:{n}" for n in d_seg))
        if start is None or finish is None:
            return {"route": "ENDPOINT_NOT_IN_MAP"}
        if "prohibited" in (start.access, finish.access):
            return {"route": "ENDPOINT_WITHHELD_BY_POLICY"}
        blocked = [e.edge_id for e in self.graph.edges.values()
                   if e.edge_id.split(":")[1] == blocked_way] if blocked_way else ()
        try:
            r = shortest_route(self.graph, start.target, finish.target, incoming_edge_id=start.edge_id,
                               destination_edge_id=finish.edge_id, endpoint_uncertain_access=True,
                               blocked_edges=blocked)
        except RouteNotFound:
            return {"route": "NO_ROUTE"}
        edges = [start.edge_id, *r.edge_ids]
        nodes = [start.source.removeprefix("osm:")] + [self.graph.edges[e].target.removeprefix("osm:") for e in edges]
        nodes = [n for i, n in enumerate(nodes) if i == 0 or nodes[i - 1] != n]
        out = {"nodes": nodes}
        if maneuvers:  # the same kind of answer the other engines give: line plus turn list
            try:
                out["maneuvers"] = len(principal_maneuvers(self.graph, self.imported.coordinates, edges, []))
            except ValueError as exc:
                out["maneuvers"] = f"refused: {exc}"[:120]
        return out


def dmn_serve(clip_path: Path, port: int) -> None:
    """DMN behind a minimal localhost HTTP server, so its timing scope matches the others."""
    from http.server import BaseHTTPRequestHandler, HTTPServer
    dmn = DMNMap(clip_path.read_bytes())

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - http.server API
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            try:
                answer = dmn.route(body["origin_segment"], body["destination_segment"])
                code = 200
            except ValueError as exc:
                answer, code = {"error": str(exc)[:200]}, 400
            data = json.dumps(answer).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ready")

        def log_message(self, *args):
            pass

    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


class DMNServer:
    def __init__(self, folder: Path):
        self.proc = subprocess.Popen([sys.executable, "-m", "benchmarks.run_d", "dmn-serve",
                                      str(folder / "clip.osm"), str(DMN_PORT)], cwd=ROOT,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 120
        while time.time() < deadline:
            with socket.socket() as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", DMN_PORT)) == 0:
                    return
            if self.proc.poll() is not None:
                raise RuntimeError("DMN server exited")
            time.sleep(0.2)
        raise RuntimeError("DMN server did not start")

    def ask(self, geom: dict) -> tuple[dict, float]:
        body = json.dumps({"origin_segment": geom["origin_segment"],
                           "destination_segment": geom["destination_segment"]}).encode()
        began = time.perf_counter()
        data = t1._http_json(f"http://127.0.0.1:{DMN_PORT}/route", body)
        return data, (time.perf_counter() - began) * 1000

    def close(self) -> None:
        self.proc.terminate()
        self.proc.wait(timeout=30)


# --------------------------------------------------------------------------- 7 + 21: speed and adapters
def _geometry_key(points) -> str:
    return hashlib.sha256(json.dumps([[round(a, 6), round(b, 6)] for a, b in points or []]).encode()).hexdigest()


def speed_case(engine: str, record: dict, raw: bytes, clip, geom: dict, folder: Path) -> dict:
    headings = t1.travel_headings(clip, geom)
    out: dict = {"engine": engine}
    if engine == "DMN":
        began = time.perf_counter()
        dmn = DMNMap(raw)
        out["setup_ms"] = round((time.perf_counter() - began) * 1000, 1)
        timings, answers = [], []
        for k in range(REPEATS + 1):
            t0 = time.perf_counter()
            ans = dmn.route(geom["origin_segment"], geom["destination_segment"])
            if k:
                timings.append((time.perf_counter() - t0) * 1000)
            answers.append(json.dumps(ans.get("nodes")))
        out["scope_b_ms"] = [round(x, 2) for x in timings]
        direct = answers[-1]
        server = DMNServer(folder)
        try:
            http, answers_http = [], []
            for k in range(REPEATS + 1):
                ans, ms = server.ask(geom)
                if k:
                    http.append(ms)
                answers_http.append(json.dumps(ans.get("nodes")))
        finally:
            server.close()
        out["scope_a_ms"] = [round(x, 2) for x in http]
        nodes = json.loads(direct)
        out.update(judge(clip, geom, nodes))
        out["checks"] = {"deterministic": len(set(answers + answers_http)) == 1,
                         "anchored_start_finish": out["route"] != "OFF_TARGET" and nodes is not None,
                         "line_on_roads": "NOT_APPLICABLE_NODE_PATH",
                         "server_equals_direct_call": answers_http[-1] == direct}
        return out
    began = time.perf_counter()
    try:
        with xe.serve(engine, folder / "clip.osm.pbf", folder / engine.lower()):
            out["setup_ms"] = round((time.perf_counter() - began) * 1000, 1)
            if engine == "OsmAnd":
                data = osmand_repeat(geom, headings)
                if data["points"] is None:
                    out["route"] = "NO_ROUTE"
                    return out
                points = [tuple(p) for p in data["points"]]
                out["scope_b_ms"] = data["repeat_ms"]
                keys = {_geometry_key(points)} | ({"differs"} if not data["repeat_same"] else set())
            else:
                keys, timings = set(), []
                for k in range(REPEATS + 1):
                    points, _, ms = xe.query(engine, geom, headings)
                    if k:
                        timings.append(round(ms, 2))
                    keys.add(_geometry_key(points))
                out["scope_a_ms"] = timings
    except xe.MapRejected as exc:
        return {**out, "route": "ENGINE_REJECTED_MAP", "detail": str(exc)[:300]}
    except Exception as exc:  # noqa: BLE001 - recorded, never hidden
        return {**out, "route": "ERROR", "detail": f"{type(exc).__name__}: {exc}"[:300]}
    if points is None:
        return {**out, "route": "NO_ROUTE"}
    nodes, snaps = xe.engine_path(clip, geom, points)
    out.update(judge(clip, geom, nodes))
    out.update(snaps)
    line = j1.line_adherence(clip, nodes, points)
    out["checks"] = {
        "deterministic": len(keys) == 1,
        "anchored_start_finish": (snaps["start_snap_m"] or 0) <= t1.SNAP_TOLERANCE_M
                                 and (snaps["end_snap_m"] or 0) <= t1.SNAP_TOLERANCE_M,
        "line_on_roads": line.get("status") == "MEASURED" and line["max_off_road_m"] <= 5.0,
        "server_equals_direct_call": "NOT_APPLICABLE"}
    out["line"] = line
    return out


def osmand_repeat(geom: dict, headings: tuple[int, int]) -> dict:
    """OsmAnd timed in-process (tools/rund/OsmAndRepeat.java): warm-up, then REPEATS timed searches."""
    home = xe.CACHE / "osmand"
    classes = home / "rund-classes"
    if not (classes / "OsmAndRepeat.class").exists():
        subprocess.run(["javac", "-cp", xe.osmand_classpath(home, with_helper=False), "-d", str(classes),
                        str(ROOT / "tools" / "rund" / "OsmAndRepeat.java")], check=True)
    o, d = geom["origin"], geom["destination"]
    cp = xe.osmand_classpath(home, with_helper=False) + f":{classes}"
    r = subprocess.run([xe.JAVA, "-Xmx1g", "-cp", cp, "OsmAndRepeat", str(xe._OSMAND_OBF), f"{o[0]:.7f}",
                        f"{o[1]:.7f}", f"{d[0]:.7f}", f"{d[1]:.7f}", str(headings[0]), str(REPEATS)],
                       capture_output=True, text=True, timeout=600, cwd=xe._OSMAND_OBF.parent)
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("{")), None)
    if line is None:
        raise RuntimeError(f"OsmAnd repeat helper gave no answer: {(r.stderr or r.stdout)[-200:]}")
    return json.loads(line)


def run_speed(engines: tuple[str, ...] = ENGINES) -> None:
    """All engines on ONE machine, case by case, engine order rotated per case."""
    prepared = json.loads(PREPARED.read_text())
    records = {r["id"]: r for r in _testable()}
    journeys = {j["id"]: j["journey"] for j in prepared["closure"]}
    out_path = WORK / "speed.json"
    WORK.mkdir(parents=True, exist_ok=True)
    results: dict = {"_provenance": _provenance("speed"), "_machine": _machine()}
    for k, case_id in enumerate(prepared["speed"]):
        record = records[case_id]
        raw = j1.case_clip(record)
        clip = a1.AccessClip(raw)
        geom = journeys[case_id]
        folder = j1.WORK / "cases" / case_id
        order = engines[k % len(engines):] + engines[:k % len(engines)]
        for engine in order:
            entry = speed_case(engine, record, raw, clip, geom, folder)
            results.setdefault(case_id, {})[engine] = entry
            out_path.write_text(json.dumps(results, indent=1, sort_keys=True))
            print(case_id, engine, entry.get("route"), _median(entry.get("scope_a_ms") or entry.get("scope_b_ms")),
                  flush=True)
        subprocess.run(["rm", "-rf", str(folder)], check=False)
    if xe.osmand_build():
        results["_osmand_build_sha256"] = xe.osmand_build()
        out_path.write_text(json.dumps(results, indent=1, sort_keys=True))


def _median(xs):
    return round(statistics.median(xs), 2) if xs else None


def _machine() -> dict:
    cpu = next((ln.split(":", 1)[1].strip() for ln in Path("/proc/cpuinfo").read_text().splitlines()
                if ln.startswith("model name")), "unknown") if Path("/proc/cpuinfo").exists() else "unknown"
    return {"cpu": cpu, "cores": os.cpu_count(), "python": sys.version.split()[0]}


# --------------------------------------------------------------------------- 14: closures
def run_closure(engine: str) -> None:
    prepared = json.loads(PREPARED.read_text())
    records = {r["id"]: r for r in _testable()}
    out_path = WORK / f"closure-{engine}.json"
    WORK.mkdir(parents=True, exist_ok=True)
    results: dict = {"_provenance": _provenance(f"closure-{engine}")}
    for item in prepared["closure"]:
        geom = item["journey"]
        if geom["status"] != "TESTABLE":
            continue
        raw = j1.case_clip(records[item["id"]])
        closed_raw = close_way(raw, geom["closed_way"])
        if hashlib.sha256(closed_raw).hexdigest() != geom["closed_clip_sha256"]:
            raise RuntimeError(f"{item['id']}: closed clip differs from the frozen hash")
        open_clip, closed_clip = a1.AccessClip(raw), a1.AccessClip(closed_raw)
        folder = WORK / "cases" / item["id"]
        entry = {}
        refs = open_clip.ways[geom["closed_way"]][0]
        for label, clip_raw, clip in (("open", raw, open_clip), ("closed", closed_raw, closed_clip)):
            closed = {"closed_way": geom["closed_way"]} if label == "closed" else {"closed_refs": refs}
            if engine == "DMN":
                ans = DMNMap(clip_raw).route(geom["origin_segment"], geom["destination_segment"], maneuvers=False)
                entry[label] = judge(clip, geom, ans.get("nodes"), **closed) \
                    if "nodes" in ans or ans["route"] == "NO_ROUTE" else ans
            else:
                write_pbf(folder, clip_raw)
                result = xe.route(engine, folder, clip, geom)
                if isinstance(result, dict):
                    entry[label] = result
                else:
                    points = result[0]
                    nodes = xe.engine_path(clip, geom, points)[0] if points is not None else None
                    entry[label] = judge(clip, geom, nodes, **closed)
        if engine == "DMN":  # DMN's live-closure input: the open map with the road's edges blocked
            ans = DMNMap(raw).route(geom["origin_segment"], geom["destination_segment"],
                                    blocked_way=geom["closed_way"], maneuvers=False)
            entry["live_blocked"] = judge(closed_clip, geom, ans.get("nodes"), geom["closed_way"]) \
                if "nodes" in ans or ans["route"] == "NO_ROUTE" else ans
        results[item["id"]] = entry
        out_path.write_text(json.dumps(results, indent=1, sort_keys=True))
        shutil.rmtree(folder, ignore_errors=True)
        subprocess.run(["rm", "-rf", str(j1.WORK / "cases" / item["id"])], check=False)
        print(item["id"], entry["open"].get("route"), entry["open"].get("uses_closed_road"),
              entry["closed"].get("route"), flush=True)


# --------------------------------------------------------------------------- 17: damaged maps
DAMAGE = ("truncated", "corrupted", "no_roads")
EMPTY_OSM = b"<?xml version='1.0' encoding='UTF-8'?>\n<osm version=\"0.6\" generator=\"run_d\">\n</osm>\n"


def damaged(data: bytes, kind: str) -> bytes:
    if kind == "truncated":
        return data[:len(data) // 2]
    if kind == "corrupted":
        mid = len(data) // 2
        return data[:mid] + bytes(b ^ 0xFF for b in data[mid:mid + 256]) + data[mid + 256:]
    raise ValueError(kind)


def _manifest(payload: bytes, anchors: list[str]) -> dict:
    return {"schema_version": 1, "format": "dmn-osm-xml-v1", "byte_length": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "provenance": {"region": "Greater Manchester (Run D clip)", "snapshot": "openstreetmap.fr north_west 7332146",
                           "source": "OpenStreetMap", "attribution": "© OpenStreetMap contributors, ODbL"},
            "required_nodes": anchors}


def _store_route(store, geom) -> str:
    try:
        r = store.route(f"osm:{geom['origin_segment'][1]}", f"osm:{geom['destination_segment'][0]}")
        return "ROUTE:" + hashlib.sha256(json.dumps(r.route.edge_ids).encode()).hexdigest()[:16]
    except Exception as exc:  # noqa: BLE001 - recorded
        return f"{type(exc).__name__}"


def dmn_damage(raw: bytes, geom: dict, other_raw: bytes, other_geom: dict) -> dict:
    """DMN offline package store: damaged updates refused, the good map stays active."""
    from map_data.offline import OfflineMapStore, PackageValidationError
    anchors = list(dict.fromkeys([f"osm:{geom['origin_segment'][1]}", f"osm:{geom['destination_segment'][0]}"]))
    store = OfflineMapStore()
    out = {}
    try:  # the good map first, exactly as cut
        store.activate(raw, _manifest(raw, anchors))
        out["good_map"] = {"verdict": "ACCEPTED_GOOD_MAP"}
    except PackageValidationError as exc:
        out["good_map"] = {"verdict": "GOOD_MAP_REFUSED", "detail": str(exc)[:160]}
        # the damage checks still run, on a labelled package with time-based (:conditional) tags removed
        raw = re.sub(rb'\s*<tag k="[^"]*:conditional" v="[^"]*"/>', b"", raw)
        out["package_note"] = "conditional tags removed so the damage checks could run"
        store.activate(raw, _manifest(raw, anchors))
    before = _store_route(store, geom)
    for kind in DAMAGE:
        payload = EMPTY_OSM if kind == "no_roads" else damaged(raw, kind)
        manifest = _manifest(EMPTY_OSM, anchors) if kind == "no_roads" else _manifest(raw, anchors)
        try:  # the manifest was made by the packager from the good file; the bytes were damaged later
            store.activate(payload, manifest)
            verdict = "ACCEPTED"
        except PackageValidationError as exc:
            verdict = "REFUSED"
            out[f"{kind}_reason"] = str(exc)[:120]
        except Exception as exc:  # noqa: BLE001 - a crash is a finding
            verdict = f"CRASH:{type(exc).__name__}"
        kept = _store_route(store, geom) == before
        out[kind] = {"verdict": verdict if kept or verdict != "REFUSED" else "REFUSED_BUT_OLD_MAP_LOST",
                     "old_map_still_routes_same": kept}
        # the importer alone (no manifest): informational, not ranked
        if kind != "no_roads":
            try:
                DMNMap(payload)
                out[kind]["importer_alone"] = "ACCEPTED"
            except Exception as exc:  # noqa: BLE001
                out[kind]["importer_alone"] = f"REFUSED:{type(exc).__name__}"
    # recovery: the good map again gives the same route
    store.activate(raw, _manifest(raw, anchors))
    out["recovery"] = {"verdict": "ROUTES_SAME" if _store_route(store, geom) == before else "DIFFERENT"}
    # DMN-only update: another area's map replaces this one; the old journey is no longer covered
    other_anchors = list(dict.fromkeys([f"osm:{other_geom['origin_segment'][1]}",
                                        f"osm:{other_geom['destination_segment'][0]}"]))
    if re.search(rb'<tag\s+k="[^"]*:conditional"', other_raw):  # same labelled removal as above
        other_raw = re.sub(rb'\s*<tag k="[^"]*:conditional" v="[^"]*"/>', b"", other_raw)
        out["update_note"] = "new area's conditional tags removed so the update check could run"
    store.activate(other_raw, _manifest(other_raw, other_anchors))
    new_ok, old = _store_route(store, other_geom).startswith("ROUTE:"), _store_route(store, geom)
    overlap = all(f'<node id="{n.removeprefix("osm:")}"'.encode() in other_raw for n in anchors)
    out["update"] = {"verdict": "OVERLAP_NOT_JUDGED" if overlap and old.startswith("ROUTE:") else
                     "PASS" if new_ok and old == "CoverageUnavailable" else "FAIL",
                     "new_area_routes": new_ok, "old_area_answer": old}
    return out


def engine_damage(engine: str, folder: Path, raw: bytes, clip, geom: dict) -> dict:
    out = {}
    write_pbf(folder, raw)
    good_pbf = (folder / "clip.osm.pbf").read_bytes()
    for kind in (*DAMAGE, "recovery"):
        if kind == "no_roads":
            write_pbf(folder, EMPTY_OSM)
        elif kind == "recovery":
            (folder / "clip.osm.pbf").write_bytes(good_pbf)
        else:
            (folder / "clip.osm.pbf").write_bytes(damaged(good_pbf, kind))
        began = time.perf_counter()
        result = xe.route(engine, folder, clip, geom)
        seconds = round(time.perf_counter() - began, 1)
        if isinstance(result, dict):
            detail = result.get("detail", "")
            hang = "did not" in detail and ("start" in detail or "answer" in detail)
            out[kind] = {"verdict": "NO_SERVER_TIMEOUT" if hang else "REFUSED", "detail": detail[:200],
                         "seconds": seconds}
            continue
        points = result[0]
        nodes = xe.engine_path(clip, geom, points)[0] if points is not None else None
        judged = judge(clip, geom, nodes)
        verdict = {"VALID": "GOOD_MAP_ROUTES" if kind == "recovery" else "ACCEPTED_ROUTED",
                   "NO_ROUTE": "ACCEPTED_NO_ROUTE"}.get(judged["route"], "ACCEPTED_" + judged["route"])
        out[kind] = {"verdict": verdict, "seconds": seconds, "route": judged["route"]}
    return out


# --------------------------------------------------------------------------- 18: bad requests
def bad_requests(engine: str, clip, geom: dict, island: dict, folder: Path | None, raw: bytes) -> dict:
    o = geom["origin"]
    heads = t1.travel_headings(clip, geom)
    piece_m = t1.metres(*(clip.coords[n] for n in geom["origin_segment"]))  # same-point allowance, every engine
    island_geom = {**geom, "destination": island["destination"], "destination_segment": island["destination_segment"]}
    requests = {
        "same_point": ({**geom, "destination": o, "destination_segment": geom["origin_segment"]}, (heads[0], heads[0])),
        "unreachable": (island_geom, (heads[0], t1.bearing(*(clip.coords[n] for n in island["destination_segment"])))),
        "outside_map": ({**geom, "destination": [o[0] + 0.3, o[1]]}, (heads[0], 0)),
        "bad_latitude": ({**geom, "destination": [91.0, o[1]]}, (heads[0], 0)),
    }
    out = {}
    if engine == "DMN":
        dmn = DMNMap(raw)
        control = dmn.route(geom["origin_segment"], geom["destination_segment"])
        # native form: start and finish on the same road piece (DMN has no position along a piece,
        # so "finish on the piece you are leaving" would force a lap; the piece itself is the answer)
        from engine import RouteNotFound, shortest_route
        piece = dmn.by_pair[tuple(f"osm:{n}" for n in geom["origin_segment"])]
        try:
            r = shortest_route(dmn.graph, piece.source, piece.target, destination_edge_id=piece.edge_id,
                               endpoint_uncertain_access=True)
            nodes = [piece.source.removeprefix("osm:")] + [dmn.graph.edges[e].target.removeprefix("osm:")
                                                          for e in r.edge_ids]
        except RouteNotFound:
            nodes = None
        out["same_point"] = _classify_nodes(clip, nodes, o, "same_point", piece_m)
        unreach = dmn.route(geom["origin_segment"], island["destination_segment"])
        out["unreachable"] = _classify_nodes(clip, unreach.get("nodes"), island["destination"], "unreachable")
        out["outside_map"] = {"verdict": "NOT_APPLICABLE",
                              "why": "DMN takes road segments, not coordinates; a point outside the map has no segment"}
        try:
            from engine import shortest_route
            shortest_route(dmn.graph, f"osm:{geom['origin_segment'][1]}", "osm:999999999999")
            out["bad_latitude"] = {"verdict": "ANSWERED_INVALID", "native_form": "unknown destination node"}
        except ValueError as exc:
            out["bad_latitude"] = {"verdict": "CLEAN_REFUSAL", "native_form": "unknown destination node",
                                   "detail": str(exc)[:120]}
        again = dmn.route(geom["origin_segment"], geom["destination_segment"])
        out["still_alive"] = {"verdict": "SAME_ANSWER" if again.get("nodes") == control.get("nodes") else "DIFFERENT"}
        return out
    with xe.serve(engine, folder / "clip.osm.pbf", folder / engine.lower()):
        control = xe.query(engine, geom, heads)[0]
        for name, (g, h) in requests.items():
            began = time.perf_counter()
            try:
                points = xe.query(engine, g, h)[0]
                seconds = time.perf_counter() - began
                if points is None:
                    out[name] = {"verdict": "CLEAN_REFUSAL", "detail": "no route"}
                else:
                    out[name] = _classify_points(points, g["destination"], name, piece_m)
                    if name == "unreachable" and out[name]["verdict"] == "ROUTE_OK":
                        # the map has no way there, so reaching it means crossing something closed
                        nodes = xe.engine_path(clip, g, points)[0]
                        out[name] = {**out[name], "verdict": "REACHED_UNREACHABLE",
                                     "violations": judge(clip, g, nodes).get("violations")}
            except Exception as exc:  # noqa: BLE001 - classified below
                seconds = time.perf_counter() - began
                text = f"{type(exc).__name__}: {exc}"
                out[name] = {"verdict": "HANG" if "timed out" in text.lower() or seconds >= QUERY_TIMEOUT_S
                             else "CLEAN_REFUSAL", "detail": text[:200]}
            out[name]["seconds"] = round(seconds, 2)
        try:
            again = xe.query(engine, geom, heads)[0]
            out["still_alive"] = {"verdict": "SAME_ANSWER" if _geometry_key(again) == _geometry_key(control)
                                  else "DIFFERENT"}
        except Exception as exc:  # noqa: BLE001
            out["still_alive"] = {"verdict": "CRASHED", "detail": f"{type(exc).__name__}: {exc}"[:200]}
    return out


def _classify_points(points, asked, name: str, piece_m: float = 0.0) -> dict:
    end = tuple(points[-1])
    gap = t1.metres(end, tuple(asked)) if -90 <= asked[0] <= 90 else math.inf
    length = sum(t1.metres(tuple(a), tuple(b)) for a, b in zip(points, points[1:]))
    if name == "same_point":  # the start point itself: no drive, or a few metres, is the sensible answer
        return {"verdict": "ROUTE_OK" if length <= SAME_POINT_MAX_M + piece_m else "LOOP", "length_m": round(length, 1)}
    return {"verdict": "ROUTE_OK" if gap <= SUBSTITUTE_M else "SUBSTITUTE",
            "end_gap_m": None if gap == math.inf else round(gap, 1), "length_m": round(length, 1)}


def _classify_nodes(clip, nodes, asked, name: str, piece_m: float = 0.0) -> dict:
    if nodes is None:
        return {"verdict": "CLEAN_REFUSAL", "detail": "no route"}
    return _classify_points([clip.coords[n] for n in nodes if n in clip.coords], asked, name, piece_m)


def run_robust(engine: str, test: str) -> None:
    prepared = json.loads(PREPARED.read_text())
    records = {r["id"]: r for r in _testable()}
    out_path = WORK / f"{test}-{engine}.json"
    WORK.mkdir(parents=True, exist_ok=True)
    results: dict = {"_provenance": _provenance(f"{test}-{engine}")}
    robust = prepared["robust"]
    for k, item in enumerate(robust):
        record = records[item["id"]]
        raw = j1.case_clip(record)
        clip = a1.AccessClip(raw)
        geom = record["geometry"]
        folder = WORK / "cases" / f"{test}-{item['id']}"
        try:
            if test == "damage":
                if engine == "DMN":
                    other = records[robust[(k + 1) % len(robust)]["id"]]
                    entry = dmn_damage(raw, geom, j1.case_clip(other), other["geometry"])
                else:
                    with _short_waits():
                        entry = engine_damage(engine, folder, raw, clip, geom)
            else:
                if engine != "DMN":
                    write_pbf(folder, raw)
                entry = bad_requests(engine, clip, geom, item["island"], folder, raw)
        except Exception as exc:  # noqa: BLE001 - a failed case is recorded, never hidden
            entry = {"error": f"{type(exc).__name__}: {exc}"[:300]}
        results[item["id"]] = entry
        out_path.write_text(json.dumps(results, indent=1, sort_keys=True))
        shutil.rmtree(folder, ignore_errors=True)
        print(item["id"], {k: v.get("verdict") for k, v in entry.items() if isinstance(v, dict)}, flush=True)
    if engine == "OsmAnd":
        results["_osmand_build_sha256"] = xe.osmand_build()
        out_path.write_text(json.dumps(results, indent=1, sort_keys=True))


class _short_waits:
    """A damaged map may stop an engine server from ever starting: wait 4 minutes, not 15."""

    def __enter__(self):
        self.saved = (t1._wait, xe._wait_ok)
        t1._wait = lambda url, seconds: self.saved[0](url, min(seconds, 240))
        xe._wait_ok = lambda url, seconds, proc: self.saved[1](url, min(seconds, 240), proc)

    def __exit__(self, *exc):
        t1._wait, xe._wait_ok = self.saved


# --------------------------------------------------------------------------- provenance, score, brief
def _provenance(name: str) -> dict:
    return {"schema": 1, "run": name, "revision": t1._revision(), "prepared_sha256": t1.sha256_file(PREPARED),
            "journey001_prepared_sha256": t1.sha256_file(j1.PREPARED), "runner_sha256": t1.sha256_file(Path(__file__)),
            "engines_sha256": t1.sha256_file(Path(xe.__file__))}


def _load(name: str) -> dict | None:
    path = WORK / f"{name}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if data.get("_provenance") != _provenance(name):
        raise RuntimeError(f"Run D {name}: stale/unprovenanced result")
    return data


def _ms(xs: list[float]) -> dict:
    if not xs:
        return {"median": None, "p95": None, "samples": 0}
    s = sorted(xs)
    return {"median": round(statistics.median(s), 2), "p95": round(s[min(len(s) - 1, round(0.95 * (len(s) - 1)))], 2),
            "samples": len(s)}


def score() -> None:
    prepared = json.loads(PREPARED.read_text())
    summary = {"contract": CONTRACT, "revision": t1._revision(), "prepared_sha256": t1.sha256_file(PREPARED),
               "truth": "OpenStreetMap geometry and tags in the hashed snapshot; not independent UK road law",
               "categories": {}}
    cats = summary["categories"]
    speed = _load("speed")
    if speed is None:
        cats["7_speed"] = cats["21_adapters"] = {"status": "NOT_RUN"}
    else:
        summary["machine"] = speed["_machine"]
        cases = [c for c in prepared["speed"] if c in speed]
        per = defaultdict(lambda: defaultdict(list))
        valid_everywhere = [c for c in cases if all(speed[c].get(e, {}).get("route") == "VALID" for e in ENGINES)]
        for c in cases:
            for e, r in speed[c].items():
                for scope in ("scope_a_ms", "scope_b_ms"):
                    if r.get(scope):
                        per[scope][e].append(statistics.median(r[scope]))
                if r.get("setup_ms") is not None:
                    per["setup_ms"][e].append(r["setup_ms"])
        common = defaultdict(lambda: defaultdict(list))
        for c in valid_everywhere:
            for e, r in speed[c].items():
                for scope in ("scope_a_ms", "scope_b_ms"):
                    if r.get(scope):
                        common[scope][e].append(statistics.median(r[scope]))
        rank = lambda d: sorted(({"engine": e, **_ms(v)} for e, v in d.items()), key=lambda x: x["median"])  # noqa: E731
        cats["7_speed"] = {
            "metric": "per case: median of the timed warm queries; table: median and p95 of those case medians",
            "scope_a_http_round_trip": {"all_answered_cases": rank(per["scope_a_ms"]),
                                        "cases_valid_for_every_engine": rank(common["scope_a_ms"]),
                                        "not_in_scope": ["OsmAnd (no server; its router is called in-process)"]},
            "scope_b_in_process_call": {"all_answered_cases": rank(per["scope_b_ms"]),
                                        "cases_valid_for_every_engine": rank(common["scope_b_ms"])},
            "setup_not_ranked_ms": {e: _ms(v) for e, v in per["setup_ms"].items()},
            "cases": len(cases), "cases_valid_for_every_engine": len(valid_everywhere),
            "routes": {e: dict(Counter(speed[c].get(e, {}).get("route") for c in cases)) for e in ENGINES}}
        adapters = {}
        for e in [e for e in ENGINES if any(e in speed[c] for c in cases)]:
            checks = Counter()
            fails = defaultdict(list)
            for c in cases:
                for name, ok in speed[c].get(e, {}).get("checks", {}).items():
                    if ok in (True, False):
                        checks[(name, ok)] += 1
                        if not ok:
                            fails[name].append(c)
                missing = speed[c].get(e, {}).get("route") in ("ERROR", "ENGINE_REJECTED_MAP", None)
                if missing:
                    fails["no_answer"].append(c)
            passed, total = sum(v for (n, ok), v in checks.items() if ok), sum(checks.values())
            adapters[e] = {"passed": passed, "total": total, "failed_cases": dict(fails)}
        cats["21_adapters"] = {"metric": "harness checks passed per engine (comparison integrity, not engine quality)",
                               "ranking": sorted(({"engine": e, **v} for e, v in adapters.items()),
                                                 key=lambda x: -(x["passed"] / x["total"] if x["total"] else -1))}
    # 14 closures
    closure = {}
    shortest = {}
    loaded = {e: _load(f"closure-{e}") for e in ENGINES}
    for item in prepared["closure"]:
        c = item["id"]
        lengths = [r[c]["closed"]["length_m"] for r in loaded.values()
                   if r and r.get(c, {}).get("closed", {}).get("route") == "VALID"]
        shortest[c] = min(lengths) if lengths else None
    for e, res in loaded.items():
        if res is None:
            closure[e] = {"status": "NOT_RUN"}
            continue
        cases = {c: v for c, v in res.items() if not c.startswith("_")}
        verdicts = Counter()
        drove, missed, longer, bit = [], [], [], 0
        for c, v in cases.items():
            closed = v["closed"]
            r = closed.get("route")
            if closed.get("uses_closed_road"):
                drove.append(c)
            verdicts[r] += 1
            if r == "NO_ROUTE" and shortest[c]:
                missed.append(c)
            if r == "VALID" and shortest[c] and closed["length_m"] > 1.2 * shortest[c]:
                longer.append(c)
            bit += bool(v["open"].get("uses_closed_road"))
        ratios = [cases[c]["closed"]["length_m"] / shortest[c] for c in cases
                  if cases[c]["closed"].get("route") == "VALID" and shortest[c]]
        closure[e] = {"verdicts": dict(verdicts), "drove_closed_road": drove,
                      "no_route_though_another_engine_found_a_detour": missed,
                      "detours": len(ratios),
                      "median_detour_vs_shortest": round(statistics.median(ratios), 3) if ratios else None,
                      "detour_over_1_2x_shortest": longer, "open_route_used_the_closed_road": bit, "cases": len(cases)}
        if e == "DMN":
            same = [c for c, v in cases.items() if v.get("live_blocked", {}).get("path") == v["closed"].get("path")]
            closure[e]["live_blocked_same_as_map_closure"] = f"{len(same)}/{len(cases)}"
    cats["14_closures"] = closure
    # 17 and 18
    for cat, test in (("17_map_damage", "damage"), ("18_bad_requests", "badreq")):
        table = {}
        for e in ENGINES:
            res = _load(f"{test}-{e}")
            if res is None:
                table[e] = {"status": "NOT_RUN"}
                continue
            counts = defaultdict(Counter)
            for c, v in res.items():
                if c.startswith("_"):
                    continue
                if "error" in v:
                    counts["case_error"][v["error"][:80]] += 1
                    continue
                for kind, x in v.items():
                    if isinstance(x, dict) and "verdict" in x:
                        counts[kind][x["verdict"]] += 1
            good = {"damage": {"REFUSED", "ROUTES_SAME", "GOOD_MAP_ROUTES", "PASS", "ACCEPTED_GOOD_MAP"},
                    "badreq": {"CLEAN_REFUSAL", "ROUTE_OK", "SAME_ANSWER"}}[test]
            passed = sum(n for kind, cnt in counts.items() for v, n in cnt.items()
                         if v in good or (test == "damage" and kind == "no_roads" and v == "ACCEPTED_NO_ROUTE"))
            judged = sum(n for kind, cnt in counts.items() for v, n in cnt.items() if v != "NOT_APPLICABLE")
            table[e] = {"passed": passed, "judged": judged, "by_check": {k: dict(v) for k, v in counts.items()}}
        cats[cat] = table
    (WORK / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))


def brief() -> int:
    s = json.loads((WORK / "summary.json").read_text())
    c = s["categories"]
    lines = [f"{s['contract']} @ {s['revision'][:12]} (each category scored separately; no total)"]
    sp = c["7_speed"]
    if sp.get("status") != "NOT_RUN":
        lines.append(f"7 speed, {sp['cases']} cases ({sp['cases_valid_for_every_engine']} valid for every engine), "
                     f"machine {s.get('machine', {}).get('cpu')}")
        for scope in ("scope_a_http_round_trip", "scope_b_in_process_call"):
            lines.append(f"  {scope} median ms (p95): " + "; ".join(
                f"{r['engine']} {r['median']} ({r['p95']})" for r in sp[scope]["all_answered_cases"]))
        lines.append("21 adapter checks passed: " + "; ".join(
            f"{r['engine']} {r['passed']}/{r['total']}" for r in c["21_adapters"]["ranking"]))
    lines.append("14 closures VALID detour / drove closed road / missed detour: " + "; ".join(
        f"{e} {v.get('verdicts', {}).get('VALID', 0)}/{v.get('cases', 0)}, {len(v.get('drove_closed_road', []))}, "
        f"{len(v.get('no_route_though_another_engine_found_a_detour', []))}"
        for e, v in c["14_closures"].items() if v.get("status") != "NOT_RUN"))
    for cat in ("17_map_damage", "18_bad_requests"):
        lines.append(f"{cat.replace('_', ' ')} passed/judged: " + "; ".join(
            f"{e} {v['passed']}/{v['judged']}" for e, v in c[cat].items() if v.get("status") != "NOT_RUN"))
    dmn_drove = c["14_closures"].get("DMN", {}).get("drove_closed_road")
    bad = ["DMN drove a closed road"] if dmn_drove else []
    lines.append("RESULT: " + ("; ".join(bad) if bad else "OK"))
    print("\n".join(lines))
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare")
    sub.add_parser("speed").add_argument("--engines", nargs="*", choices=ENGINES, default=list(ENGINES))
    for name in ("closure", "damage", "badreq"):
        sub.add_parser(name).add_argument("--engine", choices=ENGINES, required=True)
    serve = sub.add_parser("dmn-serve")
    serve.add_argument("clip", type=Path)
    serve.add_argument("port", type=int)
    sub.add_parser("score")
    sub.add_parser("brief")
    args = parser.parse_args()
    if args.cmd == "prepare":
        prepare()
    elif args.cmd == "speed":
        run_speed(tuple(args.engines))
    elif args.cmd == "closure":
        run_closure(args.engine)
    elif args.cmd in ("damage", "badreq"):
        run_robust(args.engine, args.cmd)
    elif args.cmd == "dmn-serve":
        dmn_serve(args.clip, args.port)
    elif args.cmd == "score":
        score()
    else:
        return brief()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
