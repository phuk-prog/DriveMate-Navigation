"""GRAND-TOUR-001: one long UK drive testing everything DMN should do, DMN + 6 reference engines.

Owner, 17 Oct 2026: every engine gets the same start and finish, on real UK roads for many
miles: city centre (one-way streets, junctions, lights), motorway, roundabouts and country
roads. Early in the drive the car makes a few wrong turns; later traffic builds up ahead
and adds about 30 minutes; the GPS is a normal average phone signal with drop-outs. Each
category is scored and ranked separately (no combined score).

Map: the pinned Greater Manchester OSM snapshot, cut to one box (car roads, turn rules and
barriers; nothing left out), frozen by SHA-256.
Drive: Manchester city centre (one-way street) -> moor lane by Piethorne Reservoir, Rochdale.

Every engine (same machine, one after another):
  main route on the open map; routes from the three wrong-turn points; the route from the
  traffic decision point on the jam map (the jammed motorway ways carry a crawl maxspeed in
  the map every engine gets: the only traffic input every engine can read); warm query times;
  roundabout exit numbers on its own route; OSRM, Valhalla and GraphHopper also match the GPS
  trace (batch).
DMN also drives the whole journey live, fix by fix (closed loop): GPS matching, wrong-turn
detection and rerouting, the jam reported as live traffic (time penalties), announcements,
arrival, time per fix.

Time is judged with ONE neutral UK speed table for every engine (NEUTRAL_KPH, capped by the
road's maxspeed), never an engine's own estimate. Truth is map-derived, not UK road law.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import random
import resource
import shutil
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

from benchmarks import access001_route as a1
from benchmarks import extra_engines as xe
from benchmarks import journey001 as j1
from benchmarks import run_c as rc
from benchmarks import run_d as rd
from benchmarks import turn001_restrictions as t1

ROOT = t1.ROOT
WORK = ROOT / "results" / "grandtour"
PREPARED = ROOT / "config" / "grandtour-prepared.json"
CONTRACT = "GRAND-TOUR-001 v1"
ENGINES = ("DMN", *xe.ENGINES)
BBOX = "-2.30,53.46,-1.98,53.66"
CAR_HIGHWAYS = ("motorway,motorway_link,trunk,trunk_link,primary,primary_link,secondary,secondary_link,"
                "tertiary,tertiary_link,unclassified,residential,living_street,service,road,busway,"
                "bus_guideway,pedestrian,track")
# Piccadilly Gardens area (one-way street) -> moor lane by Piethorne Reservoir above Newhey (Rochdale):
# DMN's route then runs city streets, A-road, 6.5 km of M62, main roads and a country lane.
START_NEAR, END_NEAR = (53.4808, -2.2370), (53.6150, -2.0540)
NEUTRAL_KPH = {"motorway": 96, "motorway_link": 64, "trunk": 72, "trunk_link": 48, "primary": 56,
               "primary_link": 40, "secondary": 48, "secondary_link": 40, "tertiary": 48, "tertiary_link": 40,
               "unclassified": 48, "residential": 32, "living_street": 16, "service": 16, "track": 16, "road": 32}
WRONG_TURNS, WRONG_FROM, WRONG_TO, WRONG_SPACING_M = 3, 0.04, 0.35, 800.0
DEVIATION_M, LOST_M, REROUTE_POINT_M = 200.0, 700.0, 100.0
JAM_FROM, JAM_MIN_M, JAM_ADDED_S, JAM_WARNING_M = 0.40, 4000.0, 1800.0, 3000.0
SIGMA_M, SIGMA_DEG, ACCURACY_M = 4.0, 5.0, 6.0
DROPOUTS = ((0.12, 15), (0.60, 30), (0.88, 10))  # (share of the drive, seconds without fixes)
QUERY_REPEATS = 5
MAX_DRIVE_S = 4 * 3600


def _h(label: str) -> str:
    return hashlib.sha256(f"GRAND-TOUR-001:{label}".encode()).hexdigest()


# --------------------------------------------------------------------------- map
def build_clip(folder: Path) -> bytes:
    """The frozen map box (car roads, turn rules, barriers): XML bytes; also writes a PBF."""
    folder.mkdir(parents=True, exist_ok=True)
    roads = t1.WORK / "roads.osm.pbf"
    if not roads.exists():
        a1.use("access001")
        roads = a1.roads_source()
    steps = [["osmium", "extract", "--overwrite", "--strategy", "complete_ways", f"--bbox={BBOX}", str(roads),
              "-o", str(folder / "box.osm.pbf")],
             ["osmium", "tags-filter", "--overwrite", str(folder / "box.osm.pbf"), f"w/highway={CAR_HIGHWAYS}",
              "r/type=restriction", "n/barrier", "-o", str(folder / "clip.osm.pbf")],
             ["osmium", "cat", "--overwrite", str(folder / "clip.osm.pbf"), "-o", str(folder / "clip.osm"),
              "-f", "osm,add_metadata=false"]]
    for step in steps:
        subprocess.run(step, check=True, capture_output=True)
    return (folder / "clip.osm").read_bytes()


def neutral_kph(tags: dict) -> float:
    base = NEUTRAL_KPH.get(tags.get("highway", ""), 32)
    value = (tags.get("maxspeed") or "").strip().lower()
    try:
        cap = float(value.split()[0]) * (1.609344 if "mph" in value else 1.0) if value else None
    except ValueError:
        cap = None
    return min(base, cap) if cap and cap > 0 else base


class Times:
    """Neutral travel times per directed road piece, with optional jam pieces."""

    def __init__(self, clip, jam_kph: float | None = None, jam_ways: set[str] = frozenset()):
        self.clip, self.jam_kph, self.jam_ways = clip, jam_kph, set(jam_ways)
        self.piece_way = {}
        for w, (refs, tags) in clip.ways.items():
            if clip.drivable(tags):
                for a, b in zip(refs, refs[1:]):
                    self.piece_way.setdefault((a, b), w)
                    self.piece_way.setdefault((b, a), w)

    def seconds(self, a: str, b: str) -> float:
        w = self.piece_way.get((a, b))
        kph = neutral_kph(self.clip.ways[w][1]) if w else 32
        if w in self.jam_ways and self.jam_kph:
            kph = min(kph, self.jam_kph)
        return t1.metres(self.clip.coords[a], self.clip.coords[b]) / (kph / 3.6)

    def route(self, nodes) -> float | None:
        if not nodes:
            return None
        return round(sum(self.seconds(a, b) for a, b in zip(nodes, nodes[1:])), 1)

    def best(self, graph, start: str, goal: str) -> float | None:
        """Lower bound: neutral-time shortest path on the car graph (turn bans ignored)."""
        best, todo = {start: 0.0}, [(0.0, start)]
        while todo:
            d, n = heapq.heappop(todo)
            if n == goal:
                return round(d, 1)
            if d > best[n]:
                continue
            for m, _, _ in graph.get(n, ()):
                c = d + self.seconds(n, m)
                if c < best.get(m, math.inf):
                    best[m] = c
                    heapq.heappush(todo, (c, m))
        return None


def jam_map(raw: bytes, ways: list[str], kph: int) -> bytes:
    """The same map with the jammed ways at a crawl: maxspeed set to the jam speed (km/h)."""
    text = raw.decode()
    import re
    for way in ways:
        m = re.search(rf'<way id="{way}"[^>]*>(.*?)</way>', text, re.S)
        body = re.sub(r'\s*<tag k="maxspeed" v="[^"]*"/>', "", m.group(1))
        body = body.rstrip() + f'\n    <tag k="maxspeed" v="{kph}"/>\n  '
        text = text[:m.start(1)] + body + text[m.end(1):]
    return text.encode()


# --------------------------------------------------------------------------- prepare (frozen)
def nearest_segment(clip, point, highways: set[str], oneway: bool | None):
    best = None
    for w, (refs, tags) in clip.ways.items():
        if tags.get("highway") not in highways or not clip.drivable(tags):
            continue
        if oneway is not None and (clip.oneway(w) != 0) != oneway:
            continue
        if any(k in tags for k in ("access", "motor_vehicle", "motorcar", "vehicle")):
            continue
        for a, b in zip(refs, refs[1:]):
            if a not in clip.coords or b not in clip.coords:
                continue
            seg = t1.metres(clip.coords[a], clip.coords[b])
            if seg < 15:
                continue
            for x, y in ((a, b), (b, a)):
                if clip.can_travel(w, x, y):
                    mid = ((clip.coords[x][0] + clip.coords[y][0]) / 2, (clip.coords[x][1] + clip.coords[y][1]) / 2)
                    d = t1.metres(mid, point)
                    if best is None or d < best[0]:
                        best = (d, [x, y], mid)
    return best


def deviation_at(clip, nodes: list[str], i: int, avoid: set[str], salt: str):
    """A legal wrong turn at node i onto a public road continuing >= DEVIATION_M, or None."""
    p, n, q = nodes[i - 1], nodes[i], nodes[i + 1]
    firsts = sorted({r for w in clip.drivable_ways(n) if rc._public(clip, w) for r in rc._neighbours(clip, w, n)
                     if r not in (p, q) and r not in avoid and r in clip.coords and clip.can_travel(w, n, r)
                     and t1.audit_route(clip, [p, n, r])["route_legal"] == "LEGAL"},
                    key=lambda r: _h(f"{salt}:{n}:{r}"))
    for r in firsts:
        walk = [n, *rc.straightest(clip, n, r, avoid, DEVIATION_M)]
        if sum(t1.metres(clip.coords[a], clip.coords[b]) for a, b in zip(walk, walk[1:])) >= DEVIATION_M:
            return walk
    return None


def prepare() -> None:
    folder = WORK / "map"
    raw = build_clip(folder)
    clip = a1.AccessClip(raw)
    start = nearest_segment(clip, START_NEAR, {"tertiary", "secondary", "unclassified", "residential", "primary"},
                            oneway=True)
    end = nearest_segment(clip, END_NEAR, {"residential", "unclassified", "tertiary"}, oneway=False)
    geom = {"origin": [round(start[2][0], 7), round(start[2][1], 7)], "origin_segment": start[1],
            "destination": [round(end[2][0], 7), round(end[2][1], 7)], "destination_segment": end[1]}
    dmn = rd.DMNMap(raw)
    route, nodes = rc.dmn_route(dmn, geom["origin_segment"], geom["destination_segment"])
    judged = rd.judge(clip, geom, nodes)
    if judged["route"] != "VALID":
        raise SystemExit(f"DMN drive route not valid: {judged['route']}")
    cum = [0.0]
    for a, b in zip(nodes, nodes[1:]):
        cum.append(cum[-1] + t1.metres(clip.coords[a], clip.coords[b]))
    times = Times(clip)
    # wrong turns
    wrong, last = [], -1e9
    for i in range(1, len(nodes) - 1):
        if len(wrong) == WRONG_TURNS:
            break
        if not WRONG_FROM * cum[-1] <= cum[i] <= WRONG_TO * cum[-1] or cum[i] - last < WRONG_SPACING_M:
            continue
        walk = deviation_at(clip, nodes, i, set(nodes), "prepare")
        if walk is None:
            continue
        acc, point = 0.0, None
        for a, b in zip(walk, walk[1:]):
            seg = t1.metres(clip.coords[a], clip.coords[b])
            if acc >= REROUTE_POINT_M and seg >= a1.MIN_SEGMENT_M:
                point = [a, b]
                break
            acc += seg
        if point is None:
            continue
        mid = ((clip.coords[point[0]][0] + clip.coords[point[1]][0]) / 2,
               (clip.coords[point[0]][1] + clip.coords[point[1]][1]) / 2)
        wrong.append({"index": i, "node": nodes[i], "at_m": round(cum[i], 1), "deviation": walk,
                      "reroute_origin_segment": point, "reroute_origin": [round(mid[0], 7), round(mid[1], 7)]})
        last = cum[i]
    # traffic jam: contiguous motorway ways on the route after JAM_FROM of the way
    jam_ways, jam_len, jam_start = [], 0.0, None
    for k, (a, b) in enumerate(zip(nodes, nodes[1:])):
        if cum[k] < JAM_FROM * cum[-1]:
            continue
        w = times.piece_way.get((a, b))
        hw = clip.ways[w][1].get("highway") if w else None
        if hw == "motorway":
            if jam_start is None:
                jam_start = k
            if w not in jam_ways:
                jam_ways.append(w)
            jam_len = cum[k + 1] - cum[jam_start]
        elif jam_start is not None:
            if jam_len >= JAM_MIN_M:
                break
            jam_ways, jam_len, jam_start = [], 0.0, None
    if jam_start is None or jam_len < JAM_MIN_M:
        raise SystemExit("no motorway stretch long enough for the jam on the drive route")
    full = sum(t1.metres(clip.coords[a], clip.coords[b]) for w in jam_ways
               for a, b in zip(clip.ways[w][0], clip.ways[w][0][1:]) if a in clip.coords and b in clip.coords)
    # added time over the whole jammed ways ~ JAM_ADDED_S: v = L / (added + L / v0)
    v0 = NEUTRAL_KPH["motorway"] / 3.6
    jam_kph = max(1, int(full / (JAM_ADDED_S + full / v0) * 3.6))
    decision = next(k for k in range(jam_start, -1, -1) if cum[jam_start] - cum[k] >= JAM_WARNING_M)
    dec_seg = [nodes[decision], nodes[decision + 1]]
    dmid = ((clip.coords[dec_seg[0]][0] + clip.coords[dec_seg[1]][0]) / 2,
            (clip.coords[dec_seg[0]][1] + clip.coords[dec_seg[1]][1]) / 2)
    jam_raw = jam_map(raw, jam_ways, jam_kph)
    mix = Counter()
    for a, b in zip(nodes, nodes[1:]):
        w = times.piece_way.get((a, b))
        mix[clip.ways[w][1].get("highway") if w else "?"] += t1.metres(clip.coords[a], clip.coords[b])
    rings = sum(1 for a, b in zip(nodes, nodes[1:]) for w in [times.piece_way.get((a, b))]
                if w and clip.ways[w][1].get("junction") in ("roundabout", "circular"))
    oneway_m = sum(t1.metres(clip.coords[a], clip.coords[b]) for a, b in zip(nodes, nodes[1:])
                   for w in [times.piece_way.get((a, b))] if w and clip.oneway(w) != 0)
    out = {"contract": CONTRACT, "frozen_before_reference_runs": True, "bbox": BBOX,
           "clip_sha256": hashlib.sha256(raw).hexdigest(), "jam_clip_sha256": hashlib.sha256(jam_raw).hexdigest(),
           "source_sha256": t1.sha256_file(t1.WORK / "gm.osm.pbf"),
           "geometry": geom, "drive_nodes": nodes, "drive_m": round(cum[-1], 1),
           "drive_neutral_s": times.route(nodes), "dmn_estimated_s": round(route.estimated_seconds, 1),
           "road_mix_km": {k: round(v / 1000, 2) for k, v in sorted(mix.items(), key=lambda x: -x[1])},
           "roundabout_pieces": rings, "one_way_km": round(oneway_m / 1000, 2),
           "maneuvers": len(rc.maneuvers(clip, nodes)), "wrong_turns": wrong,
           "jam": {"ways": jam_ways, "kph": jam_kph, "route_m": round(jam_len, 1), "ways_m": round(full, 1),
                   "start_index": jam_start, "decision_segment": dec_seg,
                   "decision_point": [round(dmid[0], 7), round(dmid[1], 7)]},
           "rules": {"neutral_kph": NEUTRAL_KPH, "gps": f"1 fix/s, sigma {SIGMA_M} m / {SIGMA_DEG} deg, "
                                                        f"accuracy {ACCURACY_M} m, drop-outs {DROPOUTS}",
                     "wrong_turns": f"{WRONG_TURNS} public-road wrong turns between {WRONG_FROM:.0%} and "
                                    f"{WRONG_TO:.0%} of the drive, >= {WRONG_SPACING_M:.0f} m apart",
                     "jam": f"motorway ways from {JAM_FROM:.0%} of the drive, >= {JAM_MIN_M:.0f} m, crawl speed "
                            f"so the jammed ways take about {JAM_ADDED_S / 60:.0f} min longer; reported "
                            f"{JAM_WARNING_M:.0f} m before it"}}
    text = json.dumps(out, indent=1, sort_keys=True)
    if PREPARED.exists() and PREPARED.read_text() != text:
        raise SystemExit("Prepared GRAND-TOUR-001 differs from the frozen config/grandtour-prepared.json")
    PREPARED.write_text(text)
    print(json.dumps({k: out[k] for k in ("drive_m", "drive_neutral_s", "road_mix_km", "roundabout_pieces",
                                          "one_way_km", "maneuvers")}, indent=1))
    print("wrong turns at", [w["at_m"] for w in wrong], "jam", out["jam"]["kph"], "km/h over", out["jam"]["ways_m"])


def load_maps(prepared: dict) -> tuple[bytes, bytes]:
    raw = build_clip(WORK / "map")
    if hashlib.sha256(raw).hexdigest() != prepared["clip_sha256"]:
        raise RuntimeError("map box differs from the frozen hash")
    jam_raw = jam_map(raw, prepared["jam"]["ways"], prepared["jam"]["kph"])
    if hashlib.sha256(jam_raw).hexdigest() != prepared["jam_clip_sha256"]:
        raise RuntimeError("jam map differs from the frozen hash")
    return raw, jam_raw


def geoms(prepared: dict) -> dict:
    g = prepared["geometry"]
    out = {"main": g}
    for k, w in enumerate(prepared["wrong_turns"], 1):
        out[f"wrong_turn_{k}"] = {**g, "origin": w["reroute_origin"], "origin_segment": w["reroute_origin_segment"]}
    jam = prepared["jam"]
    out["traffic"] = {**g, "origin": jam["decision_point"], "origin_segment": jam["decision_segment"]}
    return out


# --------------------------------------------------------------------------- the car
class TourCar(rc.Car):
    """run C's car with neutral road speeds, the jam crawl and a slow final approach."""

    def __init__(self, clip, geom, nodes, times: Times, jam_on: list[bool]):
        self.times, self.jam_on = times, jam_on
        super().__init__(clip, geom, nodes)

    def speed(self) -> float:
        if self.length - self.dist <= rc.ARRIVE_ZONE_M:
            return rc.ARRIVE_SPEED
        k = self.piece()
        a, b = self.nodes[k], self.nodes[k + 1]
        w = self.times.piece_way.get((a, b))
        kph = neutral_kph(self.clip.ways[w][1]) if w else 32
        if self.jam_on[0] and w in self.times.jam_ways:
            kph = min(kph, self.times.jam_kph)
        return min(30.0, kph / 3.6 * 0.9)


