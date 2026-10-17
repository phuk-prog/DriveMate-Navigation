"""Run C: simulated drives, categories 3, 4, 6, 12, 13, 16, 20 (+19), DMN + 6 reference engines.

Owner-approved grouping (17 Oct 2026; started on the owner's word after run D): drives
share execution, each category keeps its own rules, verdicts and ranking; no combined
score. Journeys are the 24 frozen run D closure journeys (1-2 km, hashed JOURNEY-001
clips), on the OPEN map. Only GPS is simulated; maps are real OSM.

Each journey is driven three times at 10 m/s with one GPS fix a second (position noise
sigma 3 m, heading sigma 4 deg, deterministic seed per drive), then 5 stopped fixes:
  normal     the car follows the planned route;
  dropout    no fixes for 25 s from 45% of the way, then one 60 m multipath jump and one
             50 m-accuracy fix;
  wrong_turn at a frozen junction the car leaves the route onto another legal road and
             keeps going (straightest legal road) until it is given a new route; after
             400 m off route without one it is LOST.
The driven route is DMN's planned open-map route (frozen in config/runc-prepared.json
before any reference engine ran). It is only the path the car drives; GPS truth is the
car's own position on it, never an engine answer.

3  GPS matching (per fix): DMN live, fix by fix (directed road piece); OSRM /match,
   Valhalla trace_route and GraphHopper /match get the whole trace at once (batch).
4  GPS loss recovery: same, on the fixes after the dropout.
6  route quality: every engine's open-map route, length against the shortest valid one.
12 rerouting: every engine routes from a frozen point 120 m along the wrong road; DMN
   also closed loop (detection delay, false reroutes in normal/dropout drives).
13 instruction timing, 16 arrival, 20 whole journey, 19 memory/time: DMN only (the
   references expose no live guidance, arrival or announcement logic).
Truth is map-derived from the hashed snapshot, not independent UK road law.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import shutil
import statistics
import subprocess
import time
import tracemalloc
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from benchmarks import access001_route as a1
from benchmarks import extra_engines as xe
from benchmarks import journey001 as j1
from benchmarks import run_d as rd
from benchmarks import turn001_restrictions as t1

ROOT = t1.ROOT
WORK = ROOT / "results" / "runc"
PREPARED = ROOT / "config" / "runc-prepared.json"
CONTRACT = "RUN-C v1"
ENGINES = ("DMN", *xe.ENGINES)
MATCHERS = ("OSRM", "Valhalla", "GraphHopper")
SCENARIOS = ("normal", "dropout", "wrong_turn")
SPEED, ARRIVE_SPEED, ARRIVE_ZONE_M = 10.0, 3.0, 40.0  # m/s; the car slows for the last 40 m
PUBLIC = {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary",
          "secondary_link", "tertiary", "tertiary_link", "unclassified", "residential"}
SIGMA_M, SIGMA_DEG, ACCURACY_M = 3.0, 4.0, 5.0
DROPOUT_AT, DROPOUT_S, JUMP_M = 0.45, 25, 60.0
WRONG_FROM, WRONG_TO = 0.35, 0.75  # wrong turn at a junction in this share of the route
DEVIATION_M, REROUTE_POINT_M, LOST_M = 200.0, 120.0, 400.0
NODE_TOLERANCE_M = 5.0  # a fix this close to a junction may belong to either road piece
LINE_SNAP_M = 3.0  # batch matchers: their line must lie on a road piece this closely
CUE_WINDOW = (10.0, 60.0, 10.0)  # on time: first cue 10 m .. max(60 m, 10 s) before the turn
ARRIVAL_OK_M = 30.0
MAX_DRIVE_S = 600


def _seed(label: str) -> int:
    return int(hashlib.sha256(f"RUN-C:{label}".encode()).hexdigest()[:16], 16)


# --------------------------------------------------------------------------- geometry
def _xy(p, ref):
    k = 111_320 * math.cos(math.radians(ref[0]))
    return ((p[1] - ref[1]) * k, (p[0] - ref[0]) * 111_320)


def _ll(xy, ref):
    k = 111_320 * math.cos(math.radians(ref[0]))
    return (ref[0] + xy[1] / 111_320, ref[1] + xy[0] / k)


def _bearing(a, b) -> float:
    return t1.bearing(a, b) % 360


def straightest(clip, prev: str, node: str, avoid: set[str], metres: float) -> list[str]:
    """Nodes driven from node (arriving from prev) on the straightest legal public road (residential
    or bigger, no access tags: a typical wrong turn, not a car park or private lane), up to metres."""
    path, walked = [prev, node], 0.0
    while walked < metres:
        a, b = path[-2], path[-1]
        options = []
        for w in clip.drivable_ways(b):
            if not _public(clip, w):
                continue
            refs = clip.ways[w][0]
            for i, n in enumerate(refs):
                if n != b:
                    continue
                for k in (i - 1, i + 1):
                    if 0 <= k < len(refs) and refs[k] != a and refs[k] not in path and refs[k] not in avoid \
                            and refs[k] in clip.coords and clip.can_travel(w, b, refs[k]) \
                            and rd.b1.barrier_class(clip.barriers.get(refs[k], {})) != "closed" \
                            and t1.audit_route(clip, [a, b, refs[k]])["route_legal"] == "LEGAL":
                        turn = abs((_bearing(clip.coords[b], clip.coords[refs[k]])
                                    - _bearing(clip.coords[a], clip.coords[b]) + 180) % 360 - 180)
                        options.append((turn, refs[k]))
        if not options:
            break
        nxt = min(options)[1]
        walked += t1.metres(clip.coords[b], clip.coords[nxt])
        path.append(nxt)
    return path[1:]


def _public(clip, way: str) -> bool:
    tags = clip.ways[way][1]
    return tags.get("highway") in PUBLIC and not any(k in tags for k in ("access", "vehicle", "motor_vehicle",
                                                                         "motorcar"))


def maneuvers(clip, nodes: list[str]) -> list[int]:
    """Indexes of route nodes where guidance is due (DMN's own rule: >= 45 deg turn, or a
    roundabout entry)."""
    ring_pairs = {(a, b) for w, (refs, tags) in clip.ways.items() if tags.get("junction") in ("roundabout", "circular")
                  for a, b in zip(refs, refs[1:])}
    ring = lambda a, b: (a, b) in ring_pairs or (b, a) in ring_pairs  # noqa: E731
    out, i = [], 1
    while i < len(nodes) - 1:
        a, b, c = nodes[i - 1], nodes[i], nodes[i + 1]
        if ring(b, c) and not ring(a, b):
            out.append(i)
            while i < len(nodes) - 1 and ring(nodes[i], nodes[i + 1]):
                i += 1
            i += 1
            continue
        if not ring(a, b):
            d = abs((_bearing(clip.coords[b], clip.coords[c]) - _bearing(clip.coords[a], clip.coords[b]) + 180) % 360 - 180)
            if d >= 45:
                out.append(i)
        i += 1
    return out


# --------------------------------------------------------------------------- prepare (frozen)
def wrong_turn(clip, nodes: list[str], journey_id: str) -> dict | None:
    cum = [0.0]
    for a, b in zip(nodes, nodes[1:]):
        cum.append(cum[-1] + t1.metres(clip.coords[a], clip.coords[b]))
    on_route = set(nodes)
    for i in range(1, len(nodes) - 1):
        if not WRONG_FROM * cum[-1] <= cum[i] <= WRONG_TO * cum[-1]:
            continue
        p, n, q = nodes[i - 1], nodes[i], nodes[i + 1]
        firsts = sorted({r for w in clip.drivable_ways(n) if _public(clip, w) for r in _neighbours(clip, w, n)
                         if r not in (p, q) and r not in on_route and r in clip.coords
                         and clip.can_travel(w, n, r)
                         and t1.audit_route(clip, [p, n, r])["route_legal"] == "LEGAL"},
                        key=lambda r: rd._h(f"{journey_id}:{n}:{r}"))
        for r in firsts:
            walk = [n, *straightest(clip, n, r, on_route, DEVIATION_M)]
            length = sum(t1.metres(clip.coords[a], clip.coords[b]) for a, b in zip(walk, walk[1:]))
            if length < DEVIATION_M:
                continue
            acc = 0.0
            for a, b in zip(walk, walk[1:]):
                seg = t1.metres(clip.coords[a], clip.coords[b])
                if acc >= REROUTE_POINT_M and seg >= a1.MIN_SEGMENT_M:
                    mid = [(clip.coords[a][0] + clip.coords[b][0]) / 2, (clip.coords[a][1] + clip.coords[b][1]) / 2]
                    return {"index": i, "node": n, "first": r, "deviation": walk,
                            "reroute_origin_segment": [a, b], "reroute_origin": [round(mid[0], 7), round(mid[1], 7)],
                            "reroute_after_m": round(acc, 1)}
                acc += seg
    return None


def _neighbours(clip, way: str, node: str) -> list[str]:
    refs = clip.ways[way][0]
    return [refs[k] for i, x in enumerate(refs) if x == node for k in (i - 1, i + 1) if 0 <= k < len(refs)]


def prepare() -> None:
    rdp = json.loads(rd.PREPARED.read_text())
    records = {r["id"]: r for r in rd._testable()}
    journeys = []
    for item in rdp["closure"]:
        geom = item["journey"]
        if geom["status"] != "TESTABLE":
            continue
        raw = j1.case_clip(records[item["id"]])
        clip = a1.AccessClip(raw)
        ans = rd.DMNMap(raw).route(geom["origin_segment"], geom["destination_segment"], maneuvers=False)
        judged = rd.judge(clip, geom, ans.get("nodes"))
        entry = {"id": item["id"], "status": "TESTABLE" if judged["route"] == "VALID" else "NO_VALID_DRIVE_ROUTE"}
        if entry["status"] == "TESTABLE":
            nodes = ans["nodes"]
            wt = wrong_turn(clip, nodes, item["id"])
            entry.update({"drive_nodes": nodes, "drive_m": judged["length_m"], "wrong_turn": wt,
                          "maneuver_count": len(maneuvers(clip, nodes))})
            if wt is None:
                entry["status"] = "NO_WRONG_TURN_JUNCTION"
        journeys.append(entry)
        print(item["id"], entry["status"], flush=True)
        subprocess.run(["rm", "-rf", str(j1.WORK / "cases" / item["id"])], check=False)
    out = {"contract": CONTRACT, "frozen_before_reference_runs": True,
           "rund_prepared_sha256": t1.sha256_file(rd.PREPARED),
           "rules": {"drive": f"DMN open-map route, {SPEED} m/s ({ARRIVE_SPEED} m/s in the last {ARRIVE_ZONE_M:.0f} m), 1 fix/s, noise {SIGMA_M} m / {SIGMA_DEG} deg, "
                              f"accuracy {ACCURACY_M} m, seed sha256('RUN-C:<id>:<scenario>')",
                     "dropout": f"no fixes for {DROPOUT_S} s from {DROPOUT_AT:.0%} of the route, then a {JUMP_M:.0f} m "
                                "jump fix and a 50 m-accuracy fix",
                     "wrong_turn": f"first junction between {WRONG_FROM:.0%} and {WRONG_TO:.0%} of the route with "
                                   f"another legal public road (residential or bigger, no access tags) continuing "
                                   f">= {DEVIATION_M:.0f} m (straightest such road, "
                                   f"off the route); reference reroute point: first segment >= 5 m after "
                                   f"{REROUTE_POINT_M:.0f} m on it",
                     "cue": f"on time if the first cue comes {CUE_WINDOW[0]:.0f} m .. max({CUE_WINDOW[1]:.0f} m, "
                            f"{CUE_WINDOW[2]:.0f} s) before the turn",
                     "arrival": f"correct if declared within {ARRIVAL_OK_M:.0f} m of the destination"},
           "journeys": journeys}
    text = json.dumps(out, indent=1, sort_keys=True)
    if PREPARED.exists() and PREPARED.read_text() != text:
        raise SystemExit("Prepared Run C drives differ from the frozen config/runc-prepared.json")
    PREPARED.write_text(text)
    print(Counter(j["status"] for j in journeys))


# --------------------------------------------------------------------------- the car and its GPS
class Car:
    """Drives a node path at SPEED; the path after the current piece can be replaced."""

    def __init__(self, clip, geom: dict, nodes: list[str]):
        self.clip, self.geom = clip, geom
        self.nodes = list(nodes)
        self.start, self.end = tuple(geom["origin"]), tuple(geom["destination"])
        self.dist = 0.0
        self._build()

    def _build(self):
        pts = [self.start] + [self.clip.coords[n] for n in self.nodes[1:-1]] + [self.end]
        self.pts = pts
        self.cum = [0.0]
        for a, b in zip(pts, pts[1:]):
            self.cum.append(self.cum[-1] + t1.metres(a, b))
        self.length = self.cum[-1]

    def piece(self, dist: float | None = None) -> int:
        d = self.dist if dist is None else dist
        for k in range(len(self.cum) - 1):
            if d < self.cum[k + 1]:
                return k
        return len(self.cum) - 2

    def speed(self) -> float:
        return SPEED if self.length - self.dist > ARRIVE_ZONE_M else ARRIVE_SPEED

    def step(self) -> None:
        self.dist = min(self.length, self.dist + self.speed())

    def where(self):
        k = self.piece()
        a, b = self.pts[k], self.pts[k + 1]
        f = 0.0 if self.cum[k + 1] == self.cum[k] else (self.dist - self.cum[k]) / (self.cum[k + 1] - self.cum[k])
        return (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])), _bearing(a, b), k

    def true_edges(self) -> set[tuple[str, str]]:
        """The road piece the car is on, plus the neighbouring one when it is near a junction."""
        k = self.piece()
        out = {(self.nodes[k], self.nodes[k + 1])}
        if self.dist - self.cum[k] <= NODE_TOLERANCE_M and k > 0:
            out.add((self.nodes[k - 1], self.nodes[k]))
        if self.cum[k + 1] - self.dist <= NODE_TOLERANCE_M and k + 2 < len(self.nodes):
            out.add((self.nodes[k + 1], self.nodes[k + 2]))
        return out

    def distance_to_node(self, node: str) -> float | None:
        """Metres along the car's path to the next visit of node (None if not ahead)."""
        for k in range(self.piece() + 1, len(self.nodes) - 1):
            if self.nodes[k] == node:
                return self.cum[k] - self.dist
        return None

    def replace_after(self, k: int, nodes: list[str], end: tuple[float, float]) -> None:
        """Keep the path up to node index k (the current piece's end), then follow nodes."""
        self.nodes = self.nodes[:k + 1] + nodes[1:]
        self.end = end
        self._build()


