"""ACCESS-001 and ONEWAY-002: route-level legality checks on real Greater Manchester roads.

Two separately frozen and separately scored Category 2 tests share this harness and
one GitHub run (owner, 17 Oct 2026: combine execution where each stays separately
measured; never one combined score). Choose with --test access001 | oneway002.

ONEWAY-002 (one-way streets): the tested way is a real one-way road and the request
runs from the car road at its exit end to the car road at its entry end, so the
direct route drives it the wrong way. FAIL_AGAINST_ONEWAY when the route travels
any segment of it against its direction; groups by road kind (roundabout, major,
residential, service); the control removes the one-way rule.

ACCESS-001 (no-car roads):

Category 2 (road legality and restrictions), sibling of TURN-001 and BARRIER-001 and
reusing their clips, engine runners and whole-route audit. For a frozen,
pre-registered sample of real OpenStreetMap road ways that cars may not use, every
engine gets the SAME small clip of the SAME hashed snapshot and is asked for a car
route from the car road just before the way to the car road just after it, so the
direct route drives along it.

Road groups (from the way's own tags, decided before any engine ran):

closed      bus_gate   car road tagged no for cars (first of motorcar, motor_vehicle,
                       vehicle, access) with bus or psv yes/designated
            busway     highway=busway (no car access tag)
            no_cars    car road tagged no for cars, no bus exception
            pedestrian highway=pedestrian with no access tag, or tagged no
restricted  bus_private  private/destination... road with bus or psv yes/designated
            private      private
            destination  destination

Verdicts per engine and case (never invented, never pooled across unlike runs):

PASS                   closed: route does not use the way
FAIL_THROUGH_NO_CAR_ROAD  route uses a segment of a closed way
USED_RESTRICTED / AVOIDED_RESTRICTED   restricted group: reported, not judged
SAFE_NO_ROUTE          no route (re-asked on a clip three times wider)
UNRESOLVED_SNAP        route does not start and finish on the exact test segments
ENDPOINT_WITHHELD_BY_POLICY / ENGINE_REJECTED_MAP / ERROR   as in TURN-001

Every route is also audited against every one-way and turn restriction (TURN-001
audit), every closed barrier (BARRIER-001 audit) and every other closed road way it
uses. A DMN control with the tested way opened to cars marks DISCRIMINATING cases
(the unblocked route uses the way); an OSRM control run does the same as a harness
check. Source OSM is not independent legal truth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from benchmarks import barrier001_route as b1
from benchmarks import turn001_restrictions as t1

ROOT = t1.ROOT
SOURCE = t1.WORK / "gm.osm.pbf"  # pinned on data/turn001-snapshot
TESTS = {
    "access001": {"contract": "ACCESS-001 v1.1", "fail": "FAIL_THROUGH_NO_CAR_ROAD",
                  "broke": "drove a road closed to cars"},
    "oneway002": {"contract": "ONEWAY-002 v1", "fail": "FAIL_AGAINST_ONEWAY",
                  "broke": "drove the wrong way along a one-way road"},
}
TEST = "access001"
WORK = ROOT / "results" / TEST
COHORT = ROOT / "config" / f"{TEST}-cohort.json"
PREPARED = ROOT / "config" / f"{TEST}-prepared.json"
CONTRACT = TESTS[TEST]["contract"]
FAIL = TESTS[TEST]["fail"]


def use(test: str) -> None:
    """Point the harness at one test's own frozen files and results folder."""
    global TEST, WORK, COHORT, PREPARED, CONTRACT, FAIL
    TEST, WORK = test, ROOT / "results" / test
    COHORT, PREPARED = ROOT / "config" / f"{test}-cohort.json", ROOT / "config" / f"{test}-prepared.json"
    CONTRACT, FAIL = TESTS[test]["contract"], TESTS[test]["fail"]