def make_fix(rnd, pos, bearing, t_ms, *, moving=True, extra=None, speed=10.0):
    from gps.fix_quality import GPSFix
    if extra == "jump":
        side = math.radians(bearing + 90)
        lat, lon = rc._ll((60 * math.sin(side), 60 * math.cos(side)), pos)
        return GPSFix(t_ms, lat, lon, 8.0, speed, bearing)
    lat, lon = rc._ll((rnd.gauss(0, SIGMA_M), rnd.gauss(0, SIGMA_M)), pos)
    if not moving:
        return GPSFix(t_ms, lat, lon, ACCURACY_M, 0.0, None)
    acc = max(3.0, ACCURACY_M + rnd.gauss(0, 1.5))
    return GPSFix(t_ms, lat, lon, round(acc, 1), max(0.0, speed + rnd.gauss(0, 0.3)),
                  (bearing + rnd.gauss(0, SIGMA_DEG)) % 360)


def gaps_for(length_m: float, speed_guess: float = 14.0) -> list[tuple[int, int]]:
    """Drop-outs as (from second, to second): by share of the distance at a typical speed."""
    return [(int(share * length_m / speed_guess), int(share * length_m / speed_guess) + secs)
            for share, secs in DROPOUTS]


def open_trace(clip, geom, nodes, times) -> list[dict]:
    """The fixed trace along the frozen drive (no wrong turns, no jam): the same for every matcher."""
    car = TourCar(clip, geom, nodes, times, [False])
    rnd = random.Random(int(_h("trace")[:16], 16))
    gaps = gaps_for(car.length)
    out, t = [], 0
    while t < MAX_DRIVE_S:
        pos, brg, _ = car.where()
        stopped = car.dist >= car.length
        in_gap = any(a <= t <= b for a, b in gaps)
        extra = "jump" if t == gaps[0][1] + 1 else None
        fix = make_fix(rnd, pos, brg, t * 1000, moving=not stopped, extra=extra, speed=car.speed())
        if not in_gap:
            out.append({"t": t, "fix": fix, "truth": sorted(car.true_edges()), "extra": extra,
                        "after_gap_s": next((t - b for a, b in gaps if 0 < t - b <= 30), None)})
        if stopped:
            return out
        car.step()
        t += 1
    return out