def make_fix(rnd: random.Random, pos, bearing, t_ms: int, *, moving: bool = True, extra=None, speed=SPEED):
    from gps.fix_quality import GPSFix
    ref = pos
    if extra == "jump":  # multipath: 60 m to one side of the road
        side = math.radians(bearing + 90)
        lat, lon = _ll((JUMP_M * math.sin(side), JUMP_M * math.cos(side)), ref)
        return GPSFix(t_ms, lat, lon, 8.0, SPEED, bearing)
    lat, lon = _ll((rnd.gauss(0, SIGMA_M), rnd.gauss(0, SIGMA_M)), ref)
    if not moving:
        return GPSFix(t_ms, lat, lon, ACCURACY_M, 0.0, None)
    return GPSFix(t_ms, lat, lon, 50.0 if extra == "weak" else ACCURACY_M,
                  max(0.0, speed + rnd.gauss(0, 0.3)), (bearing + rnd.gauss(0, SIGMA_DEG)) % 360)


def open_trace(clip, geom: dict, nodes: list[str], journey_id: str, scenario: str) -> list[dict]:
    """The fixed (open-loop) trace of a normal or dropout drive: the same for every engine."""
    car = Car(clip, geom, nodes)
    rnd = random.Random(_seed(f"{journey_id}:{scenario}"))
    gap = (int(DROPOUT_AT * car.length / SPEED), int(DROPOUT_AT * car.length / SPEED) + DROPOUT_S) \
        if scenario == "dropout" else None
    out, t = [], 0
    while True:
        pos, brg, k = car.where()
        truth = sorted(car.true_edges())
        stopped = car.dist >= car.length
        extra = None
        if gap and t == gap[1] + 1:
            extra = "jump"
        elif gap and t == gap[1] + 2:
            extra = "weak"
        fix = make_fix(rnd, pos, brg, t * 1000, moving=not stopped, extra=extra, speed=car.speed())
        out_dist = car.dist
        if not (gap and gap[0] <= t <= gap[1]):
            out.append({"t": t, "fix": fix, "truth": truth, "pos": pos, "extra": extra, "dist": out_dist,
                        "after_gap_s": (t - gap[1]) if gap and t > gap[1] else None})
        if stopped:
            for s in range(1, 5):
                out.append({"t": t + s, "fix": make_fix(rnd, pos, brg, (t + s) * 1000, moving=False),
                            "truth": truth, "pos": pos, "extra": None, "dist": out_dist,
                            "after_gap_s": (t + s - gap[1]) if gap else None})
            return out
        car.step()
        t += 1