# v1.1 (owner, before any result was reported): clips several miles wide so a real
# detour fits. Each clip is a 5 km (about 3 miles) square of roads, turn restrictions
# and barriers centred on the tested way; a no-route is re-asked on a 10 km square.
CLIP_KM, WIDE_SCALE = 5.0, 2
HALF_LAT = CLIP_KM / 2 * 1000 / 111_320
HALF_LON = CLIP_KM / 2 * 1000 / 66_220  # metres per degree of longitude at 53.5N
ROADS = t1.WORK / "roads.osm.pbf"  # source filtered to roads, restrictions and barriers
ACCESS_KEYS = ("motorcar", "motor_vehicle", "vehicle", "access")
BUS_KEYS = ("bus", "psv")
BUS_VALUES = {"yes", "designated"}
RESTRICTED_VALUES = {"private", "destination"}
# Road kinds a car route could be matched along (the test way included).
ROAD_HIGHWAYS = t1.CAR_HIGHWAYS | {"busway", "pedestrian"}
# Frozen stratum quotas (chosen before any engine was run).
QUOTAS = {
    ("closed", "bus_gate"): 30, ("closed", "busway"): 20, ("closed", "no_cars"): 40,
    ("closed", "pedestrian"): 30, ("restricted", "bus_private"): 15,
    ("restricted", "private"): 10, ("restricted", "destination"): 10,
}
ONEWAY_QUOTAS = {
    ("closed", "oneway_roundabout"): 15, ("closed", "oneway_major"): 25,
    ("closed", "oneway_residential"): 25, ("closed", "oneway_service"): 10,
}
MAJOR = {"trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link",
         "tertiary", "tertiary_link"}
MIN_WAY_M, MAX_WAY_M = 15.0, 400.0  # the whole way must fit well inside the clip
APPROACH_M = 20.0  # origin/destination points this far along the car road from the junction
MIN_SEGMENT_M = 5.0  # and on a segment at least this long


def car_value(tags: dict[str, str]) -> str | None:
    return next((tags[k] for k in ACCESS_KEYS if k in tags), None)


def road_class(tags: dict[str, str]) -> tuple[str, str] | None:
    """(group, kind) of a road way that cars may not freely use, or None."""
    highway = tags.get("highway")
    if highway not in ROAD_HIGHWAYS or tags.get("area") == "yes":
        return None
    if any(k.endswith(":conditional") for k in tags):
        return None
    value = car_value(tags)
    bus = any(tags.get(k) in BUS_VALUES for k in BUS_KEYS)
    if highway == "busway":
        return ("closed", "busway") if value is None or value == "no" else None
    if highway == "pedestrian":
        return ("closed", "pedestrian") if value is None or value == "no" else None
    if value == "no":
        return ("closed", "bus_gate") if bus else ("closed", "no_cars")
    if value in RESTRICTED_VALUES:
        return ("restricted", "bus_private") if bus else ("restricted", value)
    return None


def oneway_class(tags: dict[str, str]) -> tuple[str, str] | None:
    """(group, kind) of a one-way car road (no conditional or unusual rule), or None."""
    highway = tags.get("highway")
    if not t1.Clip.drivable(tags) or highway == "motorway" or tags.get("area") == "yes" \
            or any(k.endswith(":conditional") for k in tags) or car_value(tags) is not None:
        return None
    value = tags.get("oneway", "")
    if value not in ("", "yes", "1", "true", "-1", "reverse"):
        return None
    roundabout = tags.get("junction") in ("roundabout", "circular")
    if not value and not roundabout:
        return None
    kind = "roundabout" if roundabout else "major" if highway in MAJOR else \
        "service" if highway == "service" else "residential"
    return "closed", f"oneway_{kind}"


def is_oneway_case(case: dict) -> bool:
    return case["stratum"][1].startswith("oneway_")


# --------------------------------------------------------------------------- clips
class AccessClip(b1.BarrierClip):
    """BARRIER-001 clip plus every road way cars may not use, indexed for route matching."""

    def __init__(self, raw: bytes):
        super().__init__(raw)
        self.no_car: dict[str, tuple[str, str]] = {}
        for way, (refs, tags) in self.ways.items():
            group = road_class(tags)
            if group is not None:
                self.no_car[way] = group
            if not self.drivable(tags) and tags.get("highway") in ROAD_HIGHWAYS and tags.get("area") != "yes":
                for n in refs:  # matching only: lets a route along the way be read back
                    self.node_ways[n].add(way)

    def drivable_ways(self, node: str) -> list[str]:
        return sorted((w for w in self.node_ways.get(node, ()) if self.drivable(self.ways[w][1])), key=int)


def way_segments(refs: list[str]) -> set[tuple[str, str]]:
    return {s for a, b in zip(refs, refs[1:]) for s in ((a, b), (b, a))}