# --------------------------------------------------------------------------- DMN live drive
def dmn_drive(dmn, clip, prepared: dict, times: Times) -> dict:
    """The whole journey, fix by fix, with wrong turns, the jam reported live and drop-outs."""
    from engine.arrival_controller import ArrivalController
    from engine.instruction_cues import instruction_phase, lead_seconds_for
    from engine.progress_estimator import ProgressEstimator
    from engine.rerouting_controller import ReroutingController
    from engine.routing import Route, shortest_route
    from gps.matcher import DirectedRoadMatcher
    from gps.temporal_matcher import TemporalRoadMatcher
    geom = prepared["geometry"]
    dest = tuple(geom["destination"])
    route, nodes = rc.dmn_route(dmn, geom["origin_segment"], geom["destination_segment"])
    jam_on = [False]
    car = TourCar(clip, geom, list(prepared["drive_nodes"]), times, jam_on)
    tm = TemporalRoadMatcher(DirectedRoadMatcher(dmn.graph, dmn.imported.coordinates), confirm_after_gap_ms=10000)
    tm.matcher.set_route(route.edge_ids)
    rer = ReroutingController(post_gap_ms=5000)
    rer.begin(route, now_ms=0)
    ac = ArrivalController()
    est = ProgressEstimator()
    plan = {}

    def install(new_route, new_nodes, now):
        pairs = list(zip(new_nodes, new_nodes[1:]))
        cum = [0.0]
        for a, b in pairs:
            cum.append(cum[-1] + t1.metres(clip.coords[a], clip.coords[b]))
        plan.update(route=new_route, nodes=new_nodes, pairs=pairs, cum=cum, progress=0,
                    mans=rc.maneuvers(clip, new_nodes), spoken={}, now=set(),
                    rev=ac.begin(dest, route_length_m=new_route.length_m, now_ms=now))
        tm.matcher.set_route(new_route.edge_ids)
        est.reset()

    install(route, nodes, 0)
    jam_edges = {e.edge_id for e in dmn.graph.edges.values() if e.edge_id.split(":")[1] in times.jam_ways}
    jam_penalty = {e: max(0.0, dmn.graph.edges[e].length_m / (prepared["jam"]["kph"] / 3.6)
                          - dmn.graph.edges[e].estimated_seconds) for e in jam_edges}
    jam_start_node = prepared["drive_nodes"][prepared["jam"]["start_index"]]
    rnd = random.Random(int(_h("dmn-drive")[:16], 16))
    gaps = gaps_for(car.length)
    log = {"fixes": [], "reroutes": [], "cues": [], "wrong_turns": [], "traffic": None, "arrival": None}
    pending_wrong = list(prepared["wrong_turns"])
    timings, t, stopped_n, reached = [], 0, 0, None
    along = 0.0
    while t < MAX_DRIVE_S:
        now = t * 1000
        # wrong turns: when the car has driven past the frozen distance, at the next junction ahead
        if pending_wrong and car.dist >= pending_wrong[0]["at_m"] - 50:
            k0 = car.piece() + 1
            for i in range(k0, min(len(car.nodes) - 1, k0 + 60)):
                walk = deviation_at(clip, car.nodes, i, set(car.nodes), f"drive:{len(log['wrong_turns'])}")
                if walk:
                    cont = rc.straightest(clip, walk[-2], walk[-1], set(car.nodes), LOST_M - DEVIATION_M)
                    car.nodes = car.nodes[:i] + walk + cont[1:]
                    car.end = clip.coords[car.nodes[-1]]
                    car._build()
                    log["wrong_turns"].append({"t": t, "node": car.nodes[i], "at_m": round(car.cum[i], 1),
                                               "left_at_index": i, "noticed_t": None})
                    break
            pending_wrong.pop(0)
        # traffic: reported live JAM_WARNING_M before the jam (if the car is heading into it)
        if log["traffic"] is None:
            d = car.distance_to_node(jam_start_node)
            if d is not None and d <= JAM_WARNING_M:
                jam_on[0] = True
                log["traffic"] = {"t": t, "reported_at_m_before": round(d, 1)}
        pos, brg, _ = car.where()
        truth = car.true_edges()
        stopped = car.dist >= car.length
        in_gap = any(a <= t <= b for a, b in gaps)
        extra = "jump" if t == gaps[0][1] + 1 else None
        fix = make_fix(rnd, pos, brg, now, moving=not stopped, extra=extra, speed=car.speed())
        if not in_gap:
            began = time.perf_counter()
            res = tm.update(fix, now_ms=now)
            matched = res.status == "MATCHED"
            edge = None
            on_route = None
            if matched:
                e = dmn.graph.edges[res.edge_id]
                edge = (e.source.removeprefix("osm:"), e.target.removeprefix("osm:"))
                idx = next((k for k in range(max(0, plan["progress"] - 2), len(plan["pairs"]))
                            if plan["pairs"][k] == edge), None)
                on_route = idx is not None
                if on_route:
                    plan["progress"] = idx
                    a, b = (clip.coords[n] for n in edge)
                    ax, ay = rc._xy(a, (fix.latitude, fix.longitude))
                    bx, by = rc._xy(b, (fix.latitude, fix.longitude))
                    dx, dy = bx - ax, by - ay
                    f = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
                    along = plan["cum"][idx] + f * (plan["cum"][idx + 1] - plan["cum"][idx])
                    est.confirm(timestamp_ms=now, along_m=along, speed_mps=fix.speed_mps or 0.0)
            # live traffic: once reported, re-plan with the jam's time penalties
            if log["traffic"] is not None and "decided" not in log["traffic"] and matched:
                start = dmn.graph.edges[res.edge_id]
                try:
                    alt = shortest_route(dmn.graph, start.target, dmn.by_pair[tuple(
                        f"osm:{n}" for n in geom["destination_segment"])].target, incoming_edge_id=start.edge_id,
                        destination_edge_id=dmn.by_pair[tuple(f"osm:{n}" for n in geom["destination_segment"])].edge_id,
                        endpoint_uncertain_access=True, time_penalties_s=jam_penalty)
                except Exception:  # noqa: BLE001
                    alt = None
                rest = [e for e in plan["route"].edge_ids[(plan["progress"] or 0) + 1:]]
                keep_s = sum(dmn.graph.edges[e].estimated_seconds + jam_penalty.get(e, 0) for e in rest)
                log["traffic"].update(decided=t, current_route_with_jam_s=round(keep_s, 1),
                                      alternative_s=round(alt.estimated_seconds, 1) if alt else None)
                if alt is not None and alt.estimated_seconds < keep_s - 60:
                    new_nodes = [edge[1]] + [dmn.graph.edges[e].target.removeprefix("osm:") for e in alt.edge_ids]
                    new_route = Route((start.edge_id, *alt.edge_ids), alt.length_m + start.length_m,
                                      alt.estimated_seconds + start.estimated_seconds)
                    rer.begin(new_route, now_ms=now)
                    install(new_route, [edge[0]] + new_nodes, now)
                    here = car.piece()
                    k = next((k for k in (here, here - 1, here + 1) if 0 <= k < len(car.nodes) - 1
                              and (car.nodes[k], car.nodes[k + 1]) == edge), None)
                    if k is not None:
                        car.replace_after(k + 1, plan["nodes"][1:], dest)
                    log["traffic"].update(switched=True, followed=k is not None,
                                          avoids_jam=not any(e in jam_edges for e in alt.edge_ids))
                else:
                    log["traffic"].update(switched=False)
            request = rer.observe(timestamp_ms=now, now_ms=now, reliable=matched, on_route=on_route)
            if request is not None:
                new_route, new_nodes = rc.dmn_route(dmn, list(edge), geom["destination_segment"])
                installed = rer.complete(request, new_route, now_ms=now)
                entry = {"t": t, "from": list(edge), "installed": bool(installed and new_route)}
                if installed and new_route:
                    install(new_route, new_nodes, now)
                    entry.update(rd.judge(clip, {"origin_segment": list(edge),
                                                 "destination_segment": geom["destination_segment"]}, new_nodes))
                    entry.pop("path", None)
                    here = car.piece()
                    k = next((k for k in (here, here - 1, here + 1) if 0 <= k < len(car.nodes) - 1
                              and (car.nodes[k], car.nodes[k + 1]) == edge and edge in truth), None)
                    if k is not None:
                        car.replace_after(k + 1, new_nodes[1:], dest)
                        entry["followed"] = True
                    for w in log["wrong_turns"]:
                        if w["noticed_t"] is None and w["t"] <= t:
                            w["noticed_t"] = t
                log["reroutes"].append(entry)
            # announcements
            cue_at = (along, 0) if on_route else (est.estimate(timestamp_ms=now) if on_route is None else None)
            if cue_at is not None:
                cue_along, age = cue_at
                nxt = next((m for m in plan["mans"] if m > plan["progress"]), None)
                if nxt is not None:
                    key = (plan["rev"], nxt)
                    speed = fix.speed_mps or 0.0
                    phase = instruction_phase(distance_m=max(0.0, plan["cum"][nxt] - cue_along), speed_mps=speed,
                                              reliable_fix=True, on_correct_route=True, maneuver_verified=True,
                                              observation_age_ms=int(age), spoken_before=key in plan["spoken"],
                                              lead_seconds=lead_seconds_for(speed), now_given=key in plan["now"])
                    if phase == "NOW":
                        plan["now"].add(key)
                    if phase in ("APPROACH", "NOW") and key not in plan["spoken"]:
                        plan["spoken"][key] = phase
                        true_d = car.distance_to_node(plan["nodes"][nxt])
                        log["cues"].append({"t": t, "phase": phase, "speed": round(speed, 1),
                                            "true_distance_m": None if true_d is None else round(true_d, 1),
                                            "car_off_route": not (truth & set(plan["pairs"]))})
            remaining = plan["cum"][-1] - along if on_route else 1e9
            verdict = ac.observe(context_revision=plan["rev"], timestamp_ms=now, now_ms=now,
                                 position=(fix.latitude, fix.longitude), accuracy_m=fix.horizontal_accuracy_m,
                                 reliable=matched, on_route=bool(on_route), remaining_m=max(0.0, remaining),
                                 speed_mps=fix.speed_mps)
            timings.append((time.perf_counter() - began) * 1000)
            if verdict == "ARRIVED" and log["arrival"] is None:
                log["arrival"] = {"t": t, "to_destination_m": round(t1.metres(pos, dest), 1),
                                  "true_remaining_m": round(max(0.0, car.length - car.dist), 1)}
            ok = "OK" if matched and edge in truth else "WRONG" if matched else "WITHHELD"
            if ok == "WRONG":
                way = res.edge_id.split(":")[1]
                if any(times.piece_way.get(p) == way for p in truth):
                    ok = "SAME_ROAD_NEXT_PIECE"
            log["fixes"].append({"t": t, "match": ok, "extra": extra,
                                 "after_gap_s": next((t - b for a, b in gaps if 0 < t - b <= 30), None)})
        if stopped:
            reached = reached if reached is not None else t
            stopped_n += 1
            if stopped_n > 6:
                break
        if t % 300 == 0:
            print(f"  DMN drive t={t}s at {car.dist / 1000:.1f} of {car.length / 1000:.1f} km", flush=True)
        car.step()
        t += 1
    log.update(reached_destination_at=reached if t1.metres(car.end, dest) <= 1.0 else None,
               lost=t1.metres(car.end, dest) > 1.0, drive_s=t,
               ms_per_fix=rd._ms(timings), fixes_processed=len(timings),
               neutral_s_driven=times.route(car.nodes), driven_m=round(car.length, 1))
    log["first_route_neutral_s"] = times.route(nodes)
    return log