def trace_sha(trace: list[dict]) -> str:
    return hashlib.sha256(json.dumps([[r["t"], round(r["fix"].latitude, 7), round(r["fix"].longitude, 7)]
                                      for r in trace]).encode()).hexdigest()


# --------------------------------------------------------------------------- DMN closed-loop drive
def dmn_route(dmn: rd.DMNMap, o_seg, d_seg):
    from engine import RouteNotFound, shortest_route
    start = dmn.by_pair.get(tuple(f"osm:{n}" for n in o_seg))
    finish = dmn.by_pair.get(tuple(f"osm:{n}" for n in d_seg))
    if start is None or finish is None:
        return None, None
    try:
        r = shortest_route(dmn.graph, start.target, finish.target, incoming_edge_id=start.edge_id,
                           destination_edge_id=finish.edge_id, endpoint_uncertain_access=True)
    except RouteNotFound:
        return None, None
    from engine.routing import Route
    edges = (start.edge_id, *r.edge_ids)
    nodes = [start.source.removeprefix("osm:")] + [dmn.graph.edges[e].target.removeprefix("osm:") for e in edges]
    return Route(edges, r.length_m + start.length_m, r.estimated_seconds + start.estimated_seconds), nodes


def drive(dmn: rd.DMNMap, clip, geom: dict, plan: dict, scenario: str, improved: bool = False) -> dict:
    """One DMN drive, fix by fix: matcher -> on-route -> rerouting -> cues -> arrival."""
    from engine.arrival_controller import ArrivalController
    from engine.instruction_cues import instruction_phase, lead_seconds_for
    from engine.progress_estimator import ProgressEstimator
    from engine.route_check import destination_side
    from engine.rerouting_controller import ReroutingController
    from gps.matcher import DirectedRoadMatcher
    from gps.temporal_matcher import TemporalRoadMatcher
    jid = plan["id"]
    route, nodes = dmn_route(dmn, geom["origin_segment"], geom["destination_segment"])
    wt = plan["wrong_turn"]
    if scenario == "wrong_turn":
        i = wt["index"]
        cont = straightest(clip, wt["deviation"][-2], wt["deviation"][-1], set(plan["drive_nodes"]),
                           LOST_M - DEVIATION_M)
        car_nodes = plan["drive_nodes"][:i] + wt["deviation"] + cont[1:]
        leave_node = True
    else:
        car_nodes = list(plan["drive_nodes"])  # the frozen drive (equal to DMN's route unless DMN changed)
        leave_node = False
    car = Car(clip, geom, car_nodes)
    if scenario == "wrong_turn":  # no destination at the end of a lost drive: stop where the road ends
        car.end = clip.coords[car_nodes[-1]]
        car._build()
    trace = open_trace(clip, geom, plan["drive_nodes"], jid, scenario) if scenario != "wrong_turn" else None
    # improved = every owner-approved DMN change (17 Oct 2026); otherwise the pre-Run-C stack
    tm = TemporalRoadMatcher(DirectedRoadMatcher(dmn.graph, dmn.imported.coordinates,
                                                 same_road_pieces=improved,
                                                 route_aware_access=improved),
                             confirm_after_gap_ms=10000 if improved else None)
    tm.matcher.set_route(route.edge_ids)
    rc = ReroutingController(post_gap_ms=5000) if improved else ReroutingController()
    est = ProgressEstimator()
    ac = ArrivalController()
    rc.begin(route, now_ms=0)
    planned = {"nodes": nodes, "pairs": list(zip(nodes, nodes[1:])), "rev": ac.begin(
        tuple(geom["destination"]), route_length_m=route.length_m, now_ms=0)}

    def install(new_nodes):
        pairs = list(zip(new_nodes, new_nodes[1:]))
        cum = [0.0]
        for a, b in pairs:
            cum.append(cum[-1] + t1.metres(clip.coords[a], clip.coords[b]))
        planned.update(nodes=new_nodes, pairs=pairs, cum=cum, progress=0, mans=maneuvers(clip, new_nodes), spoken={})

    install(nodes)
    rnd = random.Random(_seed(f"{jid}:{scenario}"))
    log = {"fixes": [], "cues": [], "reroutes": [], "arrival": None, "lost": False}
    timings = []
    t, left_at, reached_at = 0, None, None
    stopped_fixes = 0
    while t <= MAX_DRIVE_S:
        if trace is not None:
            if t >= len(trace):
                break
            row = trace[t]
            fix, truth, pos = row["fix"], set(map(tuple, row["truth"])), row["pos"]
            car.dist = row["dist"]
            now = row["fix"].timestamp_ms
            clock = row["t"]
        else:
            pos, brg, _ = car.where()
            truth = car.true_edges()
            stopped = car.dist >= car.length
            fix = make_fix(rnd, pos, brg, t * 1000, moving=not stopped, speed=car.speed())
            now = t * 1000
            clock = t
            row = {"extra": None, "after_gap_s": None}
        if leave_node and left_at is None and car.piece() >= wt["index"]:
            left_at = clock  # the car has passed the junction onto the wrong road
        began = time.perf_counter()
        res = tm.update(fix, now_ms=now)
        matched = res.status == "MATCHED"
        edge = None
        if matched:
            e = dmn.graph.edges[res.edge_id]
            edge = (e.source.removeprefix("osm:"), e.target.removeprefix("osm:"))
        on_route = None
        if matched:
            idx = next((k for k in range(max(0, planned["progress"] - 2), len(planned["pairs"]))
                        if planned["pairs"][k] == edge), None)
            on_route = idx is not None
            if on_route:
                planned["progress"] = idx
                a, b = (clip.coords[n] for n in edge)
                ax, ay = _xy(a, (fix.latitude, fix.longitude))
                bx, by = _xy(b, (fix.latitude, fix.longitude))
                dx, dy = bx - ax, by - ay
                f = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
                along = planned["cum"][idx] + f * (planned["cum"][idx + 1] - planned["cum"][idx])
                est.confirm(timestamp_ms=now, along_m=along, speed_mps=fix.speed_mps or 0.0)
        request = rc.observe(timestamp_ms=now, now_ms=now, reliable=matched, on_route=on_route)
        if request is not None:
            new_route, new_nodes = dmn_route(dmn, list(edge), geom["destination_segment"])
            installed = rc.complete(request, new_route, now_ms=now)
            entry = {"t": clock, "from": list(edge), "installed": bool(installed and new_route),
                     "car_on_that_piece": edge in truth}
            if installed and new_route:
                install(new_nodes)
                est.reset()
                tm.matcher.set_route(new_route.edge_ids)
                planned["rev"] = ac.begin(tuple(geom["destination"]), route_length_m=new_route.length_m, now_ms=now)
                judged = rd.judge(clip, {"origin_segment": list(edge),
                                         "destination_segment": geom["destination_segment"]}, new_nodes)
                entry.update(route=judged["route"], length_m=judged.get("length_m"))
                # the driver follows the new route when it starts on the car's piece or the piece
                # just behind/ahead (within NODE_TOLERANCE_M of the joint, so the car moves < 5 m)
                here = car.piece()
                k = next((k for k in (here, here - 1, here + 1) if 0 <= k < len(car.nodes) - 1
                          and (car.nodes[k], car.nodes[k + 1]) == edge and edge in truth), None)
                if k is not None:
                    car.replace_after(k + 1, new_nodes[1:], tuple(geom["destination"]))
                    entry["followed"] = True
            log["reroutes"].append(entry)
        # guidance for the next turn on the installed route; improved: also from the short
        # estimate while the position is briefly unsure (never when the matcher says off route)
        cue_at = (along, 0) if on_route else (est.estimate(timestamp_ms=now) if improved and on_route is None
                                              else None)
        if cue_at is not None:
            cue_along, age = cue_at
            nxt = next((m for m in planned["mans"] if m > planned["progress"]), None)
            if nxt is not None:
                dist = planned["cum"][nxt] - cue_along
                key = (planned["rev"], nxt)
                speed = fix.speed_mps or 0.0
                phase = instruction_phase(distance_m=max(0.0, dist), speed_mps=speed,
                                          reliable_fix=True, on_correct_route=True, maneuver_verified=True,
                                          observation_age_ms=int(age), spoken_before=key in planned["spoken"],
                                          lead_seconds=lead_seconds_for(speed) if improved else 5.0,
                                          now_given=(key in planned.setdefault("now", set())) if improved else None)
                if phase == "NOW" and improved:
                    planned["now"].add(key)
                if phase in ("APPROACH", "NOW"):
                    planned["spoken"].setdefault(key, phase)
                    node = planned["nodes"][nxt]
                    true_d = car.distance_to_node(node)
                    car_off = not (truth & set(planned["pairs"]))
                    log["cues"].append({"t": clock, "rev": planned["rev"], "node": node, "phase": phase,
                                        "true_distance_m": None if true_d is None else round(true_d, 1),
                                        "car_off_route": car_off})
        remaining = planned["cum"][-1] - along if on_route else 1e9
        verdict = ac.observe(context_revision=planned["rev"], timestamp_ms=now, now_ms=now,
                             position=(fix.latitude, fix.longitude), accuracy_m=fix.horizontal_accuracy_m,
                             reliable=matched, on_route=bool(on_route), remaining_m=max(0.0, remaining),
                             speed_mps=fix.speed_mps if improved else None)
        timings.append((time.perf_counter() - began) * 1000)
        if verdict == "ARRIVED" and log["arrival"] is None:
            log["arrival"] = {"t": clock, "true_remaining_m": round(max(0.0, car.length - car.dist), 1),
                              "to_destination_m": round(t1.metres(pos, tuple(geom["destination"])), 1)}
            if improved:  # which side of the road the destination point is (UK: left is the kerb)
                last = dmn.by_pair.get(tuple(f"osm:{n}" for n in planned["pairs"][-1]))
                if last is not None:
                    log["arrival"]["destination_side"] = destination_side(
                        dmn.imported.coordinates, last, tuple(geom["destination"]))
        ok = "OK" if matched and edge in truth else "WRONG" if matched else "WITHHELD"
        if ok == "WRONG":  # the next/previous piece of the very same road, a few metres out: not a wrong road
            way = res.edge_id.split(":")[1]
            if any(dmn.by_pair.get((f"osm:{x}", f"osm:{y}")) is not None
                   and dmn.by_pair[(f"osm:{x}", f"osm:{y}")].edge_id.split(":")[1] == way for x, y in truth):
                ok = "SAME_ROAD_NEXT_PIECE"
        log["fixes"].append({"t": clock, "match": ok, "status": res.status, "reason": res.reason,
                             "extra": row.get("extra"),
                             "after_gap_s": row.get("after_gap_s")})
        if car.dist >= car.length and reached_at is None:
            reached_at = clock
        if trace is None:
            if car.dist >= car.length:
                stopped_fixes += 1
                if stopped_fixes > 5:
                    break
            car.step()
        t += 1
    end_ok = t1.metres(car.end, tuple(geom["destination"])) <= 1.0
    log["lost"] = scenario == "wrong_turn" and not end_ok
    log.update(left_route_at=left_at, reached_destination_at=reached_at if end_ok else None,
               ms_per_fix=rd._ms(timings), planned_m=round(route.length_m, 1),
               trace_sha256=trace_sha(trace) if trace else None)
    # did the car drive each cued/expected turn while that route was installed? (scored later)
    log["driven_nodes"] = car.nodes
    log["maneuver_nodes_first_route"] = [nodes[m] for m in maneuvers(clip, nodes)]
    return log