def uses_way(nodes: list[str], refs: list[str], directed: bool = False) -> bool:
    """The route travels a segment of the way (directed: in the order of refs)."""
    segs = set(zip(refs, refs[1:])) if directed else way_segments(refs)
    return any((x, y) in segs for x, y in zip(nodes, nodes[1:]))


def geom_uses_way(nodes: list[str], geom: dict) -> bool:
    return uses_way(nodes, geom["way_nodes"], directed=geom.get("against_oneway", False))


def way_length(clip: t1.Clip, refs: list[str]) -> float:
    return sum(t1.metres(clip.coords[a], clip.coords[b]) for a, b in zip(refs, refs[1:]))


def _approaches(clip: AccessClip, junction: str, test_way: str, avoid: set[str], arriving: bool) -> list[list[str]]:
    """Car-road stretches arriving at (or leaving) the junction, shortest walk first.

    Each walks along one car road away from the junction until it has covered
    APPROACH_M and its last segment is at least MIN_SEGMENT_M (BARRIER-001 style),
    so engines snap to a clear segment. Returned in travel order: the first
    (arriving) or last (leaving) segment is the test segment.
    """
    found = []
    for way in clip.drivable_ways(junction):
        if way == test_way:
            continue
        refs = clip.ways[way][0]
        for i, n in enumerate(refs):
            if n != junction:
                continue
            for step in (-1, 1):
                walk, walked, j = [junction], 0.0, i + step
                while 0 <= j < len(refs) and refs[j] not in avoid and refs[j] not in walk and refs[j] in clip.coords:
                    move = (refs[j], walk[-1]) if arriving else (walk[-1], refs[j])
                    if not clip.can_travel(way, *move):
                        break
                    seg_m = t1.metres(clip.coords[walk[-1]], clip.coords[refs[j]])
                    walk.append(refs[j])
                    walked += seg_m
                    if walked >= APPROACH_M and seg_m >= MIN_SEGMENT_M:
                        found.append((round(walked, 1), int(way), refs[j],
                                      list(reversed(walk)) if arriving else walk))
                        break
                    j += step
    return [path for *_, path in sorted(found)]


def case_geometry(case: dict, clip: AccessClip) -> dict:
    """Origin on the car road before the way, destination on the car road after it."""
    way = str(case["way"])
    group = case["stratum"][0]
    if way not in clip.ways or clip.ways[way][0] != [str(n) for n in case["refs"]] \
            or any(n not in clip.coords for n in clip.ways[way][0]):
        return {"status": "WAY_CHANGED_IN_CLIP", "group": group}
    refs = clip.ways[way][0]
    against = is_oneway_case(case)
    if against and clip.oneway(way) == 0:
        return {"status": "NOT_ONE_WAY_IN_CLIP", "group": group}
    # no-car road: travel its allowed direction; one-way road: travel against it
    if clip.oneway(way) == (1 if against else -1):
        refs = list(reversed(refs))
    origins = _approaches(clip, refs[0], way, set(refs), arriving=True)
    destinations = _approaches(clip, refs[-1], way, set(refs), arriving=False)
    if not origins or not destinations:
        return {"status": "NO_CAR_ROAD_AT_END", "group": group}
    # first pair (shortest walks first) that does not share nodes, so the direct path is simple
    pair = next(((o, d) for o in origins for d in destinations if not set(o) & set(d)), None)
    if pair is None:
        return {"status": "SAME_ROAD_BOTH_ENDS", "group": group}
    o_walk, d_walk = pair
    o_seg, d_seg = o_walk[:2], d_walk[-2:]
    direct = [*o_walk[:-1], *refs, *d_walk[1:]]

    def mid(seg):
        p, q = clip.coords[seg[0]], clip.coords[seg[1]]
        return [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2]
    return {"status": "TESTABLE", "group": group, "kind": case["stratum"][1], "way": way,
            "way_nodes": refs, "origin": mid(o_seg), "destination": mid(d_seg),
            "origin_segment": o_seg, "destination_segment": d_seg, "direct_path": direct,
            **({"against_oneway": True} if against else {})}


