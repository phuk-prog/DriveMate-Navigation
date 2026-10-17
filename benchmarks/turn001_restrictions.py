"""TURN-001: real Greater Manchester turn-restriction route legality comparison.

Category 1 (map data and road graph). For a frozen, pre-registered sample of
real OpenStreetMap turn-restriction relations, every engine receives the SAME
small clipped extract of the SAME hashed snapshot and is asked for a car route
whose shortest unrestricted path would make the restricted movement. Each
route is mapped back to OSM nodes and checked for the prohibited movement:

* ``no_*``    start on the ``from`` way, finish on the ``to`` way;
* ``only_*``  start on the ``from`` way, finish on another exit at the via point.

Verdicts per engine and case (never invented, never pooled across unlike runs):

PASS                 route found, prohibited movement not used, anchored on both ways
FAIL_PROHIBITED      route uses the prohibited movement
SAFE_NO_ROUTE        engine returned no route (legal but unhelpful; reported apart)
UNRESOLVED_SNAP      route not anchored on the from/destination way (cannot judge)
ENGINE_REJECTED_MAP  engine refused to load the identical clip (capability failure)
ERROR                engine/harness failure, with the message preserved

v1.2 adds a whole-route audit to every returned route (route_legal LEGAL or
ILLEGAL with every other one-way or restriction relation it breaks) and stores
the OSM node path, so a no-route answer can be checked against a legal route
another engine found on the identical clip. v1.1 verdict meanings are unchanged.
v1.3 also gives every reference engine the direction of travel on the start and
end segments (OSRM bearings, GraphHopper heading, Valhalla heading), as DMN gets it.
v1.3 runs DMN as a real journey: an uncertain road (e.g. untagged service road)
may be the start or finish, never a through route; mapped closures still refuse.
v1.3 fixes a harness flaw for engines that start mid-segment: their paths now
include the first and last partial segments, and PASS requires the exact origin
and destination segments (v1.1/v1.2 reference-engine results are superseded).

A positive control routes DMN on the same clip with only the tested relation
removed; cases whose unrestricted route uses the movement are DISCRIMINATING
and get their own separate ranking. Source OSM is not independent legal truth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "results" / "turn001"
COHORT = ROOT / "config" / "turn001-cohort.json"
CONTRACT = "TURN-001 v1.3"
CAR_HIGHWAYS = {
    "motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link",
    "secondary", "secondary_link", "tertiary", "tertiary_link", "unclassified",
    "residential", "living_street", "service", "road",
}
NO_CAR = {"no", "private", "agricultural", "forestry", "delivery", "permit", "customers", "destination"}
# Frozen stratum quotas (chosen before any engine was run).
QUOTAS = {
    ("via-node", "no_right_turn"): 20, ("via-node", "no_left_turn"): 20,
    ("via-node", "no_u_turn"): 12, ("via-node", "no_straight_on"): 15,
    ("via-node", "only_straight_on"): 20, ("via-node", "only_right_turn"): 15,
    ("via-node", "only_left_turn"): 15, ("via-node", "no_entry"): 13,
    ("via-node", "only_u_turn"): 4, ("via-way", "*"): 30, ("conditional", "*"): 6,
}
HALF_LAT, HALF_LON = 0.0042, 0.0070  # about 470 m x 465 m each side at 53.5N


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def metres(p: tuple[float, float], q: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (p[0], p[1], q[0], q[1]))
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 12_742_000 * math.asin(min(1.0, math.sqrt(a)))


def bearing(p: tuple[float, float], q: tuple[float, float]) -> int:
    lat1, lon1, lat2, lon2 = map(math.radians, (p[0], p[1], q[0], q[1]))
    y = math.sin(lon2 - lon1) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
    return round(math.degrees(math.atan2(y, x))) % 360


def travel_headings(clip: "Clip", geom: dict) -> tuple[int, int]:
    """v1.3: compass direction of travel on the origin and destination segments.

    DMN receives the direction as its incoming/destination edge; reference engines
    receive the same information through their public heading/bearing parameters.
    """
    (a, b), (c, d) = geom["origin_segment"], geom["destination_segment"]
    return bearing(clip.coords[a], clip.coords[b]), bearing(clip.coords[c], clip.coords[d])


HEADING_TOLERANCE = 30


# --------------------------------------------------------------------------- cohort
def _rule(tags: dict[str, str]) -> str | None:
    return tags.get("restriction:motorcar") or tags.get("restriction:motor_vehicle") or tags.get("restriction")


def _applies_to_cars(tags: dict[str, str]) -> bool:
    exempt = {v.strip() for v in tags.get("except", "").replace(",", ";").split(";")}
    return not exempt & {"motorcar", "motor_vehicle", "vehicle"}


def select(source: Path) -> None:
    import osmium

    found = []

    class Relations(osmium.SimpleHandler):
        def relation(self, r):  # noqa: D401 - osmium callback
            tags = {t.k: t.v for t in r.tags}
            if tags.get("type") != "restriction":
                return
            members = [(m.type, m.ref, m.role) for m in r.members]
            vias = [m for m in members if m[2] == "via"]
            conditional = any(k.endswith(":conditional") for k in tags)
            if conditional:
                stratum = ("conditional", "*")
            elif vias and all(m[0] == "w" for m in vias):
                stratum = ("via-way", "*")
            elif len(vias) == 1 and vias[0][0] == "n":
                stratum = ("via-node", _rule(tags) or "")
            else:
                return
            found.append({"relation": r.id, "stratum": list(stratum), "tags": tags,
                          "members": [list(m) for m in members]})

    Relations().apply_file(str(source))
    chosen = []
    for key, quota in QUOTAS.items():
        pool = [c for c in found if tuple(c["stratum"]) == key]
        pool.sort(key=lambda c: hashlib.sha256(f"TURN-001:{c['relation']}".encode()).hexdigest())
        chosen.extend(pool[:quota])
    COHORT.parent.mkdir(parents=True, exist_ok=True)
    COHORT.write_text(json.dumps({
        "contract": CONTRACT,
        "frozen_before_engine_runs": True,
        "selection_rule": "per-stratum quota, ordered by sha256('TURN-001:'+relation_id)",
        "quotas": {"/".join(k): v for k, v in QUOTAS.items()},
        "source_snapshot": source.name,
        "source_sha256": sha256_file(source),
        "available_by_stratum": dict(Counter("/".join(c["stratum"]) for c in found)),
        "cases": chosen,
    }, indent=1, sort_keys=True))
    print(f"Frozen {len(chosen)} cases of {len(found)} restriction relations -> {COHORT}")


# --------------------------------------------------------------------------- clips
class Clip:
    """Minimal topology of one clipped OSM XML extract (read-only)."""

    def __init__(self, raw: bytes):
        root = ET.fromstring(raw)
        self.coords: dict[str, tuple[float, float]] = {}
        self.ways: dict[str, tuple[list[str], dict[str, str]]] = {}
        self.node_ways: dict[str, set[str]] = defaultdict(set)
        self.relations: dict[str, tuple[dict[str, str], list[tuple[str, str, str]]]] = {}
        for e in root:
            if e.tag == "node":
                self.coords[e.get("id")] = (float(e.get("lat")), float(e.get("lon")))
            elif e.tag == "way":
                tags = {t.get("k"): t.get("v") for t in e.findall("tag")}
                refs = [n.get("ref") for n in e.findall("nd")]
                self.ways[e.get("id")] = (refs, tags)
                if self.drivable(tags):
                    for n in refs:
                        self.node_ways[n].add(e.get("id"))
            elif e.tag == "relation":
                tags = {t.get("k"): t.get("v") for t in e.findall("tag")}
                if tags.get("type") == "restriction":
                    self.relations[e.get("id")] = (tags, [(m.get("type"), m.get("ref"), m.get("role"))
                                                          for m in e.findall("member")])
        grid: dict[tuple[int, int], list[str]] = defaultdict(list)
        for node, (lat, lon) in self.coords.items():
            grid[(round(lat * 1e4), round(lon * 1e4))].append(node)
        self._grid = grid

    @staticmethod
    def drivable(tags: dict[str, str]) -> bool:
        if tags.get("highway") not in CAR_HIGHWAYS or tags.get("area") == "yes":
            return False
        for key in ("motorcar", "motor_vehicle", "vehicle", "access"):
            if key in tags:
                return tags[key] not in NO_CAR
        return True

    def oneway(self, way: str) -> int:
        tags = self.ways[way][1]
        value = tags.get("oneway", "")
        if value in ("yes", "1", "true") or (not value and tags.get("junction") in ("roundabout", "circular")) \
                or (not value and tags.get("highway") in ("motorway",)):
            return 1
        return -1 if value in ("-1", "reverse") else 0

    def can_travel(self, way: str, frm: str, to: str) -> bool:
        """Whether a car may travel from node frm to adjacent node to along way."""
        refs = self.ways[way][0]
        for i, (a, b) in enumerate(zip(refs, refs[1:])):
            if (a, b) == (frm, to):
                return self.oneway(way) != -1
            if (a, b) == (to, frm):
                return self.oneway(way) != 1
        return False

    def neighbour(self, way: str, node: str, away_side: int) -> str | None:
        refs = self.ways[way][0]
        if node not in refs:
            return None
        i = refs.index(node) + away_side
        return refs[i] if 0 <= i < len(refs) else None

    def segment_point(self, way: str, node: str, toward_node: bool) -> tuple[tuple[float, float], str, str] | None:
        """A mid-segment point on `way` 30-120 m from `node` (deterministic).

        Returns (point, segment_start, segment_end) oriented in travel direction
        (toward `node` when toward_node, otherwise away from it).
        """
        refs = self.ways[way][0]
        if node not in refs:
            return None
        i = refs.index(node)
        if i not in (0, len(refs) - 1):
            return None  # way passes through: side is ambiguous
        path = refs if i == 0 else list(reversed(refs))  # path[0] == node, walking away
        walked = 0.0
        for a, b in zip(path, path[1:]):
            if a not in self.coords or b not in self.coords:
                return None
            length = metres(self.coords[a], self.coords[b])
            if walked + length >= 30 or b == path[-1] or walked + length > 120:
                lat = self.coords[a][0] + 0.5 * (self.coords[b][0] - self.coords[a][0])
                lon = self.coords[a][1] + 0.5 * (self.coords[b][1] - self.coords[a][1])
                start, end = (b, a) if toward_node else (a, b)
                if not self.can_travel(way, start, end):
                    return None
                return (lat, lon), start, end
            walked += length
        return None

    def _nearest(self, point: tuple[float, float], tolerance_m: float) -> str | None:
        best, best_d = None, tolerance_m
        key = (round(point[0] * 1e4), round(point[1] * 1e4))
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for node in self._grid.get((key[0] + dy, key[1] + dx), ()):
                    d = metres(point, self.coords[node])
                    if d <= best_d:
                        best, best_d = node, d
        return best

    def match_nodes(self, points: list[tuple[float, float]], tolerance_m: float = 1.0) -> list[str]:
        """Map route geometry back to OSM nodes (exact within tolerance).

        v1.3: also walks each line between consecutive route points, so nodes an
        engine simplified away are restored; a restored node must share a way with
        the previous node, which keeps nodes of crossing roads out.
        """
        out: list[str] = []

        def add(node: str | None) -> None:
            if node is not None and (not out or out[-1] != node):
                out.append(node)

        for k, point in enumerate(points):
            if k:
                prev = points[k - 1]
                gap = metres(prev, point)
                steps = int(gap // 0.5)
                for j in range(1, steps):
                    t = j / steps
                    node = self._nearest((prev[0] + t * (point[0] - prev[0]),
                                          prev[1] + t * (point[1] - prev[1])), tolerance_m)
                    if node is not None and out and node != out[-1] and \
                            self.node_ways.get(node, set()) & self.node_ways.get(out[-1], set()):
                        add(node)
            add(self._nearest(point, tolerance_m))
        return out


def _member(case: dict, role: str, kind: str) -> list[str]:
    return [str(ref) for typ, ref, r in case["members"] if r == role and typ == kind]


def case_geometry(case: dict, clip: Clip) -> dict:
    """Derive the prohibited node sequence and test endpoints from the clip."""
    frm, to = _member(case, "from", "w"), _member(case, "to", "w")
    via_n, via_w = _member(case, "via", "n"), _member(case, "via", "w")
    rule = _rule(case["tags"]) or ""
    if case["stratum"][0] == "conditional":
        for key, value in case["tags"].items():
            if key.endswith(":conditional"):
                rule = value.split("@")[0].strip()
    if not rule.startswith(("no_", "only_")):
        return {"status": "UNSUPPORTED_RULE", "rule": rule}
    if len(frm) != 1 or len(to) != 1 or (len(via_n), len(via_w)) not in ((1, 0), (0, 1)):
        return {"status": "UNSUPPORTED_MEMBERS", "rule": rule}
    f, t = frm[0], to[0]
    if f not in clip.ways or t not in clip.ways or (via_w and via_w[0] not in clip.ways):
        return {"status": "MEMBER_OUTSIDE_CLIP", "rule": rule}
    if via_n:
        a = b = via_n[0]
        chain: list[str] = [a]
    else:
        w = via_w[0]
        refs = clip.ways[w][0]
        shared_f = set(clip.ways[f][0]) & {refs[0], refs[-1]}
        shared_t = set(clip.ways[t][0]) & {refs[0], refs[-1]}
        if len(shared_f) != 1 or len(shared_t) != 1 or shared_f == shared_t:
            return {"status": "UNSUPPORTED_VIA_WAY_GEOMETRY", "rule": rule}
        a, b = shared_f.pop(), shared_t.pop()
        chain = refs if refs[0] == a else list(reversed(refs))
        for x, y in zip(chain, chain[1:]):
            if not clip.can_travel(w, x, y):
                return {"status": "VIA_WAY_NOT_TRAVERSABLE", "rule": rule}
    origin = clip.segment_point(f, a, toward_node=True)
    if origin is None:
        return {"status": "FROM_WAY_NOT_APPROACHABLE", "rule": rule}
    f_prev = origin[1] if origin[2] == a else clip.neighbour(f, a, 1 if clip.ways[f][0].index(a) == 0 else -1)
    if rule.startswith("no_"):
        exits = [t]
    else:
        exits = sorted((w for w in clip.node_ways.get(b, ()) if w not in (t, f) and w != (via_w[0] if via_w else None)),
                       key=int)
    for exit_way in exits:
        dest = clip.segment_point(exit_way, b, toward_node=False)
        if dest is None:
            continue
        refs = clip.ways[exit_way][0]
        side = 1 if refs.index(b) == 0 else -1
        t_next = clip.neighbour(exit_way, b, side)
        prohibited = [f_prev] + chain + [t_next]
        return {"status": "TESTABLE", "rule": rule, "origin": origin[0], "destination": dest[0],
                "origin_segment": [origin[1], origin[2]], "destination_segment": [dest[1], dest[2]],
                "from_way": f, "exit_way": exit_way, "prohibited_sequence": prohibited,
                "via_way": via_w[0] if via_w else None}
    return {"status": "NO_DRIVABLE_EXIT", "rule": rule}


def uses_sequence(nodes: list[str], seq: list[str]) -> bool:
    n = len(seq)
    return any(nodes[i:i + n] == seq for i in range(len(nodes) - n + 1))


# --------------------------------------------------------------------------- v1.2 whole-route audit
def _adjacent(clip: Clip, way: str, node: str) -> set[str]:
    refs = clip.ways[way][0]
    return {refs[i + d] for i, n in enumerate(refs) if n == node for d in (-1, 1) if 0 <= i + d < len(refs)}


def _via_chain(clip: Clip, start: str, via_ways: list[str]) -> list[str] | None:
    """Order via ways end to end from `start`; the node path, or None if ambiguous."""
    remaining, path, at = list(via_ways), [start], start
    while remaining:
        nxt = [w for w in remaining if at in (clip.ways[w][0][0], clip.ways[w][0][-1])]
        if len(nxt) != 1:
            return None
        refs = clip.ways[nxt[0]][0]
        refs = refs if refs[0] == at else list(reversed(refs))
        path.extend(refs[1:])
        at = refs[-1]
        remaining.remove(nxt[0])
    return path


def audit_route(clip: Clip, nodes: list[str]) -> dict:
    """Check a whole route (OSM node path) against every car rule mapped in the clip.

    Rules: one-way direction of each travelled segment and every type=restriction
    relation (via node, via way chains, no_entry/no_exit products, truncated only_).
    Movements barred by a conditional restriction are listed apart (no clock is
    evaluated); unorderable or ambiguous relations are listed as not judged.
    """
    violations: list[str] = []
    conditional_hits: list[str] = []
    not_judged: list[str] = []
    for x, y in zip(nodes, nodes[1:]):
        ways = [w for w in clip.node_ways.get(x, ()) if y in _adjacent(clip, w, x)]
        if ways and not any(clip.can_travel(w, x, y) for w in ways):
            violations.append(f"oneway:{'/'.join(sorted(ways))}:{x}>{y}")
    for rid, (tags, members) in sorted(clip.relations.items()):
        conditional = next((v.split("@")[0].strip() for k, v in tags.items()
                            if k.startswith("restriction") and k.endswith(":conditional")), None)
        if not _applies_to_cars(tags):
            continue
        rule = conditional or _rule(tags) or ""
        if not rule.startswith(("no_", "only_")):
            continue
        frm = [r for t, r, role in members if role == "from" and t == "way" and r in clip.ways]
        to = [r for t, r, role in members if role == "to" and t == "way" and r in clip.ways]
        to_missing = any(role == "to" and r not in clip.ways for t, r, role in members if t == "way")
        via_n = [r for t, r, role in members if role == "via" and t == "node"]
        via_w = [r for t, r, role in members if role == "via" and t == "way"]
        if via_n and via_w or len(via_n) > 1 or not (via_n or via_w) or any(w not in clip.ways for w in via_w):
            not_judged.append(f"{rid}:structure")
            continue
        if rule.startswith("only_") and (len(frm) != 1 or len(to) > 1):
            not_judged.append(f"{rid}:only_multi")
            continue
        for f in frm:
            if via_n:
                chain = [via_n[0]]
            else:
                ends = [n for n in (clip.ways[f][0][0], clip.ways[f][0][-1])
                        if any(n in (clip.ways[w][0][0], clip.ways[w][0][-1]) for w in via_w)]
                chain = _via_chain(clip, ends[0], via_w) if len(ends) == 1 else None
                if chain is None:
                    not_judged.append(f"{rid}:via_order")
                    continue
            entries = _adjacent(clip, f, chain[0]) - ({chain[1]} if len(chain) > 1 else set())
            n = len(chain)
            for i in range(1, len(nodes) - n):
                if nodes[i:i + n] != chain or nodes[i - 1] not in entries:
                    continue
                p, q = nodes[i - 1], nodes[i + n]
                end = chain[-1]
                if rule.startswith("no_"):
                    hit = any((q == p) if (t == f and n == 1) else (q in _adjacent(clip, t, end)) for t in to)
                elif to:
                    t = to[0]
                    hit = (q != p) if (t == f and n == 1) else (q not in _adjacent(clip, t, end))
                else:
                    hit = to_missing  # only_ towards a way outside the clip: every exit here is barred
                if hit:
                    (conditional_hits if conditional else violations).append(f"restriction:{rid}:{rule}")
    legal = "ILLEGAL" if violations else "DEPENDS_ON_CONDITION" if conditional_hits else "LEGAL"
    return {"route_legal": legal, "violations": sorted(set(violations)),
            "conditional_movements_used": sorted(set(conditional_hits)), "not_judged": sorted(set(not_judged))}


def prepare(source: Path) -> None:
    cohort = json.loads(COHORT.read_text())
    if sha256_file(source) != cohort["source_sha256"]:
        raise SystemExit("Source snapshot does not match the frozen cohort")
    import osmium

    needed_nodes: set[int] = set()
    needed_ways: set[int] = set()
    for case in cohort["cases"]:
        for typ, ref, _ in case["members"]:
            (needed_nodes if typ == "n" else needed_ways).add(int(ref))
    way_nodes: dict[int, list[int]] = {}

    class Ways(osmium.SimpleHandler):
        def way(self, w):
            if w.id in needed_ways:
                way_nodes[w.id] = [n.ref for n in w.nodes]
    Ways().apply_file(str(source))
    for refs in way_nodes.values():
        needed_nodes.update(refs)
    coords: dict[int, tuple[float, float]] = {}

    class Nodes(osmium.SimpleHandler):
        def node(self, n):
            if n.id in needed_nodes:
                coords[n.id] = (n.location.lat, n.location.lon)
    Nodes().apply_file(str(source))

    out = []
    for case in cohort["cases"]:
        rid = case["relation"]
        vias = [(typ, int(ref)) for typ, ref, role in case["members"] if role == "via"]
        if vias and vias[0][0] == "n":
            anchor = coords.get(vias[0][1])
        else:
            pts = [coords[n] for typ, ref in vias for n in way_nodes.get(ref, []) if n in coords]
            anchor = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else None
        folder = WORK / "cases" / str(rid)
        folder.mkdir(parents=True, exist_ok=True)
        record = {"relation": rid, "stratum": case["stratum"]}
        if anchor is None:
            record["geometry"] = {"status": "VIA_OUTSIDE_SNAPSHOT"}
            out.append(record)
            continue
        bbox = f"{anchor[1]-HALF_LON:.6f},{anchor[0]-HALF_LAT:.6f},{anchor[1]+HALF_LON:.6f},{anchor[0]+HALF_LAT:.6f}"
        pbf = folder / "clip.osm.pbf"
        subprocess.run(["osmium", "extract", "--overwrite", "--strategy", "complete_ways",
                        f"--bbox={bbox}", str(source), "-o", str(pbf)], check=True)
        subprocess.run(["osmium", "cat", "--overwrite", str(pbf), "-o", str(folder / "clip.osm"),
                        "-f", "osm,add_metadata=false"], check=True)
        raw = (folder / "clip.osm").read_bytes()
        record.update(bbox=bbox, clip_sha256=hashlib.sha256(raw).hexdigest(), clip_bytes=len(raw),
                      geometry=case_geometry(case, Clip(raw)))
        out.append(record)
    (WORK / "prepared.json").write_text(json.dumps(out, indent=1))
    print(Counter(r["geometry"]["status"] for r in out))


WIDE_SCALE = 3


def wide_clip(record: dict, source: Path | None = None) -> Path:
    """v1.3: the same case on a clip WIDE_SCALE times wider (roads and restrictions only).

    Used, identically for every engine, only to re-ask a case that had no route on
    the base clip, so a missing way round at the clip edge is not mistaken for a
    real dead end. Cached per case; hashed in the run record.
    """
    folder = WORK / "cases" / str(record["relation"]) / "wide"
    if (folder / "clip.osm").exists():
        return folder
    folder.mkdir(parents=True, exist_ok=True)
    w, so, e, n = map(float, record["bbox"].split(","))
    cx, cy, hx, hy = (w + e) / 2, (so + n) / 2, (e - w) / 2 * WIDE_SCALE, (n - so) / 2 * WIDE_SCALE
    raw_pbf = folder / "all.osm.pbf"
    subprocess.run(["osmium", "extract", "--overwrite", "--strategy", "complete_ways",
                    f"--bbox={cx-hx:.6f},{cy-hy:.6f},{cx+hx:.6f},{cy+hy:.6f}",
                    str(source or WORK / "gm.osm.pbf"), "-o", str(raw_pbf)], check=True)
    subprocess.run(["osmium", "tags-filter", "--overwrite", str(raw_pbf), "w/highway", "r/type=restriction",
                    "-o", str(folder / "clip.osm.pbf")], check=True)
    raw_pbf.unlink()
    subprocess.run(["osmium", "cat", "--overwrite", str(folder / "clip.osm.pbf"), "-o", str(folder / "clip.osm"),
                    "-f", "osm,add_metadata=false"], check=True)
    return folder


# --------------------------------------------------------------------------- engines
def _verdict(clip: Clip, geom: dict, nodes: list[str] | None, error: str | None = None) -> dict:
    if error == "ENDPOINT_WITHHELD":
        # DMN policy withholds the start/finish road (e.g. untagged service road);
        # neither a pass nor a legality failure: reported separately for review.
        # v1.2 split: OSM itself bars cars from an endpoint way (correct to withhold)
        # versus DMN's uncertain-access policy (untagged service roads: owner decision).
        barred = [w for w in (geom["from_way"], geom["exit_way"]) if not clip.drivable(clip.ways[w][1])]
        return {"verdict": "ENDPOINT_WITHHELD_BY_POLICY",
                "endpoint_reason": "osm_bars_cars" if barred else "uncertain_access_policy"}
    if error is not None:
        return {"verdict": "ERROR", "detail": error[:300]}
    if nodes is None:
        return {"verdict": "SAFE_NO_ROUTE"}
    seq = geom["prohibited_sequence"]
    extra = {"nodes": len(nodes), "path": nodes, **audit_route(clip, nodes)}  # v1.2 whole-route audit
    if uses_sequence(nodes, seq):
        return {"verdict": "FAIL_PROHIBITED", **extra}
    # v1.3: anchored only when the path starts on the exact origin segment and ends on
    # the exact destination segment, both in travel direction (v1.1/v1.2 accepted any
    # node of the from/exit way, which could not see a banned move made at the start).
    anchored = nodes[:2] == list(geom["origin_segment"]) and nodes[-2:] == list(geom["destination_segment"])
    return {"verdict": "PASS" if anchored else "UNRESOLVED_SNAP", **extra}


SNAP_TOLERANCE_M = 5.0


def engine_path(clip: Clip, geom: dict, points: list[tuple[float, float]]) -> tuple[list[str], dict]:
    """OSM node path of an engine route, including the partial first and last segments.

    Engines start and finish at the mid-segment test points, which are not OSM nodes;
    when the route begins (ends) at the test point, the segment's start (end) node is
    restored so a banned move at the first or last junction stays visible (v1.3).
    """
    nodes = clip.match_nodes(points)
    o_seg, d_seg = list(geom["origin_segment"]), list(geom["destination_segment"])
    start_gap = metres(points[0], tuple(geom["origin"])) if points else None
    end_gap = metres(points[-1], tuple(geom["destination"])) if points else None
    if start_gap is not None and start_gap <= SNAP_TOLERANCE_M and nodes[:1] == o_seg[1:]:
        nodes.insert(0, o_seg[0])
    if end_gap is not None and end_gap <= SNAP_TOLERANCE_M and nodes[-1:] == d_seg[:1]:
        nodes.append(d_seg[1])
    return nodes, {"start_snap_m": None if start_gap is None else round(start_gap, 1),
                   "end_snap_m": None if end_gap is None else round(end_gap, 1)}


def dmn_route(raw: bytes, geom: dict, drop_relation: int | None = None) -> tuple[list[str] | None, str | None, str | None]:
    """Returns (nodes, error, import_rejection)."""
    from engine import RouteNotFound, shortest_route
    from map_data import OSMImportError, Provenance, import_osm_xml

    if drop_relation is not None:
        root = ET.fromstring(raw)
        for rel in list(root.findall("relation")):
            if rel.get("id") == str(drop_relation):
                root.remove(rel)
        raw = ET.tostring(root)
    try:
        imported = import_osm_xml(raw, provenance=Provenance(
            region="Greater Manchester (TURN-001 clip)", snapshot="openstreetmap.fr north_west 7332146",
            source="OpenStreetMap", attribution="© OpenStreetMap contributors, ODbL"))
    except OSMImportError as exc:
        return None, None, str(exc)
    coords = imported.coordinates

    def segment_edge(start: str, end: str):
        for edge in imported.graph.edges.values():
            if edge.source == f"osm:{start}" and edge.target == f"osm:{end}":
                # v1.3: like a real journey, the car may start on / head for an
                # uncertain road; only roads mapped as closed to cars are refused.
                return edge if edge.access != "prohibited" else None
        return None

    start = segment_edge(*geom["origin_segment"])
    finish = segment_edge(*geom["destination_segment"])
    if start is None or finish is None:
        return None, "ENDPOINT_WITHHELD", None
    try:
        # v1.1: finish by travelling the destination segment so the turn onto it is
        # checked (v1 appended it unchecked; preserved in run-DMN-v1-before-fixes.json).
        route = shortest_route(imported.graph, start.target, finish.target, incoming_edge_id=start.edge_id,
                               destination_edge_id=finish.edge_id, endpoint_uncertain_access=True)
    except RouteNotFound:
        return None, None, None
    except ValueError as exc:
        return None, str(exc), None
    nodes = [start.source, start.target]
    for edge_id in route.edge_ids:
        nodes.append(imported.graph.edges[edge_id].target)
    clean = [n.removeprefix("osm:") for n in nodes]
    return [n for i, n in enumerate(clean) if i == 0 or clean[i - 1] != n], None, None


def _http_json(url: str, body: bytes | None = None, timeout: float = 30) -> dict:
    from urllib.request import Request, urlopen
    req = Request(url, data=body, headers={"Content-Type": "application/json"} if body else {})
    with urlopen(req, timeout=timeout) as response:  # noqa: S310 - local engine only
        return json.loads(response.read())


def _decode_polyline(text: str, precision: int) -> list[tuple[float, float]]:
    coords, index, lat, lon, factor = [], 0, 0, 0, 10 ** precision
    while index < len(text):
        for which in (0, 1):
            shift = result = 0
            while True:
                b = ord(text[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if which == 0:
                lat += delta
            else:
                lon += delta
        coords.append((lat / factor, lon / factor))
    return coords


def osrm_query(geom: dict, headings: tuple[int, int]) -> tuple[list[tuple[float, float]] | None, float]:
    o, d = geom["origin"], geom["destination"]
    url = (f"http://127.0.0.1:5000/route/v1/driving/{o[1]:.7f},{o[0]:.7f};{d[1]:.7f},{d[0]:.7f}"
           "?overview=full&geometries=geojson&continue_straight=true"
           f"&bearings={headings[0]},{HEADING_TOLERANCE};{headings[1]},{HEADING_TOLERANCE}")
    from urllib.error import HTTPError
    began = time.perf_counter()
    try:
        data = _http_json(url)
    except HTTPError as exc:
        data = json.loads(exc.read() or b"{}")
    ms = (time.perf_counter() - began) * 1000
    if data.get("code") == "NoRoute":
        return None, ms
    if data.get("code") != "Ok":
        raise RuntimeError(f"OSRM {data.get('code')}: {data.get('message', '')[:200]}")
    return [(lat, lon) for lon, lat in data["routes"][0]["geometry"]["coordinates"]], ms


def graphhopper_query(geom: dict, headings: tuple[int, int]) -> tuple[list[tuple[float, float]] | None, float]:
    from urllib.error import HTTPError
    o, d = geom["origin"], geom["destination"]
    # Headings need the non-CH (exact, same weighting) search in GraphHopper.
    url = (f"http://127.0.0.1:8989/route?point={o[0]:.7f},{o[1]:.7f}&point={d[0]:.7f},{d[1]:.7f}"
           "&profile=car&points_encoded=false&instructions=false&ch.disable=true&way_point_max_distance=0"
           f"&heading={headings[0]}&heading={headings[1]}")
    began = time.perf_counter()
    try:
        data = _http_json(url)
    except HTTPError as exc:
        body = json.loads(exc.read() or b"{}")
        if any("ConnectionNotFound" in str(h.get("details", "")) for h in body.get("hints", [])):
            return None, (time.perf_counter() - began) * 1000
        raise RuntimeError(f"GraphHopper HTTP {exc.code}: {body.get('message', '')[:200]}") from exc
    ms = (time.perf_counter() - began) * 1000
    return [(lat, lon) for lon, lat in data["paths"][0]["points"]["coordinates"]], ms


def valhalla_query(geom: dict, headings: tuple[int, int]) -> tuple[list[tuple[float, float]] | None, float]:
    from urllib.error import HTTPError
    o, d = geom["origin"], geom["destination"]
    body = json.dumps({"locations": [
        {"lat": o[0], "lon": o[1], "heading": headings[0], "heading_tolerance": HEADING_TOLERANCE},
        {"lat": d[0], "lon": d[1], "heading": headings[1], "heading_tolerance": HEADING_TOLERANCE}],
                       "costing": "auto", "directions_type": "none"}).encode()
    began = time.perf_counter()
    try:
        data = _http_json("http://127.0.0.1:8002/route", body)
    except HTTPError as exc:
        payload = json.loads(exc.read() or b"{}")
        if payload.get("error_code") in (442, 443):  # no path / no route between locations
            return None, (time.perf_counter() - began) * 1000
        raise RuntimeError(f"Valhalla {payload.get('error_code')}: {payload.get('error', '')[:200]}") from exc
    ms = (time.perf_counter() - began) * 1000
    points: list[tuple[float, float]] = []
    for leg in data["trip"]["legs"]:
        points.extend(_decode_polyline(leg["shape"], 6))
    return points, ms


def run(engine: str, control: bool = False, only: set[str] | None = None) -> None:
    """Run one engine; with control, on each clip minus the tested relation (harness check)."""
    prepared = json.loads((WORK / "prepared.json").read_text())
    out = WORK / f"run-{engine}{'-control' if control else ''}.json"
    results = json.loads(out.read_text()) if out.exists() else {}
    for record in prepared:
        rid = str(record["relation"])
        geom = record["geometry"]
        if geom["status"] != "TESTABLE" or rid in results or (only and rid not in only):
            continue
        folder = WORK / "cases" / rid
        raw = (folder / "clip.osm").read_bytes()
        clip = Clip(raw)
        entry: dict = {"clip_sha256": record["clip_sha256"]}
        if engine == "DMN":
            began = time.perf_counter()
            nodes, error, rejected = dmn_route(raw, geom)
            entry["ms_import_and_route"] = round((time.perf_counter() - began) * 1000, 1)
            if rejected:
                entry.update(verdict="ENGINE_REJECTED_MAP", detail=rejected[:300])
            else:
                entry.update(_verdict(clip, geom, nodes, error))
            ctrl_nodes, ctrl_error, ctrl_rejected = dmn_route(raw, geom, drop_relation=record["relation"])
            entry["control_without_relation"] = (
                "REJECTED" if ctrl_rejected else "NO_ROUTE" if ctrl_nodes is None else
                "USES_MOVEMENT" if uses_sequence(ctrl_nodes, geom["prohibited_sequence"]) else "AVOIDS_MOVEMENT")
        elif control:
            root = ET.fromstring(raw)
            for rel in root.findall("relation"):
                if rel.get("id") == rid:
                    root.remove(rel)
            ctrl = WORK / "control" / rid
            ctrl.mkdir(parents=True, exist_ok=True)
            (ctrl / "clip.osm").write_bytes(ET.tostring(root))
            subprocess.run(["osmium", "cat", "--overwrite", str(ctrl / "clip.osm"), "-o", str(ctrl / "clip.osm.pbf")],
                           check=True)
            entry.update(engine_case(engine, ctrl, Clip(ET.tostring(root)), geom))
        else:
            entry.update(engine_case(engine, folder, clip, geom))
        if entry.get("verdict") == "SAFE_NO_ROUTE" and not control:
            wide = wide_clip(record)
            wraw = (wide / "clip.osm").read_bytes()
            wclip = Clip(wraw)
            if engine == "DMN":
                nodes, error, rejected = dmn_route(wraw, geom)
                wide_entry = ({"verdict": "ENGINE_REJECTED_MAP", "detail": rejected[:300]} if rejected
                              else _verdict(wclip, geom, nodes, error))
            else:
                wide_entry = engine_case(engine, wide, wclip, geom)
            entry["wide_clip"] = {"scale": WIDE_SCALE, "clip_sha256": hashlib.sha256(wraw).hexdigest(), **wide_entry}
        results[rid] = entry
        out.write_text(json.dumps(results, indent=1, sort_keys=True))
        print(rid, entry.get("verdict"), entry.get("detail", "")[:100], flush=True)


IMAGES = {
    "OSRM": "ghcr.io/project-osrm/osrm-backend:v5.27.1@sha256:855614a38f464b0558a2ad6eaa7cb8c139f39887da9b38b485ce453c6e6e6124",
    "Valhalla": "ghcr.io/valhalla/valhalla-scripted:3.9.1@sha256:6238809f9dc3057743d70a20efd3911ec38e458bfa13a0601909b58f68dfd956",
}


def _wait(url: str, seconds: float, body: bytes | None = None) -> None:
    deadline = time.time() + seconds
    from urllib.request import Request, urlopen
    while time.time() < deadline:
        try:
            req = Request(url, data=body, headers={"Content-Type": "application/json"} if body else {})
            with urlopen(req, timeout=3) as response:  # noqa: S310 - local engine only
                if response.status == 200:  # any body: GraphHopper /health answers plain "OK"
                    return
        except Exception:  # noqa: BLE001 - polling a starting local server
            time.sleep(0.5)
    raise RuntimeError(f"Local engine did not start: {url}")


def engine_case(engine: str, folder: Path, clip: Clip, geom: dict) -> dict:
    work = folder / engine.lower()
    subprocess.run(["rm", "-rf", str(work)], check=False)
    work.mkdir(parents=True)
    subprocess.run(["cp", str(folder / "clip.osm.pbf"), str(work / "input.osm.pbf")], check=True)
    name = f"turn001-{engine.lower()}"
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    proc = None
    try:
        if engine == "OSRM":
            image = IMAGES["OSRM"]
            for step in (["osrm-extract", "-p", "/opt/car.lua", "/data/input.osm.pbf"],
                         ["osrm-partition", "/data/input.osrm"], ["osrm-customize", "/data/input.osrm"]):
                r = subprocess.run(["docker", "run", "--rm", "-v", f"{work}:/data", image, *step],
                                   capture_output=True, text=True)
                if r.returncode:
                    return {"verdict": "ENGINE_REJECTED_MAP", "detail": (r.stderr or r.stdout)[-300:]}
            subprocess.run(["docker", "run", "-d", "--rm", "--name", name, "-p", "127.0.0.1:5000:5000",
                            "-v", f"{work}:/data", image, "osrm-routed", "--algorithm", "mld", "/data/input.osrm"],
                           check=True, capture_output=True)
            _wait("http://127.0.0.1:5000/nearest/v1/driving/%f,%f" % (geom["origin"][1], geom["origin"][0]), 30)
            points, ms = osrm_query(geom, travel_headings(clip, geom))
        elif engine == "Valhalla":
            image = IMAGES["Valhalla"]
            subprocess.run(["docker", "run", "-d", "--rm", "--name", name, "-p", "127.0.0.1:8002:8002",
                            "-v", f"{work}:/custom_files", "-e", "build_admins=False", "-e", "build_time_zones=False",
                            "-e", "build_elevation=False", "-e", "build_transit=False", "-e", "serve_tiles=True",
                            "-e", "use_tiles_ignore_pbf=False", "-e", "use_default_speeds_config=False",
                            "-e", "build_tar=False", "-e", "server_threads=2", image], check=True, capture_output=True)
            probe = json.dumps({"locations": [{"lat": geom["origin"][0], "lon": geom["origin"][1]}]}).encode()
            _wait("http://127.0.0.1:8002/locate", 900, probe)
            points, ms = valhalla_query(geom, travel_headings(clip, geom))
        elif engine == "GraphHopper":
            jar = WORK / "engines" / "gh.jar"
            config = work / "config.yml"
            config.write_text(graphhopper_config(work / "input.osm.pbf", work / "cache"))
            log = (work / "startup.log").open("w")
            proc = subprocess.Popen(["/opt/jdk17/bin/java", "-Xmx1g", "-jar", str(jar), "server", str(config)],
                                    stdout=log, stderr=subprocess.STDOUT)
            _wait("http://127.0.0.1:8989/health", 90)
            points, ms = graphhopper_query(geom, travel_headings(clip, geom))
        else:
            raise ValueError(engine)
    except Exception as exc:  # noqa: BLE001 - recorded, never hidden
        return {"verdict": "ERROR", "detail": f"{type(exc).__name__}: {exc}"[:300]}
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=30)
        subprocess.run(["sudo", "-n", "rm", "-rf", str(work)], capture_output=True)
    if points is None:
        result = _verdict(clip, geom, None)
    else:
        nodes, snaps = engine_path(clip, geom, points)
        result = {**_verdict(clip, geom, nodes), **snaps}
    result["warm_query_ms"] = round(ms, 1)
    return result


def graphhopper_config(pbf: Path, cache: Path) -> str:
    """The repository's pinned GraphHopper 11.1 config; only paths and min network size change."""
    text = (ROOT / "config" / "graphhopper-public-smoke.yml").read_text()
    text = text.replace("results/public-graphhopper-subset.osm.pbf", str(pbf))
    text = text.replace("results/graphhopper-cache", str(cache))
    return text.replace("prepare.min_network_size: 10", "prepare.min_network_size: 0")