def memory_peak(dmn, clip, geom, plan) -> float:
    tracemalloc.start()
    drive(dmn, clip, geom, plan, "normal")
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return round(peak / 1e6, 2)


# --------------------------------------------------------------------------- reference matchers (batch)
def match_line(engine: str, trace: list[dict]) -> list[tuple[float, float]] | None:
    """The engine's matched road line for the whole trace (None: it matched nothing)."""
    fixes = [r["fix"] for r in trace]
    if engine == "OSRM":  # osrm-routed matches at most 100 points per request: windows of 90
        lines = []
        for s in range(0, len(fixes), 90):
            part = fixes[s:s + 90]
            if len(part) < 2:
                continue
            coords = ";".join(f"{f.longitude:.7f},{f.latitude:.7f}" for f in part)
            stamps = ";".join(str(f.timestamp_ms // 1000) for f in part)
            radii = ";".join(str(max(5, round(2 * f.horizontal_accuracy_m))) for f in part)
            url = (f"http://127.0.0.1:5000/match/v1/driving/{coords}?timestamps={stamps}&radiuses={radii}"
                   "&overview=full&geometries=geojson&gaps=split&tidy=false")
            try:
                data = t1._http_json(url)
            except HTTPError as exc:
                data = json.loads(exc.read() or b"{}")
            for m in data.get("matchings", []):
                lines.append([(lat, lon) for lon, lat in m["geometry"]["coordinates"]])
        return [p for line in lines for p in line] or None
    if engine == "Valhalla":
        body = json.dumps({"shape": [{"lat": f.latitude, "lon": f.longitude, "time": f.timestamp_ms // 1000}
                                     for f in fixes], "costing": "auto", "shape_match": "map_snap",
                           "use_timestamps": True}).encode()
        try:
            data = t1._http_json("http://127.0.0.1:8002/trace_route", body)
        except HTTPError as exc:
            raise RuntimeError(f"Valhalla trace_route {exc.code}: {(exc.read() or b'')[:200]!r}") from exc
        return [p for leg in data["trip"]["legs"] for p in t1._decode_polyline(leg["shape"], 6)] or None
    # GraphHopper /match takes GPX
    # simulated fixes only, serialised like benchmarks/graphhopper_match_reference.research_gpx
    import xml.etree.ElementTree as ET
    ns = "http://www.topografix.com/GPX/1/1"
    root = ET.Element("gpx", {"version": "1.1", "creator": "DMN-run-c-synthetic", "xmlns": ns})
    seg = ET.SubElement(ET.SubElement(root, "trk"), "trkseg")
    for f in fixes:
        when = datetime.fromtimestamp(1_700_000_000 + f.timestamp_ms / 1000, timezone.utc)
        pt = ET.SubElement(seg, "trkpt", {"lat": f"{f.latitude:.7f}", "lon": f"{f.longitude:.7f}"})
        ET.SubElement(pt, "time").text = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    req = Request("http://127.0.0.1:8989/match?profile=car&points_encoded=false&ch.disable=true"
                  "&way_point_max_distance=0",
                  ET.tostring(root, encoding="utf-8", xml_declaration=True), {"Content-Type": "application/gpx+xml"})
    try:
        with urlopen(req, timeout=60) as r:  # noqa: S310 - local engine only
            data = json.load(r)
    except HTTPError as exc:
        raise RuntimeError(f"GraphHopper /match {exc.code}: {(exc.read() or b'')[:200]!r}") from exc
    return [(lat, lon) for lon, lat in data["paths"][0]["points"]["coordinates"]] or None


def judge_line(clip, trace: list[dict], line) -> list[str]:
    """Per fix: the road piece of the engine's line nearest the fix, against the car's truth."""
    if not line:
        return ["WITHHELD"] * len(trace)
    segs = []
    for a, b in zip(line, line[1:]):
        if t1.metres(a, b) > 0.5:
            segs.append((a, b))
    out = []
    for r in trace:
        p = (r["fix"].latitude, r["fix"].longitude)
        best = min(segs, key=lambda s: j1._seg_dist(p, *s))
        if j1._seg_dist(p, *best) > 50:  # the engine dropped this part of the trace
            out.append("WITHHELD")
            continue
        a, b = best
        piece = _road_piece(clip, _closest_point(p, a, b), _bearing(a, b))
        if piece is None:
            out.append("UNREADABLE")
        else:
            truth = set(map(tuple, r["truth"]))
            out.append("OK" if piece in truth else "SAME_ROAD_NEXT_PIECE"
                       if _ways_of(clip, piece) & set().union(*(_ways_of(clip, x) for x in truth)) else "WRONG")
    return out


def _ways_of(clip, piece) -> set[str]:
    """Car ways that have this road piece (two neighbouring nodes) in either direction."""
    x, y = piece
    return {w for w in clip.node_ways.get(x, ()) if w in clip.ways
            and any({u, v} == {x, y} for u, v in zip(clip.ways[w][0], clip.ways[w][0][1:]))}


def _closest_point(p, a, b):
    """The point of segment a-b nearest p (local flat approximation)."""
    ax, ay = _xy(a, p)
    bx, by = _xy(b, p)
    dx, dy = bx - ax, by - ay
    f = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
    return _ll((ax + f * dx, ay + f * dy), p)


_PIECES: dict[int, list] = {}


def _road_piece(clip, point, heading: float):
    """Directed OSM road piece the point lies on (within LINE_SNAP_M), oriented by heading."""
    key = id(clip)
    if key not in _PIECES:
        pieces = []
        for w, (refs, tags) in clip.ways.items():
            if not clip.drivable(tags):
                continue
            for a, b in zip(refs, refs[1:]):
                if a in clip.coords and b in clip.coords:
                    pieces.append((a, b, clip.coords[a], clip.coords[b]))
        _PIECES.clear()
        _PIECES[key] = pieces
    best = None
    for a, b, pa, pb in _PIECES[key]:
        if abs(pa[0] - point[0]) > 0.002 or abs(pa[1] - point[1]) > 0.003:
            continue
        d = j1._seg_dist(point, pa, pb)
        if d <= LINE_SNAP_M and (best is None or d < best[0]):
            fwd = abs((_bearing(pa, pb) - heading + 180) % 360 - 180) <= 90
            best = (d, (a, b) if fwd else (b, a))
    return None if best is None else best[1]


# --------------------------------------------------------------------------- runs
def _provenance(name: str) -> dict:
    return {"schema": 1, "run": name, "revision": t1._revision(), "prepared_sha256": t1.sha256_file(PREPARED),
            "rund_prepared_sha256": t1.sha256_file(rd.PREPARED), "runner_sha256": t1.sha256_file(Path(__file__)),
            "engines_sha256": t1.sha256_file(Path(xe.__file__))}


def _reroute_geom(plan: dict, geom: dict) -> dict:
    wt = plan["wrong_turn"]
    return {"origin": wt["reroute_origin"], "origin_segment": wt["reroute_origin_segment"],
            "destination": geom["destination"], "destination_segment": geom["destination_segment"]}


def run(engine: str, only: set[str] | None = None) -> None:
    prepared = json.loads(PREPARED.read_text())
    rdp = {j["id"]: j["journey"] for j in json.loads(rd.PREPARED.read_text())["closure"]}
    records = {r["id"]: r for r in rd._testable()}
    out_path = WORK / f"run-{engine}.json"
    WORK.mkdir(parents=True, exist_ok=True)
    results: dict = {"_provenance": _provenance(engine)}
    for plan in prepared["journeys"]:
        if plan["status"] != "TESTABLE" or (only and plan["id"] not in only):
            continue
        geom = rdp[plan["id"]]
        raw = j1.case_clip(records[plan["id"]])
        clip = a1.AccessClip(raw)
        rgeom = _reroute_geom(plan, geom)
        entry: dict = {}
        traces = {s: open_trace(clip, geom, plan["drive_nodes"], plan["id"], s) for s in ("normal", "dropout")}
        entry["trace_sha256"] = {s: trace_sha(tr) for s, tr in traces.items()}
        try:
            if engine == "DMN":
                dmn = rd.DMNMap(raw)
                for label, g in (("route", geom), ("reroute_point", rgeom)):
                    _, nodes = dmn_route(dmn, g["origin_segment"], g["destination_segment"])
                    entry[label] = rd.judge(clip, g, nodes)
                if entry["route"].get("path") != plan["drive_nodes"]:
                    entry["drive_route_changed"] = True  # the frozen drive no longer equals DMN's route
                entry["drives"] = {s: drive(dmn, clip, geom, plan, s) for s in SCENARIOS}
                entry["drives_v2"] = {s: drive(dmn, clip, geom, plan, s, improved=True) for s in SCENARIOS}
                entry["memory_peak_mb"] = memory_peak(dmn, clip, geom, plan)
            else:
                folder = WORK / "cases" / plan["id"]
                rd.write_pbf(folder, raw)
                with xe.serve(engine, folder / "clip.osm.pbf", folder / engine.lower()):
                    for label, g in (("route", geom), ("reroute_point", rgeom)):
                        points, _, ms = xe.query(engine, g, t1.travel_headings(clip, g))
                        nodes = xe.engine_path(clip, g, points)[0] if points is not None else None
                        entry[label] = rd.judge(clip, g, nodes)
                    if engine in MATCHERS:
                        for s, tr in traces.items():
                            try:
                                entry[f"match_{s}"] = judge_line(clip, tr, match_line(engine, tr))
                            except Exception as exc:  # noqa: BLE001 - recorded, never hidden
                                # the engine matched nothing for this trace: every fix withheld, error kept
                                entry[f"match_{s}"] = ["WITHHELD"] * len(tr)
                                entry[f"match_{s}_error"] = f"{type(exc).__name__}: {exc}"[:300]
                shutil.rmtree(folder, ignore_errors=True)
        except xe.MapRejected as exc:
            entry["error"] = f"ENGINE_REJECTED_MAP: {exc}"[:300]
        except Exception as exc:  # noqa: BLE001
            entry["error"] = f"{type(exc).__name__}: {exc}"[:300]
        results[plan["id"]] = entry
        out_path.write_text(json.dumps(results, indent=1, sort_keys=True, default=str))
        subprocess.run(["rm", "-rf", str(j1.WORK / "cases" / plan["id"])], check=False)
        print(plan["id"], entry.get("route", {}).get("route"), entry.get("reroute_point", {}).get("route"),
              entry.get("error", ""), flush=True)
    if engine == "OsmAnd":
        results["_osmand_build_sha256"] = xe.osmand_build()
        out_path.write_text(json.dumps(results, indent=1, sort_keys=True, default=str))


# --------------------------------------------------------------------------- score
def _load(engine: str) -> dict | None:
    path = WORK / f"run-{engine}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if data.get("_provenance") != _provenance(engine):
        raise RuntimeError(f"Run C {engine}: stale/unprovenanced result")
    return data


def _share(c: Counter) -> dict:
    n = sum(c.values())
    return {"fixes": n, **{k: c.get(k, 0) for k in ("OK", "SAME_ROAD_NEXT_PIECE", "WRONG", "WITHHELD", "UNREADABLE")},
            "ok_pct": round(100 * c.get("OK", 0) / n, 1) if n else None,
            "wrong_pct": round(100 * c.get("WRONG", 0) / n, 2) if n else None}


def cue_verdicts(drive_log: dict) -> Counter:
    """13: per turn driven on its route, the first cue's true distance before the turn."""
    first = {}
    for c in drive_log["cues"]:
        first.setdefault((c["rev"], c["node"]), c)
    out = Counter()
    for c in first.values():
        d = c["true_distance_m"]
        if c["car_off_route"]:
            out["WRONG_CUE_OFF_ROUTE"] += 1
        elif d is None:
            out["LATE_AFTER_TURN"] += 1
        elif d < CUE_WINDOW[0] or c["phase"] == "NOW":
            out["LATE"] += 1
        elif d > max(CUE_WINDOW[1], CUE_WINDOW[2] * SPEED):
            out["EARLY"] += 1
        else:
            out["ON_TIME"] += 1
    return out


def score() -> None:
    prepared = json.loads(PREPARED.read_text())
    ids = [p["id"] for p in prepared["journeys"] if p["status"] == "TESTABLE"]
    runs = {e: r for e in ENGINES if (r := _load(e)) is not None}
    if "DMN" in runs:  # DMN with the same-road-pieces matcher (owner-approved improvement)
        runs["DMN v2"] = {i: {**v, "drives": v["drives_v2"]} for i, v in runs["DMN"].items()
                          if isinstance(v, dict) and "drives_v2" in v}
        runs["DMN v2"]["_provenance"] = runs["DMN"]["_provenance"]
    summary = {"contract": CONTRACT, "revision": t1._revision(), "prepared_sha256": t1.sha256_file(PREPARED),
               "journeys": len(ids), "truth": "map-derived from the hashed OSM snapshot; simulated GPS only",
               "categories": {}}
    cats = summary["categories"]
    # every engine must have been given the same traces
    shas = {e: {i: r.get(i, {}).get("trace_sha256") for i in ids} for e, r in runs.items()}
    summary["same_traces_for_every_engine"] = len({json.dumps(v, sort_keys=True) for v in shas.values()}) == 1
    # 6 and 12 (reference form): route validity and length vs the shortest valid answer
    for cat, label in (("6_route_quality", "route"), ("12_reroute_from_point", "reroute_point")):
        shortest = {}
        for i in ids:
            ls = [r[i][label]["length_m"] for r in runs.values() if r.get(i, {}).get(label, {}).get("route") == "VALID"]
            shortest[i] = min(ls) if ls else None
        table = {}
        for e, r in runs.items():
            if e == "DMN v2":  # routing is unchanged by the matcher option
                continue
            verdicts = Counter(r.get(i, {}).get(label, {}).get("route", "ERROR") for i in ids)
            ratios = [r[i][label]["length_m"] / shortest[i] for i in ids
                      if r.get(i, {}).get(label, {}).get("route") == "VALID" and shortest[i]]
            table[e] = {"verdicts": dict(verdicts), "valid": verdicts.get("VALID", 0),
                        "median_length_vs_shortest": round(statistics.median(ratios), 3) if ratios else None,
                        "over_1_2x": [i for i in ids if r.get(i, {}).get(label, {}).get("route") == "VALID"
                                      and shortest[i] and r[i][label]["length_m"] > 1.2 * shortest[i]]}
        cats[cat] = table
    dmn = runs.get("DMN")
    # 3 and 4: GPS matching
    for cat, scen in (("3_gps_matching", "normal"), ("4_gps_loss_recovery", "dropout")):
        table = {}
        for e, r in runs.items():
            c, after, errors = Counter(), Counter(), 0
            for i in ids:
                entry = r.get(i, {})
                if e.startswith("DMN"):
                    fixes = entry.get("drives", {}).get(scen, {}).get("fixes", [])
                    verdicts = [f["match"] for f in fixes]
                    gaps = [f["after_gap_s"] for f in fixes]
                elif e in MATCHERS:
                    verdicts = entry.get(f"match_{scen}")
                    if not isinstance(verdicts, list):
                        continue
                    errors += f"match_{scen}_error" in entry
                    gaps = [None] * len(verdicts)
                else:
                    continue
                c.update(verdicts)
                if scen == "dropout":
                    if not e.startswith("DMN"):  # batch matchers: same trace (checked by hash), aligned by fix order
                        gaps = [f["after_gap_s"] for f in dmn[i]["drives"]["dropout"]["fixes"]] if dmn else gaps
                    after.update(v for v, g in zip(verdicts, gaps) if g is not None and g <= 30)
            if e.startswith("DMN") or e in MATCHERS:
                table[e] = {"scope": "live, fix by fix" if e.startswith("DMN") else "batch, whole trace",
                            "all_fixes": _share(c), "errors": errors}
                if scen == "dropout":
                    table[e]["first_30_s_after_gap"] = _share(after)
        for variant in [v for v in ("DMN", "DMN v2") if v in runs and scen == "dropout"]:
            dmn = runs[variant]
            rec = []
            for i in ids:
                fx = dmn[i]["drives"]["dropout"]["fixes"]
                ok = next((f["after_gap_s"] for f in fx if f["after_gap_s"] and f["match"] == "OK"), None)
                rec.append(ok)
            got = [x for x in rec if x is not None]
            table[variant]["seconds_to_first_correct_match_after_gap"] = {
                "median": statistics.median(got) if got else None, "max": max(got) if got else None,
                "never": rec.count(None)}
            jumps = Counter(f["match"] for i in ids for f in dmn[i]["drives"]["dropout"]["fixes"] if f["extra"])
            table[variant]["jump_and_weak_fixes"] = dict(jumps)
        cats[cat] = table
    dmn_variants = {v: runs[v] for v in ("DMN", "DMN v2") if v in runs}
    for variant, dmn in dmn_variants.items():  # before / after the matcher improvement
        # 12 closed loop
        wt = [dmn[i]["drives"]["wrong_turn"] for i in ids]
        delays = [d["reroutes"][0]["t"] - d["left_route_at"] for d in wt
                  if d["reroutes"] and d["left_route_at"] is not None]
        false = {s: sum(len(dmn[i]["drives"][s]["reroutes"]) for i in ids) for s in ("normal", "dropout")}
        cats.setdefault("12_rerouting_dmn_closed_loop", {})[variant] = {
            "detected": len(delays), "of": len(ids),
            "detection_delay_s": {"median": statistics.median(delays) if delays else None,
                                  "max": max(delays) if delays else None},
            "new_route_valid": sum(1 for d in wt for r in d["reroutes"][:1] if r.get("route") == "VALID"),
            "lost": [i for i, d in zip(ids, wt) if d["lost"]],
            "reached_destination": sum(1 for d in wt if d["reached_destination_at"] is not None),
            "false_reroutes": false}
        # 13 cue timing
        cues = Counter()
        missed = 0
        for i in ids:
            for s in SCENARIOS:
                d = dmn[i]["drives"][s]
                cues += cue_verdicts(d)
                if s == "normal":
                    cued = {c["node"] for c in d["cues"] if c["rev"] == 1}
                    missed += sum(1 for n in d["maneuver_nodes_first_route"] if n not in cued)
        cats.setdefault("13_instruction_timing_dmn", {})[variant] = {"first_cue_per_turn": dict(cues),
                                             "normal_drives_turns_never_cued": missed,
                                             "rule": prepared["rules"]["cue"]}
        # 16 arrival
        arr = Counter()
        for i in ids:
            for s in SCENARIOS:
                d = dmn[i]["drives"][s]
                a = d["arrival"]
                if a is None:
                    arr["NOT_DECLARED" if d["reached_destination_at"] is not None else "NOT_REACHED"] += 1
                elif a["true_remaining_m"] > ARRIVAL_OK_M:
                    arr["EARLY"] += 1
                elif a["to_destination_m"] <= ARRIVAL_OK_M:
                    arr["CORRECT"] += 1
                else:
                    arr["WRONG_PLACE"] += 1
        delay = [d["arrival"]["t"] - d["reached_destination_at"] for i in ids for s in SCENARIOS
                 for d in [dmn[i]["drives"][s]] if d["arrival"] and d["reached_destination_at"] is not None]
        cats.setdefault("16_arrival_dmn", {})[variant] = {"verdicts": dict(arr), "seconds_after_reaching": {
            "median": statistics.median(delay) if delay else None, "max": max(delay) if delay else None}}
        # 20 whole journey
        passed, fails = 0, defaultdict(list)
        for i in ids:
            for s in SCENARIOS:
                d = dmn[i]["drives"][s]
                why = []
                if d["arrival"] is None or d["arrival"]["to_destination_m"] > ARRIVAL_OK_M:
                    why.append("no_correct_arrival")
                if s != "wrong_turn" and d["reroutes"]:
                    why.append("false_reroute")
                if s == "wrong_turn" and d["lost"]:
                    why.append("lost")
                if any(f["match"] == "WRONG" for f in d["fixes"]):
                    why.append("confidently_wrong_position")
                v = cue_verdicts(d)
                if v.get("WRONG_CUE_OFF_ROUTE") or v.get("LATE_AFTER_TURN"):
                    why.append("wrong_or_missed_cue")
                if why:
                    for w in why:
                        fails[w].append(f"{i}:{s}")
                else:
                    passed += 1
        cats.setdefault("20_whole_journey_dmn", {})[variant] = {"passed": passed, "drives": len(ids) * len(SCENARIOS),
                                        "failures": {k: v for k, v in fails.items()}}
        # 19 memory and time
        cats.setdefault("19_memory_time_dmn", {})[variant] = {
            "peak_traced_mb": rd._ms([dmn[i]["memory_peak_mb"] for i in ids]),
            "ms_per_fix_median_of_drives": rd._ms([dmn[i]["drives"][s]["ms_per_fix"]["median"]
                                                   for i in ids for s in SCENARIOS]),
            "ms_per_fix_p95_of_drives": rd._ms([dmn[i]["drives"][s]["ms_per_fix"]["p95"]
                                                for i in ids for s in SCENARIOS])}
        summary["drive_route_changed_since_freeze"] = [i for i in ids if dmn[i].get("drive_route_changed")]
    summary["errors"] = {e: {i: r[i]["error"] for i in ids if "error" in r.get(i, {})} for e, r in runs.items()
                         if e != "DMN v2"}
    (WORK / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))


def brief() -> int:
    s = json.loads((WORK / "summary.json").read_text())
    c = s["categories"]
    lines = [f"{s['contract']} @ {s['revision'][:12]}: {s['journeys']} journeys x 3 drives; same traces for "
             f"every engine: {s['same_traces_for_every_engine']} (each category separate; no total)"]
    for cat in ("3_gps_matching", "4_gps_loss_recovery"):
        lines.append(f"{cat} ok% / wrong% of fixes: " + "; ".join(
            f"{e} {v['all_fixes']['ok_pct']} / {v['all_fixes']['wrong_pct']} ({v['scope']})" for e, v in c[cat].items()))
    for cat in ("6_route_quality", "12_reroute_from_point"):
        lines.append(f"{cat} valid, median vs shortest: " + "; ".join(
            f"{e} {v['valid']}, {v['median_length_vs_shortest']}" for e, v in c[cat].items()))
    for cat in ("12_rerouting_dmn_closed_loop", "13_instruction_timing_dmn", "16_arrival_dmn",
                "20_whole_journey_dmn", "19_memory_time_dmn"):
        for variant, v in c.get(cat, {}).items():
            lines.append(f"{cat} [{variant}]: {json.dumps(v, sort_keys=True)[:300]}")
    errs = {e: len(v) for e, v in s["errors"].items() if v}
    lines.append(f"errors: {errs or 'none'}")
    bad = []
    if "20_whole_journey_dmn" in c and c["3_gps_matching"].get("DMN", {}).get("all_fixes", {}).get("WRONG"):
        bad.append("DMN gave confidently wrong positions")
    lines.append("RESULT: " + ("; ".join(bad) if bad else "OK"))
    print("\n".join(lines))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare")
    r = sub.add_parser("run")
    r.add_argument("--engine", choices=ENGINES, required=True)
    r.add_argument("--only", nargs="*")
    sub.add_parser("score")
    sub.add_parser("brief")
    args = parser.parse_args()
    if args.cmd == "prepare":
        prepare()
    elif args.cmd == "run":
        run(args.engine, set(args.only or ()) or None)
    elif args.cmd == "score":
        score()
    else:
        return brief()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