# --------------------------------------------------------------------------- cohort
def select(source: Path) -> None:
    if COHORT.exists():
        raise RuntimeError(f"{CONTRACT} frozen cohort exists; select a new named cohort instead of overwriting")
    WORK.mkdir(parents=True, exist_ok=True)
    classify, quotas = (oneway_class, ONEWAY_QUOTAS) if TEST == "oneway002" else (road_class, QUOTAS)
    what = "one-way car road" if TEST == "oneway002" else "road way cars may not use"
    label = CONTRACT.split()[0]
    hw, ways_opl, nodes_opl = WORK / "hw.osm.pbf", WORK / "ways.opl", WORK / "nodes.opl"
    subprocess.run(["osmium", "tags-filter", str(source), "w/highway", "-O", "-o", str(hw)], check=True)
    subprocess.run(["osmium", "cat", str(hw), "-O", "-o", str(ways_opl), "-t", "way",
                    "-f", "opl,add_metadata=false"], check=True)
    subprocess.run(["osmium", "cat", str(hw), "-O", "-o", str(nodes_opl), "-t", "node",
                    "-f", "opl,add_metadata=false"], check=True)
    coords: dict[str, tuple[float, float]] = {}
    for line in nodes_opl.read_text().splitlines():
        parts = line.split(" ")
        lon = next(p for p in parts if p.startswith("x"))[1:]
        lat = next(p for p in parts if p.startswith("y"))[1:]
        if lon and lat:
            coords[parts[0][1:]] = (float(lat), float(lon))
    car_nodes: Counter = Counter()
    candidates = []
    for line in ways_opl.read_text().splitlines():
        parts = line.split(" ")
        tags = b1._opl_tags(next((p for p in parts if p.startswith("T")), "T"))
        refs = [r[1:] for r in next(p for p in parts if p.startswith("N"))[1:].split(",")]
        if t1.Clip.drivable(tags):
            car_nodes.update(set(refs))
        key = classify(tags)
        if key is None or len(refs) < 2 or refs[0] == refs[-1] or len(set(refs)) != len(refs) \
                or any(r not in coords for r in refs):
            continue
        length = sum(t1.metres(coords[a], coords[b]) for a, b in zip(refs, refs[1:]))
        if MIN_WAY_M <= length <= MAX_WAY_M:
            candidates.append({"way": int(parts[0][1:]), "stratum": list(key), "tags": tags,
                               "refs": [int(r) for r in refs], "length_m": round(length, 1)})
    # Both ends must meet another road open to cars (checked again on the clip itself).
    own = 1 if TEST == "oneway002" else 0  # a one-way road is itself open to cars
    found = [c for c in candidates if car_nodes[str(c["refs"][0])] > own and car_nodes[str(c["refs"][-1])] > own]
    for c in found:
        mid = [coords[str(r)] for r in c["refs"]]
        c["lat"] = round(sum(p[0] for p in mid) / len(mid), 7)
        c["lon"] = round(sum(p[1] for p in mid) / len(mid), 7)
    chosen = []
    for key, quota in quotas.items():
        pool = [c for c in found if tuple(c["stratum"]) == key]
        pool.sort(key=lambda c: hashlib.sha256(f"{label}:{c['way']}".encode()).hexdigest())
        chosen.extend(pool[:quota])
    COHORT.write_text(json.dumps({
        "contract": CONTRACT,
        "frozen_before_engine_runs": True,
        "selection_rule": f"{what}, {MIN_WAY_M:g}-{MAX_WAY_M:g} m, not closed, not conditional, "
                          f"both end nodes on {'another' if own else 'a'} road open to cars; per-stratum quota, "
                          f"ordered by sha256('{label}:'+way_id)",
        "quotas": {"/".join(k): v for k, v in quotas.items()},
        "source_snapshot": source.name,
        "source_sha256": t1.sha256_file(source),
        "available_by_stratum": dict(sorted(Counter("/".join(c["stratum"]) for c in found).items())),
        "cases": chosen,
    }, indent=1, sort_keys=True))
    for path in (hw, ways_opl, nodes_opl):
        path.unlink()
    print(f"Frozen {len(chosen)} cases of {len(found)} candidate ways -> {COHORT}")


def roads_source(source: Path = SOURCE) -> Path:
    """The pinned source reduced to roads, turn restrictions and barriers (cut once)."""
    if not ROADS.exists():
        if t1.sha256_file(source) != json.loads(COHORT.read_text())["source_sha256"]:
            raise SystemExit("Source snapshot does not match the frozen cohort")
        WORK.mkdir(parents=True, exist_ok=True)
        subprocess.run(["osmium", "tags-filter", "--overwrite", str(source), "w/highway", "r/type=restriction",
                        "n/barrier", "-o", str(ROADS)], check=True)
    return ROADS


