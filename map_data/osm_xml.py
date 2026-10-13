"""Bounded OSM XML importer for an auditable *prototype* directed motorcar graph.

Supported: public-driving highway classes, one-way (+/-), roundabout direction,
explicit motorcar access, source geometry, maxspeed-based *cost estimate*,
node-via turn restrictions ('no_' and 'only_') and simple blocking barriers.

Unsupported conditions fail CLOSED (reject entire extract); see README.
Never treat this importer as road-legal navigation without independent checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import asin, cos, isfinite, radians, sin, sqrt
import re
import xml.etree.ElementTree as ET

from engine import RoadEdge, RoadGraph

MAX_INPUT_BYTES = 6_000_000
# Purposefully small enough for auditable prototype examples, NOT UK extracts.
MAX_OBJECTS = 30_000
DRIVING_SPEEDS = {
    "motorway": 95, "trunk": 80, "primary": 55, "secondary": 48,
    "tertiary": 40, "unclassified": 35, "residential": 30,
    "living_street": 12, "motorway_link": 45, "trunk_link": 45,
    "primary_link": 35, "secondary_link": 30, "tertiary_link": 25,
}
UNCERTAIN_ROADS = {"service", "track"}
ALLOWED_VALUES = {"yes", "designated", "permissive"}
BLOCKED_VALUES = {"no", "private", "agricultural", "forestry", "delivery",
                  "destination", "customers", "permit"}
BLOCKING_BARRIERS = {"bollard", "block", "cycle_barrier", "bus_trap"}
UNCERTAIN_BARRIERS = {"gate", "lift_gate", "swing_gate", "cattle_grid"}
CONDITIONAL = re.compile(r"(?:^|:)conditional$")
MAXSPEED = re.compile(r"^([0-9]+(?:\.[0-9]+)?)\s*(mph|km/h|kph)?$", re.I)


class OSMImportError(ValueError):
    """Extract contains insufficient or unsupported data for safe prototype import."""


@dataclass(frozen=True)
class Provenance:
    region: str
    snapshot: str
    source: str
    attribution: str

    def __post_init__(self):
        if not all((self.region.strip(), self.snapshot.strip(), self.source.strip(),
                    self.attribution.strip())):
            raise OSMImportError("Region, snapshot, source and attribution are required")
        if "openstreetmap" not in self.attribution.lower():
            raise OSMImportError("Include OpenStreetMap contributor attribution")


@dataclass(frozen=True)
class ImportedMap:
    graph: RoadGraph
    coordinates: dict[str, tuple[float, float]]
    metadata: dict[str, str | int]


def _tags(element: ET.Element) -> dict[str, str]:
    return {t.get("k", ""): t.get("v", "") for t in element.findall("tag")}


def _check_conditions(tags: dict[str, str], label: str) -> None:
    """Fail closed: no time-dependent legality without a clock + evaluator."""
    if any(CONDITIONAL.search(k) for k in tags):
        raise OSMImportError(f"{label}: conditional tags are unsupported")


def _haversine(p: tuple[float, float], q: tuple[float, float]) -> float:
    a, b = map(radians, p)
    c, d = map(radians, q)
    lat = c - a
    lon = d - b
    k = sin(lat / 2)**2 + cos(a) * cos(c) * sin(lon / 2)**2
    return 12_742_000 * asin(min(1.0, sqrt(max(0.0, k))))


def _estimated_speed(highway: str, maxspeed: str | None) -> float:
    default = DRIVING_SPEEDS.get(highway, 15.0)
    if not maxspeed:
        return default
    m = MAXSPEED.fullmatch(maxspeed.strip())
    if not m:
        return default
    speed = float(m.group(1)) * (1.609344 if m.group(2) == "mph" else 1.0)
    return min(default, speed) if isfinite(speed) and speed > 0 else default


def _road_access(tags: dict[str, str]) -> str | None:
    highway = tags.get("highway", "")
    if highway not in DRIVING_SPEEDS and highway not in UNCERTAIN_ROADS:
        return None
    # Specific car permission overrides general vehicle/access tags.
    for key in ("motorcar", "motor_vehicle", "vehicle", "access"):
        value = tags.get(key)
        if value is not None:
            if value in ALLOWED_VALUES:
                return "allowed"
            if value in BLOCKED_VALUES:
                return "prohibited"
            return "unknown"
    return "unknown" if highway in UNCERTAIN_ROADS else "allowed"


def _barrier_access(tags: dict[str, str]) -> str:
    kind = tags.get("barrier")
    if not kind:
        return "allowed"
    for key in ("motorcar", "motor_vehicle", "vehicle", "access"):
        value = tags.get(key)
        if value is not None:
            if value in BLOCKED_VALUES:
                return "prohibited"
            if value in ALLOWED_VALUES and kind not in BLOCKING_BARRIERS:
                return "allowed"
            return "unknown"
    if kind in BLOCKING_BARRIERS:
        return "prohibited"
    # Unrecognised physical barriers could block a vehicle; don't assume open.
    return "unknown"


def _combine_access(a: str, b: str) -> str:
    if "prohibited" in (a, b):
        return "prohibited"
    if "unknown" in (a, b):
        return "unknown"
    return "allowed"


def import_osm_xml(raw: bytes, *, provenance: Provenance) -> ImportedMap:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_INPUT_BYTES:
        raise OSMImportError("Expected nonempty OSM XML bytes within 6 MB prototype limit")
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise OSMImportError("DTD/entities are not permitted")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise OSMImportError("Invalid OSM XML") from exc
    if root.tag != "osm":
        raise OSMImportError("Expected an <osm> root element")
    objects = [element for element in root if element.tag in {"node", "way", "relation"}]
    if len(objects) > MAX_OBJECTS:
        raise OSMImportError("Prototype extract has too many OSM objects")

    coordinates: dict[str, tuple[float, float]] = {}
    barriers: dict[str, str] = {}
    ways: dict[str, tuple[list[str], dict[str, str]]] = {}
    relations: list[ET.Element] = []
    for element in objects:
        ident = element.get("id", "")
        if not ident or not ident.lstrip("-").isdigit():
            raise OSMImportError("OSM objects require valid numeric IDs")
        if element.tag == "node":
            node = f"osm:{ident}"
            if node in coordinates:
                raise OSMImportError("Duplicate OSM node")
            try:
                lat, lon = float(element.attrib["lat"]), float(element.attrib["lon"])
            except (KeyError, ValueError) as exc:
                raise OSMImportError(f"{node}: missing/invalid coordinates") from exc
            if not isfinite(lat) or not isfinite(lon) or abs(lat) > 90 or abs(lon) > 180:
                raise OSMImportError("Coordinates outside Earth bounds")
            tags = _tags(element)
            _check_conditions(tags, f"node {ident}")
            coordinates[node] = (lat, lon)
            barriers[node] = _barrier_access(tags)
        elif element.tag == "way":
            if ident in ways:
                raise OSMImportError("Duplicate OSM way")
            tags = _tags(element)
            _check_conditions(tags, f"way {ident}")
            refs = [f"osm:{n.get('ref')}" for n in element.findall("nd")]
            if not refs or any(x == "osm:None" for x in refs):
                raise OSMImportError("Way has missing node references")
            ways[ident] = (refs, tags)
        else:
            relations.append(element)

    edges: list[RoadEdge] = []
    # Segments with a barrier *at either endpoint* remain inaccessible/uncertain.
    # This is conservative and may block an adjacent leg too.
    for way_id, (refs, tags) in sorted(ways.items(), key=lambda item: int(item[0])):
        access = _road_access(tags)
        if access is None:
            continue
        oneway = tags.get("oneway", "").lower()
        if not oneway and tags.get("junction") in ("roundabout", "circular"):
            oneway = "yes"
        if oneway not in ("", "no", "0", "false", "yes", "1", "true", "-1", "reverse"):
            raise OSMImportError(f"way {way_id}: unsupported oneway value {oneway}")
        direction = -1 if oneway in ("-1", "reverse") else 1
        speed = _estimated_speed(tags.get("highway", ""), tags.get("maxspeed"))
        for i, (src, dst) in enumerate(zip(refs, refs[1:])):
            if src not in coordinates or dst not in coordinates:
                raise OSMImportError(f"way {way_id}: missing node coordinate")
            length = _haversine(coordinates[src], coordinates[dst])
            if length < 0.01:
                raise OSMImportError(f"way {way_id}: degenerate road segment")
            actual = _combine_access(access, _combine_access(barriers[src], barriers[dst]))
            if direction == 1:
                edges.append(RoadEdge(f"w:{way_id}:{i}:f", src, dst, length, speed, actual))
            if direction == -1 or oneway in ("", "no", "0", "false"):
                edges.append(RoadEdge(f"w:{way_id}:{i}:r", dst, src, length, speed, actual))
    if not edges:
        raise OSMImportError("No motorcar graph edges extracted")
    # Directed manoeuvres at each via node, mapping way IDs to concrete edges.
    turns: set[tuple[str, str]] = set()
    outgoing: dict[str, list[RoadEdge]] = {}
    incoming: dict[tuple[str, str], list[RoadEdge]] = {}
    leaving: dict[tuple[str, str], list[RoadEdge]] = {}
    for edge in edges:
        outgoing.setdefault(edge.source, []).append(edge)
        way_id = edge.edge_id.split(":")[1]
        incoming.setdefault((way_id, edge.target), []).append(edge)
        leaving.setdefault((way_id, edge.source), []).append(edge)
    for relation in relations:
        tags = _tags(relation)
        if tags.get("type") != "restriction":
            continue
        _check_conditions(tags, f"relation {relation.get('id')}")
        if "motorcar" in {v.strip() for v in tags.get("except", "").replace(",", ";").split(";")}:
            continue
        # Alternative mode-specific restriction tags are not assumed to apply to cars.
        rule = tags.get("restriction:motorcar", tags.get("restriction:motor_vehicle",
                    tags.get("restriction", "")))
        if not rule:
            raise OSMImportError("Unrecognised restriction relation requires review")
        if not (rule.startswith("no_") or rule.startswith("only_")):
            raise OSMImportError(f"Unsupported turn restriction: {rule}")
        members = relation.findall("member")
        frm = [m.get("ref") for m in members if m.get("role") == "from" and m.get("type") == "way"]
        to = [m.get("ref") for m in members if m.get("role") == "to" and m.get("type") == "way"]
        via = [m.get("ref") for m in members if m.get("role") == "via" and m.get("type") == "node"]
        if len(frm) != 1 or len(to) != 1 or len(via) != 1 or len(members) != 3:
            raise OSMImportError("Only single via-node turn restrictions are supported")
        node = f"osm:{via[0]}"
        arrivals = incoming.get((frm[0], node), [])
        departures = leaving.get((to[0], node), [])
        if not arrivals or not departures:
            raise OSMImportError("Restriction references a missing/non-drivable manoeuvre")
        for arrival in arrivals:
            if rule.startswith("no_"):
                for departure in departures:
                    turns.add((arrival.edge_id, departure.edge_id))
            else:
                permitted = {departure.edge_id for departure in departures}
                for other in outgoing.get(node, []):
                    if other.edge_id not in permitted:
                        turns.add((arrival.edge_id, other.edge_id))
    graph = RoadGraph(coordinates.keys(), edges, turns)
    return ImportedMap(
        graph=graph,
        coordinates=coordinates,
        metadata={
            "source_sha256": sha256(raw).hexdigest(),
            "source": provenance.source,
            "snapshot": provenance.snapshot,
            "region": provenance.region,
            "attribution": provenance.attribution,
            "vertices": len(graph.vertices),
            "directed_edges": len(graph.edges),
            "prohibited_turn_pairs": len(graph.prohibited_turns),
            "limitations": "prototype-no-conditional-via-way-or-real-world-legality-claims",
        },
    )