# --------------------------------------------------------------------------- route-level answers
def roundabouts(clip, nodes, steps) -> dict:
    """Exit numbers on the engine's own route (single closed ring ways only) vs its steps."""
    truth = []
    i = 0
    while nodes and i < len(nodes) - 1:
        ways = [w for w in clip.node_ways.get(nodes[i], ()) if w in clip.ways
                and clip.ways[w][1].get("junction") in ("roundabout", "circular") and nodes[i + 1] in clip.ways[w][0]]
        if not ways:
            i += 1
            continue
        ring = ways[0]
        refs = clip.ways[ring][0]
        j = i
        while j + 1 < len(nodes) and nodes[j + 1] in refs:
            j += 1
        if refs[0] == refs[-1]:
            try:
                path, exits = j1.ring_exits(clip, ring, nodes[i])
                order = [e[0] for e in exits if e[0] != nodes[i]]
                truth.append(order.index(nodes[j]) + 1 if nodes[j] in order else None)
            except Exception:  # noqa: BLE001
                truth.append(None)
        else:
            truth.append(None)
        i = j + 1
    said = [s.get("exit") for s in steps if s.get("kind") == "roundabout"]
    judged = [(a, b) for a, b in zip(truth, said) if a is not None]
    return {"roundabouts": len(truth), "judged": len(judged), "correct": sum(a == b for a, b in judged),
            "said": len(said)}