def bbox_around(lat: float, lon: float, scale: float = 1) -> str:
    hy, hx = HALF_LAT * scale, HALF_LON * scale
    return f"{lon-hx:.6f},{lat-hy:.6f},{lon+hx:.6f},{lat+hy:.6f}"


def cut(folder: Path, bbox: str) -> bytes:
    folder.mkdir(parents=True, exist_ok=True)
    pbf = folder / "clip.osm.pbf"
    subprocess.run(["osmium", "extract", "--overwrite", "--strategy", "complete_ways",
                    f"--bbox={bbox}", str(roads_source()), "-o", str(pbf)], check=True)
    subprocess.run(["osmium", "cat", "--overwrite", str(pbf), "-o", str(folder / "clip.osm"),
                    "-f", "osm,add_metadata=false"], check=True)
    return (folder / "clip.osm").read_bytes()


def prepare(source: Path) -> None:
    """Freeze each clip's hash and test geometry (clips are deleted again: they are large)."""
    cohort = json.loads(COHORT.read_text())
    roads_source(source)
    out = []
    for case in cohort["cases"]:
        folder = WORK / "cases" / str(case["way"])
        bbox = bbox_around(case["lat"], case["lon"])
        raw = cut(folder, bbox)
        out.append({"way": case["way"], "node": case["way"], "stratum": case["stratum"], "bbox": bbox,
                    "clip_km": CLIP_KM, "clip_sha256": hashlib.sha256(raw).hexdigest(), "clip_bytes": len(raw),
                    "geometry": case_geometry(case, AccessClip(raw))})
        subprocess.run(["rm", "-rf", str(folder)], check=True)
        print(case["way"], out[-1]["geometry"]["status"], flush=True)
    text = json.dumps(out, indent=1)
    if PREPARED.exists() and PREPARED.read_text() != text:
        raise SystemExit("Prepared clips differ from the frozen config/access001-prepared.json")
    PREPARED.write_text(text)
    print(Counter(r["geometry"]["status"] for r in out))
    print(Counter("/".join(r["stratum"]) for r in out if r["geometry"]["status"] == "TESTABLE"))


def case_clip(record: dict) -> bytes:
    """Cut the case's clip from the pinned source; it must match the frozen hash."""
    folder = WORK / "cases" / str(record["way"])
    raw = (folder / "clip.osm").read_bytes() if (folder / "clip.osm").exists() else cut(folder, record["bbox"])
    if hashlib.sha256(raw).hexdigest() != record["clip_sha256"]:
        raise RuntimeError(f"{CONTRACT} {record['way']}: clip bytes differ from the frozen hash")
    return raw


def wide_clip(record: dict) -> Path:
    """Same case on a clip WIDE_SCALE times wider."""
    folder = WORK / "cases" / str(record["way"]) / "wide"
    if not (folder / "clip.osm").exists():
        w, s_, e, n = map(float, record["bbox"].split(","))
        cut(folder, bbox_around((s_ + n) / 2, (w + e) / 2, WIDE_SCALE))
    return folder


def opened(raw: bytes, way: str) -> bytes:
    """The clip with the tested way opened to cars, or made two-way (control)."""
    root = ET.fromstring(raw)
    for e in root.iter("way"):
        if e.get("id") != way:
            continue
        for tag in list(e.findall("tag")):
            k = tag.get("k")
            if TEST == "oneway002":
                if k == "oneway" or k.startswith("oneway:"):
                    e.remove(tag)
                elif k == "junction":
                    tag.set("v", "yes")  # roundabouts are one-way by implication
            elif k in ACCESS_KEYS or k.endswith(":conditional"):
                e.remove(tag)
            elif k == "highway" and tag.get("v") in ("busway", "pedestrian"):
                tag.set("v", "unclassified")
        if TEST == "oneway002":
            ET.SubElement(e, "tag", {"k": "oneway", "v": "no"})
    return ET.tostring(root)