# --------------------------------------------------------------------------- score
ENGINES = ("DMN", "OSRM", "GraphHopper", "Valhalla")


def final(entry: dict) -> dict:
    """v1.3 final answer: a base-clip no-route is replaced by the wide-clip answer."""
    if entry.get("verdict") == "SAFE_NO_ROUTE" and "wide_clip" in entry:
        return {**entry["wide_clip"], "base_clip_verdict": "SAFE_NO_ROUTE"}
    return entry


def score() -> None:
    prepared = json.loads((WORK / "prepared.json").read_text())
    runs = {e: json.loads((WORK / f"run-{e}.json").read_text()) for e in ENGINES if (WORK / f"run-{e}.json").exists()}
    testable = [str(r["relation"]) for r in prepared if r["geometry"]["status"] == "TESTABLE"]
    dmn = runs.get("DMN", {})
    discriminating = [rid for rid in testable if dmn.get(rid, {}).get("control_without_relation") == "USES_MOVEMENT"]
    summary = {
        "contract": CONTRACT,
        "cohort_sha256": sha256_file(COHORT),
        "cases_frozen": len(prepared),
        "geometry_status": dict(Counter(r["geometry"]["status"] for r in prepared)),
        "testable_cases": len(testable),
        "discriminating_cases": len(discriminating),
        "engines": {},
        "truth": "OpenStreetMap restriction relations in the hashed snapshot; not independent UK legal truth",
    }
    base_runs = runs
    runs = {e: {i: final(r) for i, r in res.items()} for e, res in base_runs.items()}
    for name, res in runs.items():
        def counts(ids):
            return dict(Counter(res[i]["verdict"] for i in ids if i in res))
        ms = sorted(v.get("warm_query_ms") for v in res.values() if v.get("warm_query_ms") is not None)
        summary["engines"][name] = {
            "all_testable": counts(testable), "discriminating": counts(discriminating),
            "base_clip_only_all_testable": dict(Counter(base_runs[name][i]["verdict"] for i in testable
                                                        if i in base_runs[name])),
            "answered_on_wide_clip": sorted(i for i in testable if "wide_clip" in base_runs[name].get(i, {})),
            "executed": sum(1 for i in testable if i in res),
            "fail_cases": sorted(i for i in testable if res.get(i, {}).get("verdict") == "FAIL_PROHIBITED"),
            # v1.2: whole-route audit and checked no-route answers
            "endpoint_withheld_reasons": dict(Counter(res[i]["endpoint_reason"] for i in testable
                                                      if "endpoint_reason" in res.get(i, {}))),
            "route_legal": dict(Counter(res[i]["route_legal"] for i in testable if "route_legal" in res.get(i, {}))),
            "pass_and_route_legal": sum(1 for i in testable if res.get(i, {}).get("verdict") == "PASS"
                                        and res[i].get("route_legal") == "LEGAL"),
            "other_rule_violations": {i: res[i]["violations"] for i in testable
                                      if res.get(i, {}).get("route_legal") == "ILLEGAL"},
            "no_route_but_legal_route_exists": {
                i: sorted(e for e, other in runs.items() if other.get(i, {}).get("verdict") == "PASS"
                          and other[i].get("route_legal") == "LEGAL")
                for i in testable if res.get(i, {}).get("verdict") == "SAFE_NO_ROUTE"
                and any(other.get(i, {}).get("verdict") == "PASS" and other[i].get("route_legal") == "LEGAL"
                        for other in runs.values())},
            "warm_query_ms_median": ms[len(ms) // 2] if ms else None,
            "warm_query_ms_samples": len(ms),
        }
    (WORK / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
    print(json.dumps(summary, indent=1)[:4000])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ("select", "prepare"):
        sub.add_parser(cmd).add_argument("--source", type=Path, default=WORK / "gm.osm.pbf")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--engine", choices=ENGINES, required=True)
    run_parser.add_argument("--control", action="store_true", help="drop the tested relation (harness check)")
    run_parser.add_argument("--only", nargs="*", help="limit to these relation ids")
    sub.add_parser("score")
    args = parser.parse_args()
    if args.cmd == "select":
        select(args.source)
    elif args.cmd == "prepare":
        prepare(args.source)
    elif args.cmd == "run":
        run(args.engine, args.control, set(args.only or ()) or None)
    else:
        score()


if __name__ == "__main__":
    main()