def engine_answers(engine: str, raw: bytes, jam_raw: bytes, prepared: dict, clip, jam_clip, trace) -> dict:
    out = {}
    gs = geoms(prepared)
    folder = WORK / "engines" / engine.lower()
    for label, map_raw, mclip in (("open", raw, clip), ("jam", jam_raw, jam_clip)):
        rd.write_pbf(folder, map_raw)
        began = time.perf_counter()
        try:
            with xe.serve(engine, folder / "clip.osm.pbf", folder / engine.lower()):
                out[f"setup_{label}_s"] = round(time.perf_counter() - began, 1)
                todo = ["traffic"] if label == "jam" else [g for g in gs if g != "traffic"]
                for name in todo:
                    g = gs[name]
                    heads = t1.travel_headings(mclip, g)
                    ms = []
                    for k in range(QUERY_REPEATS if name == "main" else 1):
                        points, steps, q_ms = xe.query(engine, g, heads)
                        ms.append(round(q_ms, 1))
                    nodes = xe.engine_path(mclip, g, points)[0] if points is not None else None
                    judged = rd.judge(mclip, g, nodes)
                    judged["query_ms"] = ms
                    if name == "main" and points is not None:
                        judged["roundabouts"] = roundabouts(mclip, nodes, steps)
                    out[name] = judged
                if label == "open" and engine in rc.MATCHERS:
                    try:
                        out["match"] = rc.judge_line(clip, trace, rc.match_line(engine, trace))
                    except Exception as exc:  # noqa: BLE001
                        out["match"] = ["WITHHELD"] * len(trace)
                        out["match_error"] = f"{type(exc).__name__}: {exc}"[:300]
        except Exception as exc:  # noqa: BLE001 - recorded, never hidden
            out[f"error_{label}"] = f"{type(exc).__name__}: {exc}"[:300]
        shutil.rmtree(folder, ignore_errors=True)
    return out