# --------------------------------------------------------------------------- verdicts
def audit_roads(clip: AccessClip, nodes: list[str], tested: str) -> dict:
    """Other closed / restricted road ways the route drives along."""
    closed, uncertain = set(), set()
    for x, y in zip(nodes, nodes[1:]):
        ways = [w for w in clip.node_ways.get(x, ()) if (x, y) in way_segments(clip.ways[w][0])]
        if not ways or tested in ways or any(clip.drivable(clip.ways[w][1]) for w in ways):
            continue
        for w in ways:
            group = clip.no_car.get(w)
            if group and group[0] == "closed":
                closed.add(f"road:{w}:{group[1]}")
            elif group:
                uncertain.add(f"road:{w}:{group[1]}")
    return {"other_closed_roads": sorted(closed), "other_restricted_roads": sorted(uncertain)}


def verdict(clip: AccessClip, geom: dict, nodes: list[str] | None, error: str | None = None) -> dict:
    if error == "ENDPOINT_WITHHELD":
        return {"verdict": "ENDPOINT_WITHHELD_BY_POLICY"}
    if error is not None:
        return {"verdict": "ERROR", "detail": error[:300]}
    if nodes is None:
        return {"verdict": "SAFE_NO_ROUTE"}
    through = geom_uses_way(nodes, geom)
    rules = t1.audit_route(clip, nodes)
    extra = {"nodes": len(nodes), "path": nodes, "uses_way": through, **rules,
             **b1.audit_barriers(clip, nodes, ""), **audit_roads(clip, nodes, geom["way"])}
    breaks = extra["other_closed_barriers"] + extra["other_closed_roads"]
    if breaks:
        extra["route_legal"] = "ILLEGAL"
        extra["violations"] = sorted(extra["violations"] + breaks)
    anchored = nodes[:2] == list(geom["origin_segment"]) and nodes[-2:] == list(geom["destination_segment"])
    if geom["group"] == "closed" and through:
        return {"verdict": FAIL, **extra}
    if not anchored:
        return {"verdict": "UNRESOLVED_SNAP", **extra}
    if geom["group"] == "closed":
        return {"verdict": "PASS", **extra}
    return {"verdict": "USED_RESTRICTED" if through else "AVOIDED_RESTRICTED", **extra}


# --------------------------------------------------------------------------- runs
ENGINES = ("DMN", "OSRM", "GraphHopper", "Valhalla")


def _provenance(engine: str) -> dict:
    frozen = json.loads(COHORT.read_text())
    if not frozen.get("frozen_before_engine_runs") or not frozen.get("source_sha256"):
        raise RuntimeError(f"{CONTRACT} source cohort is not frozen")
    return {"schema": 1, "engine": engine, "revision": t1._revision(),
            "cohort_sha256": t1.sha256_file(COHORT), "source_sha256": frozen["source_sha256"],
            "prepared_sha256": t1.sha256_file(PREPARED), "runner_sha256": t1.sha256_file(Path(__file__))}


def _control_label(nodes: list[str] | None, rejected: str | None, geom: dict) -> str:
    return "REJECTED" if rejected else "NO_ROUTE" if nodes is None else \
        "USES_WAY" if geom_uses_way(nodes, geom) else "AVOIDS_WAY"


def run(engine: str, *, control: bool = False, only: set[str] | None = None) -> None:
    prepared = json.loads(PREPARED.read_text())
    name = f"{engine}-control" if control else engine
    out = WORK / f"run-{name}.json"
    WORK.mkdir(parents=True, exist_ok=True)
    results: dict = {"_provenance": _provenance(name)}
    for record in prepared:
        way, geom = str(record["way"]), record["geometry"]
        if geom["status"] != "TESTABLE" or (only and way not in only):
            continue
        folder = WORK / "cases" / way
        raw = case_clip(record)
        clip = AccessClip(raw)
        entry: dict = {"clip_sha256": record["clip_sha256"]}
        if engine == "DMN":
            began = time.perf_counter()
            nodes, error, rejected = t1.dmn_route(raw, geom)
            entry["ms_import_and_route"] = round((time.perf_counter() - began) * 1000, 1)
            entry.update({"verdict": "ENGINE_REJECTED_MAP", "detail": rejected[:300]} if rejected
                         else verdict(clip, geom, nodes, error))
            c_nodes, _, c_rejected = t1.dmn_route(opened(raw, way), geom)
            entry["control_opened_way"] = _control_label(c_nodes, c_rejected, geom)
        elif control:
            ctrl = WORK / "control" / way
            ctrl.mkdir(parents=True, exist_ok=True)
            craw = opened(raw, way)
            (ctrl / "clip.osm").write_bytes(craw)
            subprocess.run(["osmium", "cat", "--overwrite", str(ctrl / "clip.osm"), "-o", str(ctrl / "clip.osm.pbf")],
                           check=True)
            entry.update(t1.engine_case(engine, ctrl, AccessClip(craw), geom, judge=verdict))
            entry["uses_way"] = geom_uses_way(entry.get("path", []), geom)
        else:
            entry.update(t1.engine_case(engine, folder, clip, geom, judge=verdict))
        if entry.get("verdict") == "SAFE_NO_ROUTE" and not control:
            wide = wide_clip(record)
            wraw = (wide / "clip.osm").read_bytes()
            wclip = AccessClip(wraw)
            if engine == "DMN":
                nodes, error, rejected = t1.dmn_route(wraw, geom)
                wide_entry = ({"verdict": "ENGINE_REJECTED_MAP", "detail": rejected[:300]} if rejected
                              else verdict(wclip, geom, nodes, error))
            else:
                wide_entry = t1.engine_case(engine, wide, wclip, geom, judge=verdict)
            entry["wide_clip"] = {"scale": WIDE_SCALE, "clip_sha256": hashlib.sha256(wraw).hexdigest(),
                                  **wide_entry}
        results[way] = entry
        out.write_text(json.dumps(results, indent=1, sort_keys=True))
        subprocess.run(["rm", "-rf", str(folder), str(WORK / "control" / way)], check=False)
        print(way, entry.get("verdict"), entry.get("detail", "")[:100], flush=True)


def final(entry: dict) -> dict:
    if entry.get("verdict") == "SAFE_NO_ROUTE" and "wide_clip" in entry:
        return {**entry["wide_clip"], "base_clip_verdict": "SAFE_NO_ROUTE"}
    return entry


ROUTED = {"PASS", "USED_RESTRICTED", "AVOIDED_RESTRICTED", "FAIL_THROUGH_NO_CAR_ROAD", "FAIL_AGAINST_ONEWAY"}