def dmn_answers(raw: bytes, jam_raw: bytes, prepared: dict, clip, jam_clip, times, trace) -> dict:
    from engine.maneuvers import principal_maneuvers
    out = {}
    gs = geoms(prepared)
    began = time.perf_counter()
    dmn = rd.DMNMap(raw)
    out["setup_open_s"] = round(time.perf_counter() - began, 1)
    for name, g in gs.items():
        if name == "traffic":
            continue
        ms = []
        for k in range(QUERY_REPEATS if name == "main" else 1):
            t0 = time.perf_counter()
            _, nodes = rc.dmn_route(dmn, g["origin_segment"], g["destination_segment"])
            ms.append(round((time.perf_counter() - t0) * 1000, 1))
        judged = rd.judge(clip, g, nodes)
        judged["query_ms"] = ms
        if name == "main" and nodes:
            edges = [dmn.by_pair[(f"osm:{a}", f"osm:{b}")].edge_id for a, b in zip(nodes, nodes[1:])]
            ring_ways = {w for w, (_, tags) in clip.ways.items() if tags.get("junction") in ("roundabout", "circular")}
            rings = [e.edge_id for e in dmn.graph.edges.values() if e.edge_id.split(":")[1] in ring_ways]
            try:
                steps = [m for m in principal_maneuvers(dmn.graph, dmn.imported.coordinates, edges, rings)]
            except ValueError:
                steps = []
            judged["roundabouts"] = roundabouts(clip, nodes, steps)
        out[name] = judged
    began = time.perf_counter()
    jam_dmn = rd.DMNMap(jam_raw)
    out["setup_jam_s"] = round(time.perf_counter() - began, 1)
    g = gs["traffic"]
    t0 = time.perf_counter()
    _, nodes = rc.dmn_route(jam_dmn, g["origin_segment"], g["destination_segment"])
    out["traffic"] = {**rd.judge(jam_clip, g, nodes), "query_ms": [round((time.perf_counter() - t0) * 1000, 1)]}
    del jam_dmn
    out["drive"] = dmn_drive(dmn, clip, prepared, times)
    out["max_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    return out


# --------------------------------------------------------------------------- run, score
def run(engines: tuple[str, ...]) -> None:
    prepared = json.loads(PREPARED.read_text())
    raw, jam_raw = load_maps(prepared)
    clip, jam_clip = a1.AccessClip(raw), a1.AccessClip(jam_raw)
    times = Times(clip, prepared["jam"]["kph"], set(prepared["jam"]["ways"]))
    trace = open_trace(clip, prepared["geometry"], prepared["drive_nodes"], Times(clip))
    WORK.mkdir(parents=True, exist_ok=True)
    meta = {"revision": t1._revision(), "prepared_sha256": t1.sha256_file(PREPARED),
            "runner_sha256": t1.sha256_file(Path(__file__)), "trace_sha256": rc.trace_sha(trace),
            "machine": rd._machine()}
    for engine in engines:
        print("running", engine, flush=True)
        began = time.perf_counter()
        if engine == "DMN":
            entry = dmn_answers(raw, jam_raw, prepared, clip, jam_clip, times, trace)
        else:
            entry = engine_answers(engine, raw, jam_raw, prepared, clip, jam_clip, trace)
        entry["_meta"] = {**meta, "wall_s": round(time.perf_counter() - began, 1)}
        if engine == "OsmAnd":
            entry["_osmand_build_sha256"] = xe.osmand_build()
        (WORK / f"run-{engine}.json").write_text(json.dumps(entry, indent=1, sort_keys=True, default=str))
        print(engine, {k: v.get("route") if isinstance(v, dict) else None for k, v in entry.items()
                       if not k.startswith("_")}, flush=True)


def speed() -> None:
    """Section 7 on ONE machine: every engine, open map, 1 warm-up + QUERY_REPEATS timed main routes."""
    prepared = json.loads(PREPARED.read_text())
    raw, _ = load_maps(prepared)
    clip = a1.AccessClip(raw)
    g = prepared["geometry"]
    out = {"_meta": {"revision": t1._revision(), "machine": rd._machine(),
                     "runner_sha256": t1.sha256_file(Path(__file__))}}
    for engine in ENGINES:
        began = time.perf_counter()
        ms = []
        try:
            if engine == "DMN":
                dmn = rd.DMNMap(raw)
                setup = time.perf_counter() - began
                for k in range(QUERY_REPEATS + 1):
                    t0 = time.perf_counter()
                    rc.dmn_route(dmn, g["origin_segment"], g["destination_segment"])
                    if k:
                        ms.append(round((time.perf_counter() - t0) * 1000, 1))
                del dmn
            else:
                folder = WORK / "speed" / engine.lower()
                rd.write_pbf(folder, raw)
                with xe.serve(engine, folder / "clip.osm.pbf", folder / engine.lower()):
                    setup = time.perf_counter() - began
                    heads = t1.travel_headings(clip, g)
                    for k in range(QUERY_REPEATS + 1):
                        q_ms = xe.query(engine, g, heads)[2]
                        if k:
                            ms.append(round(q_ms, 1))
                shutil.rmtree(folder, ignore_errors=True)
            out[engine] = {"query_ms": ms, "setup_s": round(setup, 1),
                           "scope": "in-process call" if engine == "DMN" else "localhost HTTP"}
        except Exception as exc:  # noqa: BLE001
            out[engine] = {"error": f"{type(exc).__name__}: {exc}"[:300]}
        print("speed", engine, out[engine], flush=True)
    (WORK / "speed.json").write_text(json.dumps(out, indent=1, sort_keys=True))


def _rank(rows: dict, key, reverse=False) -> list[dict]:
    have = [(e, v) for e, v in rows.items() if key(v) is not None]
    return [{"engine": e, **v} for e, v in sorted(have, key=lambda x: key(x[1]), reverse=reverse)]


def score() -> None:
    prepared = json.loads(PREPARED.read_text())
    raw, jam_raw = load_maps(prepared)
    clip = a1.AccessClip(raw)
    neutral = Times(clip)
    jam_times = Times(clip, prepared["jam"]["kph"], set(prepared["jam"]["ways"]))
    graph = rd.directed_edges(clip)
    gs = geoms(prepared)
    runs = {e: json.loads((WORK / f"run-{e}.json").read_text()) for e in ENGINES if (WORK / f"run-{e}.json").exists()}
    trace_shas = {r["_meta"]["trace_sha256"] for r in runs.values()}
    s = {"contract": CONTRACT, "revision": next(iter(runs.values()))["_meta"]["revision"] if runs else None,
         "same_trace_for_every_engine": len(trace_shas) == 1, "drive": {k: prepared[k] for k in (
             "drive_m", "drive_neutral_s", "road_mix_km", "roundabout_pieces", "one_way_km", "maneuvers")},
         "jam": prepared["jam"] | {"ways": len(prepared["jam"]["ways"])},
         "errors": {e: {k: v for k, v in r.items() if k.startswith("error") or k == "match_error"}
                    for e, r in runs.items()}, "categories": {}}
    c = s["categories"]
    best = {name: (jam_times if name == "traffic" else neutral).best(
        graph, g["origin_segment"][1], g["destination_segment"][0]) for name, g in gs.items()}
    # 2/5/6 main route
    rows = {}
    for e, r in runs.items():
        m = r.get("main", {})
        rows[e] = {"route": m.get("route"), "km": round(m["length_m"] / 1000, 2) if m.get("length_m") else None,
                   "neutral_min": round(neutral.route(m.get("path")) / 60, 1) if m.get("path") else None,
                   "rule_breaks": len(m.get("violations", [])) if m.get("route") == "ILLEGAL" else 0}
    c["5_6_main_route"] = {"best_possible_min": round(best["main"] / 60, 1) if best["main"] else None,
                           "ranking": _rank({e: v for e, v in rows.items() if v["route"] == "VALID"},
                                            lambda v: v["neutral_min"]),
                           "not_valid": {e: v["route"] for e, v in rows.items() if v["route"] != "VALID"}}
    # 2 legality on every answer
    legal = {}
    for e, r in runs.items():
        answers = [r.get(k, {}) for k in gs]
        legal[e] = {"answers": len(answers), "illegal": sum(a.get("route") == "ILLEGAL" for a in answers),
                    "violations": sorted({v for a in answers for v in a.get("violations", [])})[:10]}
    c["2_road_rules_all_answers"] = legal
    # 7 speed: from the one-machine speed section only (engine jobs run on different machines)
    sp = json.loads((WORK / "speed.json").read_text()) if (WORK / "speed.json").exists() else {}
    c["7_route_time_ms"] = _rank({e: {"median_ms": statistics.median(v["query_ms"]), "scope": v["scope"],
                                      "map_setup_s": v["setup_s"]}
                                  for e, v in sp.items() if not e.startswith("_") and v.get("query_ms")},
                                 lambda v: v["median_ms"])
    s["speed_machine"] = sp.get("_meta", {}).get("machine")
    # 9 roundabouts on own route
    c["9_roundabout_exits_own_route"] = {e: r["main"].get("roundabouts") for e, r in runs.items()
                                         if r.get("main", {}).get("roundabouts")}
    # 12 wrong turns (reference form)
    wt = {}
    for e, r in runs.items():
        valid, ratio = 0, []
        for k in range(1, len(prepared["wrong_turns"]) + 1):
            a = r.get(f"wrong_turn_{k}", {})
            if a.get("route") == "VALID":
                valid += 1
                if best[f"wrong_turn_{k}"]:
                    ratio.append(neutral.route(a["path"]) / best[f"wrong_turn_{k}"])
        wt[e] = {"valid": valid, "of": len(prepared["wrong_turns"]),
                 "time_vs_best": round(statistics.median(ratio), 3) if ratio else None}
    c["12_new_route_after_wrong_turn"] = _rank(wt, lambda v: (-v["valid"], v["time_vs_best"] or 9))
    # 14 traffic
    tr = {}
    jam_ways = set(prepared["jam"]["ways"])
    for e, r in runs.items():
        a = r.get("traffic", {})
        path = a.get("path")
        uses = bool(path) and any(neutral.piece_way.get(p) in jam_ways for p in zip(path, path[1:]))
        tr[e] = {"route": a.get("route"), "avoids_jam": (not uses) if path else None,
                 "minutes_with_jam": round(jam_times.route(path) / 60, 1) if path else None}
    c["14_traffic_jam_replan"] = {"best_possible_min": round(best["traffic"] / 60, 1) if best["traffic"] else None,
                                  "staying_in_jam_min": round(jam_times.route(
                                      prepared["drive_nodes"][prepared["drive_nodes"].index(
                                          prepared["jam"]["decision_segment"][0]):]) / 60, 1),
                                  "ranking": _rank({e: v for e, v in tr.items() if v["route"] == "VALID"},
                                                   lambda v: v["minutes_with_jam"]),
                                  "not_valid": {e: v["route"] for e, v in tr.items() if v["route"] != "VALID"}}
    # 3/4 GPS
    dmn = runs.get("DMN", {}).get("drive")
    gps = {}
    for e, r in runs.items():
        if e == "DMN" and dmn:
            v = [f["match"] for f in dmn["fixes"]]
            after = [f["match"] for f in dmn["fixes"] if f["after_gap_s"]]
            scope = "live, fix by fix, its own drive (wrong turns, jam)"
        elif isinstance(r.get("match"), list):
            v = r["match"]
            after = []
            scope = "batch, whole frozen trace"
        else:
            continue
        cnt, ca = Counter(v), Counter(after)
        gps[e] = {"scope": scope, "fixes": len(v), "right_pct": round(100 * cnt["OK"] / len(v), 1),
                  "wrong_road_pct": round(100 * cnt["WRONG"] / len(v), 2), "next_piece": cnt["SAME_ROAD_NEXT_PIECE"],
                  "after_dropouts_right_pct": round(100 * ca["OK"] / len(after), 1) if after else None,
                  "error": r.get("match_error")}
    c["3_4_gps"] = gps
    if dmn:
        cues = Counter()
        for q in dmn["cues"]:
            d = q["true_distance_m"]
            cues["WRONG_CUE_OFF_ROUTE" if q["car_off_route"] else "AFTER_TURN" if d is None else
                 "LATE" if d < 10 else "ON_TIME"] += 1
        c["dmn_live_drive"] = {
            "12_wrong_turns": [{"at_m": w["at_m"], "noticed_after_s": None if w["noticed_t"] is None
                                else w["noticed_t"] - w["t"]} for w in dmn["wrong_turns"]],
            "12_reroutes": len(dmn["reroutes"]), "12_reroutes_valid": sum(x.get("route") == "VALID"
                                                                         for x in dmn["reroutes"]),
            "14_traffic": dmn["traffic"], "13_announcements": dict(cues),
            "16_arrival": dmn["arrival"], "lost": dmn["lost"],
            "drive_minutes": round(dmn["drive_s"] / 60, 1), "driven_km": round(dmn["driven_m"] / 1000, 2),
            "19_ms_per_fix": dmn["ms_per_fix"], "19_max_memory_mb": runs["DMN"].get("max_rss_mb"),
            "20_whole_journey": "PASS" if (dmn["arrival"] and dmn["arrival"]["to_destination_m"] <= 30
                                           and not dmn["lost"] and not cues.get("WRONG_CUE_OFF_ROUTE")) else "FAIL"}
    (WORK / "summary.json").write_text(json.dumps(s, indent=1, sort_keys=True, default=str))
    print(json.dumps(s, indent=1, default=str)[:6000])


def brief() -> int:
    """Plain summary: per category the ranking, the best engine and DMN's position."""
    s = json.loads((WORK / "summary.json").read_text())
    c = s["categories"]
    out = [f"## {s['contract']} @ {(s['revision'] or '')[:12]} (each category ranked on its own)",
           f"Drive {s['drive']['drive_m'] / 1000:.1f} km: {s['drive']['road_mix_km']}; jam {s['jam']['kph']} km/h "
           f"over {s['jam']['ways_m'] / 1000:.1f} km; same GPS trace for every engine: {s['same_trace_for_every_engine']}"]

    def table(title, rows, fmt):
        out.append(f"\n**{title}**")
        for k, r in enumerate(rows, 1):
            out.append(f"{k}. {r['engine']}: {fmt(r)}")
        pos = next((k for k, r in enumerate(rows, 1) if r["engine"] == "DMN"), None)
        out.append(f"   best: {rows[0]['engine'] if rows else '-'}; DMN position: {pos or 'not ranked'}")

    m = c["5_6_main_route"]
    table(f"Main route time (neutral speeds; best possible {m['best_possible_min']} min)", m["ranking"],
          lambda r: f"{r['neutral_min']} min, {r['km']} km")
    if m["not_valid"]:
        out.append(f"   not valid: {m['not_valid']}")
    rules = c["2_road_rules_all_answers"]
    out.append("\n**Road rules broken (all answers)**: " + "; ".join(
        f"{e} {v['illegal']}/{v['answers']}" for e, v in rules.items()))
    table("Route calculation time (same machine)", c["7_route_time_ms"],
          lambda r: f"{r['median_ms']} ms ({r['scope']}), map setup {r['map_setup_s']} s")
    out.append("\n**Roundabout exits on own route (correct/judged)**: " + "; ".join(
        f"{e} {v['correct']}/{v['judged']}" for e, v in c["9_roundabout_exits_own_route"].items()))
    table("New route after each wrong turn", c["12_new_route_after_wrong_turn"],
          lambda r: f"{r['valid']}/{r['of']} valid, time vs best {r['time_vs_best']}")
    tr = c["14_traffic_jam_replan"]
    table(f"Traffic jam (+30 min): new route (best possible {tr['best_possible_min']} min, "
          f"staying in the jam {tr['staying_in_jam_min']} min)", tr["ranking"],
          lambda r: f"{r['minutes_with_jam']} min, avoids jam: {r['avoids_jam']}")
    if tr["not_valid"]:
        out.append(f"   not valid: {tr['not_valid']}")
    gps = sorted(({"engine": e, **v} for e, v in c["3_4_gps"].items()),
                 key=lambda r: (r["wrong_road_pct"], -r["right_pct"]))
    table("GPS: which road (fewest wrong roads first)", gps,
          lambda r: f"right {r['right_pct']}%, wrong road {r['wrong_road_pct']}%, after drop-outs "
                    f"{r['after_dropouts_right_pct']}% ({r['scope']})")
    if "dmn_live_drive" in c:
        d = c["dmn_live_drive"]
        out.append("\n**DMN live drive (only DMN has live guidance)**")
        out.append(f"- wrong turns noticed after (s): {[w['noticed_after_s'] for w in d['12_wrong_turns']]}; "
                   f"reroutes {d['12_reroutes']} ({d['12_reroutes_valid']} legal)")
        out.append(f"- traffic: {d['14_traffic']}")
        out.append(f"- announcements: {d['13_announcements']}; arrival: {d['16_arrival']}; lost: {d['lost']}")
        out.append(f"- drive {d['drive_minutes']} min over {d['driven_km']} km; per fix {d['19_ms_per_fix']} ms; "
                   f"memory {d['19_max_memory_mb']} MB; whole journey: {d['20_whole_journey']}")
    errors = {e: v for e, v in s["errors"].items() if v}
    out.append(f"\nErrors: {errors or 'none'}")
    print("\n".join(out))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare")
    r = sub.add_parser("run")
    r.add_argument("--engines", nargs="*", choices=ENGINES, default=list(ENGINES))
    sub.add_parser("speed")
    sub.add_parser("score")
    sub.add_parser("brief")
    args = parser.parse_args()
    if args.cmd == "prepare":
        prepare()
    elif args.cmd == "run":
        run(tuple(args.engines))
    elif args.cmd == "speed":
        speed()
    elif args.cmd == "score":
        score()
    else:
        return brief()
    return 0


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    raise SystemExit(main())