def score() -> None:
    prepared = {str(r["way"]): r for r in json.loads(PREPARED.read_text())}
    runs = {e: json.loads((WORK / f"run-{e}.json").read_text()) for e in ENGINES if (WORK / f"run-{e}.json").exists()}
    for name, record in runs.items():
        if record.get("_provenance") != _provenance(name):
            raise RuntimeError(f"{CONTRACT} {name}: stale/unprovenanced result")
    testable = [n for n, r in prepared.items() if r["geometry"]["status"] == "TESTABLE"]
    dmn = runs.get("DMN", {})
    discriminating = [n for n in testable if dmn.get(n, {}).get("control_opened_way") == "USES_WAY"]
    finals = {e: {n: final(r[n]) for n in testable if n in r} for e, r in runs.items()}

    def legal_pass(e, n):
        f = finals[e].get(n, {})
        return f.get("verdict") == "PASS" and f.get("route_legal") == "LEGAL"

    def kind(n):
        return "/".join(prepared[n]["stratum"])
    summary = {
        "contract": CONTRACT, "revision": t1._revision(), "cohort_sha256": t1.sha256_file(COHORT),
        "prepared_sha256": t1.sha256_file(PREPARED),
        "source_sha256": json.loads(COHORT.read_text())["source_sha256"],
        "cases_frozen": len(prepared),
        "geometry_status": dict(Counter(r["geometry"]["status"] for r in prepared.values())),
        "testable_by_kind": dict(sorted(Counter(kind(n) for n in testable).items())),
        "testable_cases": len(testable), "discriminating_cases": len(discriminating),
        "discriminating_by_kind": dict(sorted(Counter(kind(n) for n in discriminating).items())),
        "truth": "OpenStreetMap road access and one-way tags in the hashed snapshot; not independent UK legal truth",
        "engines": {},
    }
    for name, res in finals.items():
        by_kind: dict[str, Counter] = defaultdict(Counter)
        for n, f in res.items():
            by_kind[kind(n)][f["verdict"]] += 1
        ms_key = "ms_import_and_route" if name == "DMN" else "warm_query_ms"
        summary["engines"][name] = {
            "by_kind": {g: dict(c) for g, c in sorted(by_kind.items())},
            "discriminating": dict(Counter(res[n]["verdict"] for n in discriminating if n in res)),
            "pass_and_route_legal": sum(1 for n in res if legal_pass(name, n)),
            "fail_cases": sorted(n for n, f in res.items() if f["verdict"] == FAIL),
            "other_rule_violations": {n: f["violations"] for n, f in res.items() if f.get("route_legal") == "ILLEGAL"
                                      and f["verdict"] != FAIL},
            "no_route_but_legal_route_exists": {
                n: sorted(e for e in finals if legal_pass(e, n)) for n, f in res.items()
                if f["verdict"] == "SAFE_NO_ROUTE" and any(legal_pass(e, n) for e in finals)},
            "passes_via_restricted_roads_or_gates": {
                n: f["other_restricted_roads"] + f["other_uncertain_barriers"] for n, f in res.items()
                if legal_pass(name, n) and (f.get("other_restricted_roads") or f.get("other_uncertain_barriers"))},
            "endpoint_withheld": sorted(n for n, f in res.items() if f["verdict"] == "ENDPOINT_WITHHELD_BY_POLICY"),
            # Category 5 (route computation and validity), scored apart from the legality result:
            # a route was returned and starts and finishes on the exact test segments.
            "category5_route_validity": dict(Counter(
                "valid_route" if f["verdict"] in ROUTED else
                "no_route" if f["verdict"] == "SAFE_NO_ROUTE" else
                "off_target" if f["verdict"] == "UNRESOLVED_SNAP" else "error_or_rejected"
                for f in res.values())),
            "query_ms": b1._ms([runs[name][n][ms_key] for n in testable
                                if runs[name].get(n, {}).get(ms_key) is not None]),
            "executed": len(res),
        }
    (WORK / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
    print(json.dumps(summary, indent=1)[:3000])


def brief() -> int:
    """A few lines for the job page; exit 1 if DMN drives along a closed road."""
    s = json.loads((WORK / "summary.json").read_text())
    lines = [f"{s['contract']} @ {s['revision'][:12]}: {s['testable_cases']} testable "
             f"{s['testable_by_kind']}, {s['discriminating_cases']} discriminating"]
    for name, e in s["engines"].items():
        kinds = "; ".join(f"{g}: " + ", ".join(f"{k} {v}" for k, v in sorted(c.items()))
                          for g, c in e["by_kind"].items())
        lines.append(f"- {name}: {kinds} | legal passes {e['pass_and_route_legal']}; "
                     f"{TESTS[TEST]['broke']} {len(e['fail_cases'])}; "
                     f"other rule breaks {len(e['other_rule_violations'])}; "
                     f"no-route with a legal alternative {len(e['no_route_but_legal_route_exists'])}; "
                     f"median {e['query_ms']['median']} ms")
    lines.append("Category 5 (separate): routes returned on the exact test segments — " + "; ".join(
        f"{name} {e['category5_route_validity'].get('valid_route', 0)}/{e['executed']}"
        for name, e in s["engines"].items()))
    bad = []
    if s["engines"].get("DMN", {}).get("fail_cases"):
        bad.append(f"DMN {TESTS[TEST]['broke']}")
    control = WORK / "run-OSRM-control.json"
    if control.exists():
        ctrl = {k: v for k, v in json.loads(control.read_text()).items() if not k.startswith("_")}
        dmn = json.loads((WORK / "run-DMN.json").read_text())
        disc = [k for k in ctrl if dmn.get(k, {}).get("control_opened_way") == "USES_WAY"]
        used = sum(1 for k in disc if ctrl[k].get("uses_way"))
        lines.append(f"- harness check (OSRM with the tested rule removed): uses the road in {used} "
                     f"of {len(disc)} discriminating cases")
        if disc and used == 0:
            bad.append("harness check: control never used the road once its rule was removed")
    lines.append("RESULT: " + ("; ".join(bad) if bad else "OK"))
    print("\n".join(lines))
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", choices=sorted(TESTS), default="access001")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ("select", "prepare"):
        sub.add_parser(cmd).add_argument("--source", type=Path, default=SOURCE)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--engine", choices=ENGINES, required=True)
    run_parser.add_argument("--control", action="store_true", help="remove the tested rule (harness check)")
    run_parser.add_argument("--only", nargs="*")
    sub.add_parser("score")
    sub.add_parser("brief")
    args = parser.parse_args()
    use(args.test)
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
