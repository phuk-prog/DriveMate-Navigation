"""Bounded OSM XML importer for an auditable *prototype* directed motorcar graph.

Supported: public-driving highway classes, one-way (+/-), roundabout direction,
explicit motorcar access, source geometry, maxspeed-based *cost estimate*,
node-via and single via-way turn restrictions ('no_' and 'only_', no_entry/no_exit),
and simple blocking barriers.

Car-relevant *:conditional rules are not evaluated: the affected direction or
turn is withheld (fail closed per object) instead of rejecting the whole
extract. Unparseable restriction structures still reject the extract; see README.
Never treat this importer as road-legal navigation without independent checks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from math import asin, cos, isfinite, radians, sin, sqrt
import re
from types import MappingProxyType
from typing import Mapping
import xml.etree.ElementTree as ET

from engine import RoadEdge, RoadGraph

MAX_INPUT_BYTES = 32_000_000
# Bounded for auditable research clips (about 1 km around a junction), NOT whole UK extracts.
MAX_OBJECTS = 300_000
DRIVING_SPEEDS = {
    "motorway": 95, "trunk": 80, "primary": 55, "secondary": 48,
    "tertiary": 40, "unclassified": 35, "residential": 30,
    "living_street": 12, "motorway_link": 45, "trunk_link": 45,
    "primary_link": 35, "secondary_link": 30, "tertiary_link": 25,
}
UNCERTAIN_ROADS = {"service", "track"}
ALLOWED_VALUES = {"yes", "designated", "permissive"}
BLOCKED_VALUES = {"no"}
CONTEXTUAL_VALUES = {"private", "agricultural", "forestry", "delivery",
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
class JourneyAccessContext:
    """Caller-asserted permission, scoped to exact source bytes and destination.

    Permission is not inferred from an OSM tag. Never persist a journey view as
    the general map or claim this assertion independently proves road law.
    """
    source_sha256: str
    authorized_way_ids: frozenset[str] = frozenset()
    authorized_node_ids: frozenset[str] = frozenset()
    destination_way_ids: frozenset[str] = frozenset()
    destination_node: str | None = None

    def __post_init__(self):
        if type(self.source_sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", self.source_sha256) is None:
            raise OSMImportError("Access context requires exact source SHA-256")
        for ids in (self.authorized_way_ids, self.authorized_node_ids, self.destination_way_ids):
            if type(ids) is not frozenset or len(ids)>1000 or any(
                    type(x) is not str or re.fullmatch(r"[1-9][0-9]{0,18}",x) is None for x in ids):
                raise OSMImportError("Bounded immutable source IDs required for permission")
        if self.destination_way_ids and self.destination_node is None:
            raise OSMImportError("Qualifying destination ways require an actual destination")
        if self.destination_node is not None and (type(self.destination_node) is not str or
                re.fullmatch(r"osm:[1-9][0-9]{0,18}",self.destination_node) is None):
            raise OSMImportError("Context destination must identify an OSM node")


@dataclass(frozen=True)
class ImportedMap:
    graph: RoadGraph
    coordinates: dict[str, tuple[float, float]]
    metadata: dict[str, str | int]
    access_requirements: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "access_requirements", MappingProxyType(dict(self.access_requirements)))


def _tags(element: ET.Element) -> dict[str, str]:
    return {t.get("k", ""): t.get("v", "") for t in element.findall("tag")}


ACCESS_CONDITIONAL_KEYS = re.compile(
    r"^(?:access|vehicle|motor_vehicle|motorcar)(?::(?:forward|backward))?:conditional$")


def _conditional_restrictions(tags: dict[str, str]) -> dict[str, bool]:
    """Which travel directions a car-relevant *:conditional tag could close.

    No clock or evaluator is applied, so a condition that can restrict a car
    (access no/private/... at some times, or a time-limited one-way) makes the
    affected direction 'unknown' (never routed) instead of rejecting the whole
    map. A condition that only ever *grants* access leaves the stricter
    unconditional value in force. Unrelated conditionals (maxspeed, parking,
    lanes...) do not affect road legality here and are ignored.
    """
    closes = {"forward": False, "backward": False}
    for key, value in tags.items():
        if not CONDITIONAL.search(key):
            continue
        outcomes = {part.split("@")[0].strip().lower() for part in value.split(";") if "@" in part}
        if ACCESS_CONDITIONAL_KEYS.match(key):
            if not outcomes or outcomes - ALLOWED_VALUES:
                for direction in closes:
                    if f":{direction}:" in key or (":forward:" not in key and ":backward:" not in key):
                        closes[direction] = True
        elif key == "oneway:conditional":
            if not outcomes or outcomes & {"yes", "1", "true"}:
                closes["backward"] = True
            if not outcomes or outcomes & {"-1", "reverse"}:
                closes["forward"] = True
    return closes


def _check_conditions(tags: dict[str, str], label: str) -> None:
    """Retained for callers that still require an unconditional source object."""
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


def _selected_access(tags: dict[str, str], direction: str | None = None):
    for mode in ("motorcar", "motor_vehicle", "vehicle", "access"):
        for key in ((f"{mode}:{direction}", mode) if direction else (mode,)):
            if key in tags:
                return tags[key]
    return None


def _requirements(tags, scope, ident, direction=None):
    value = _selected_access(tags, direction)
    return (f"{scope}:{ident}:{value}",) if value in CONTEXTUAL_VALUES else ()


def _road_access(tags: dict[str, str], direction: str | None = None, *,
                 authorized: bool = False, qualifying_destination: bool = False) -> str | None:
    highway = tags.get("highway", "")
    if highway not in DRIVING_SPEEDS and highway not in UNCERTAIN_ROADS:
        return None
    value = _selected_access(tags, direction)
    if value in ALLOWED_VALUES:
        return "allowed"
    if value in BLOCKED_VALUES:
        return "prohibited"
    if value == "private" and authorized:
        return "allowed"
    if value == "destination" and qualifying_destination:
        return "allowed"
    if value is not None:
        return "unknown"
    return "unknown" if highway in UNCERTAIN_ROADS else "allowed"


def _uncertain_roads_required_by_only_turns(ways, relations) -> frozenset[str]:
    """Untagged service/track ways that a car only_* turn restriction sends cars onto.

    An only_* rule from a road open to cars says the restricted movement onto this
    road is the one cars must make, so the mapper treats it as usable by cars. Only
    roads with no access tag of any kind qualify; any access value (private, no,
    destination...), a conditional rule, a no_* rule or a barrier is never overridden.
    """
    opened: set[str] = set()
    for relation in relations:
        tags = _tags(relation)
        if tags.get("type") != "restriction" or tags.get("restriction:conditional"):
            continue
        exempt = {v.strip() for v in tags.get("except", "").replace(",", ";").split(";")}
        rule = tags.get("restriction:motorcar", tags.get("restriction:motor_vehicle", tags.get("restriction", "")))
        if not rule.startswith("only_") or exempt & {"motorcar", "motor_vehicle", "vehicle"}:
            continue
        members = relation.findall("member")
        frm = [m.get("ref") for m in members if m.get("role") == "from" and m.get("type") == "way"]
        to = [m.get("ref") for m in members if m.get("role") == "to" and m.get("type") == "way"]
        if len(frm) != 1 or len(to) != 1 or frm[0] not in ways or to[0] not in ways:
            continue
        from_tags, to_tags = ways[frm[0]][1], ways[to[0]][1]
        if _road_access(from_tags) != "allowed" or any(_conditional_restrictions(from_tags).values()):
            continue
        untagged = all(_selected_access(to_tags, d) is None for d in ("forward", "backward"))
        if (to_tags.get("highway") in UNCERTAIN_ROADS and untagged
                and not any(_conditional_restrictions(to_tags).values())):
            opened.add(to[0])
    return frozenset(opened)

def _barrier_access(tags: dict[str, str], *, authorized: bool = False,
                    qualifying_destination: bool = False) -> str:
    kind = tags.get("barrier")
    if not kind:
        return "allowed"
    for key in ("motorcar", "motor_vehicle", "vehicle", "access"):
        value = tags.get(key)
        if value is not None:
            if value in BLOCKED_VALUES:
                return "prohibited"
            permitted = (value in ALLOWED_VALUES or (value == "private" and authorized)
                         or (value == "destination" and qualifying_destination))
            if permitted and kind not in BLOCKING_BARRIERS:
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


def import_osm_xml(raw: bytes, *, provenance: Provenance,
                   access_context: JourneyAccessContext | None = None) -> ImportedMap:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_INPUT_BYTES:
        raise OSMImportError("Expected nonempty OSM XML bytes within 32 MB research limit")
    source_hash = sha256(raw).hexdigest()
    if access_context is not None and (not isinstance(access_context, JourneyAccessContext)
            or access_context.source_sha256 != source_hash):
        raise OSMImportError("Access context does not match this source snapshot")
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
    node_context: dict[str, tuple[str, ...]] = {}
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
            coordinates[node] = (lat, lon)
            node_conditional = tags.get("barrier") and any(_conditional_restrictions(tags).values())
            barriers[node] = "unknown" if node_conditional else _barrier_access(tags,
                authorized=bool(access_context and ident in access_context.authorized_node_ids),
                qualifying_destination=bool(access_context and access_context.destination_way_ids
                    and access_context.destination_node == node))
            node_context[node] = _requirements(tags,"node",ident) if tags.get("barrier") else ()
        elif element.tag == "way":
            if ident in ways:
                raise OSMImportError("Duplicate OSM way")
            tags = _tags(element)
            refs = [f"osm:{n.get('ref')}" for n in element.findall("nd")]
            if not refs or any(x == "osm:None" for x in refs):
                raise OSMImportError("Way has missing node references")
            ways[ident] = (refs, tags)
        else:
            relations.append(element)

    if access_context is not None:
        if (not (access_context.authorized_way_ids | access_context.destination_way_ids) <= ways.keys() or
                not {f"osm:{n}" for n in access_context.authorized_node_ids} <= coordinates.keys() or
                (access_context.destination_node is not None and access_context.destination_node not in coordinates)):
            raise OSMImportError("Access context references absent source objects")
        if any(access_context.destination_node not in ways[wid][0]
               for wid in access_context.destination_way_ids):
            raise OSMImportError("Qualifying destination must be on each declared destination way")
    access_requirements: dict[str, tuple[str, ...]] = {}
    edges: list[RoadEdge] = []
    conditional_ways = 0
    opened_by_only = _uncertain_roads_required_by_only_turns(ways, relations)
    # Segments with a barrier *at either endpoint* remain inaccessible/uncertain.
    # This is conservative and may block an adjacent leg too.
    for way_id, (refs, tags) in sorted(ways.items(), key=lambda item: int(item[0])):
        access = _road_access(tags)
        if access is None:
            continue
        oneway = tags.get("oneway", "").lower()
        if not oneway and tags.get("junction") in ("roundabout", "circular"):
            oneway = "yes"
        reversible = oneway == "reversible"  # direction changes over time: neither direction assumed
        if oneway == "alternating":  # signal-controlled single lane: both directions, in turn
            oneway = "no"
        elif reversible:
            oneway = "no"
        if oneway not in ("", "no", "0", "false", "yes", "1", "true", "-1", "reverse"):
            raise OSMImportError(f"way {way_id}: unsupported oneway value {oneway}")
        direction = -1 if oneway in ("-1", "reverse") else 1
        conditional_closes = _conditional_restrictions(tags)
        if reversible:
            conditional_closes = {"forward": True, "backward": True}
        if any(conditional_closes.values()):
            conditional_ways += 1
        speed = _estimated_speed(tags.get("highway", ""), tags.get("maxspeed"))
        authorized = bool(access_context and way_id in access_context.authorized_way_ids)
        destination = bool(access_context and way_id in access_context.destination_way_ids
                           and access_context.destination_node in refs)
        for i, (src, dst) in enumerate(zip(refs, refs[1:])):
            if src not in coordinates or dst not in coordinates:
                raise OSMImportError(f"way {way_id}: missing node coordinate")
            length = _haversine(coordinates[src], coordinates[dst])
            if length < 0.01:
                raise OSMImportError(f"way {way_id}: degenerate road segment")
            physical = _combine_access(barriers[src], barriers[dst])
            node_requirements = node_context[src] + node_context[dst]
            if direction == 1:
                road = _road_access(tags, "forward", authorized=authorized, qualifying_destination=destination)
                if road == "unknown" and way_id in opened_by_only:
                    road = "allowed"
                actual = _combine_access(road, physical)
                if conditional_closes["forward"]:
                    actual = _combine_access(actual, "unknown")
                edges.append(RoadEdge(f"w:{way_id}:{i}:f", src, dst, length, speed, actual))
                conditions = _requirements(tags,"way",way_id,"forward") + node_requirements
                if conditions: access_requirements[f"w:{way_id}:{i}:f"] = conditions
            if direction == -1 or oneway in ("", "no", "0", "false"):
                road = _road_access(tags, "backward", authorized=authorized, qualifying_destination=destination)
                if road == "unknown" and way_id in opened_by_only:
                    road = "allowed"
                actual = _combine_access(road, physical)
                if conditional_closes["backward"]:
                    actual = _combine_access(actual, "unknown")
                edges.append(RoadEdge(f"w:{way_id}:{i}:r", dst, src, length, speed, actual))
                conditions = _requirements(tags,"way",way_id,"backward") + node_requirements
                if conditions: access_requirements[f"w:{way_id}:{i}:r"] = conditions
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
    sequences: set[tuple[str, ...]] = set()
    skipped: dict[str, int] = {}

    def skip(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    def block_into_via(frm: list[str], via_nodes: list[str], via_ways: list[str], reason: str) -> None:
        """Fail safe per object: ban every move from the restricted road into the via
        structure (may withhold legal moves, never permits a banned one)."""
        touch = set(via_nodes) | {n.removeprefix("osm:") for w in via_ways if w in ways for n in ways[w][0]}
        for f in frm:
            for n in touch:
                for arrival in incoming.get((f, f"osm:{n}"), []):
                    for other in outgoing.get(f"osm:{n}", []):
                        turns.add((arrival.edge_id, other.edge_id))
        skip(reason)

    def via_way_chain(via_way: str, start: str, end: str) -> list[RoadEdge] | None:
        """Edges travelling along `via_way` from node `start` to node `end`."""
        chain: list[RoadEdge] = []
        node = start
        while node != end:
            step = [e for e in leaving.get((via_way, node), []) if e.edge_id not in {c.edge_id for c in chain}]
            step = [e for e in step if not chain or e.target != chain[-1].source]
            if len(step) != 1:
                return None
            chain.append(step[0])
            node = step[0].target
            if len(chain) > 500:
                return None
        return chain

    for relation in relations:
        tags = _tags(relation)
        if tags.get("type") != "restriction":
            continue
        exempt = {v.strip() for v in tags.get("except", "").replace(",", ";").split(";")}
        if exempt & {"motorcar", "motor_vehicle", "vehicle"}:
            skip("cars_exempt")
            continue
        # Only restriction keys that apply to cars; mode-specific ones (bus, hgv...) do not.
        rule = tags.get("restriction:motorcar", tags.get("restriction:motor_vehicle",
                    tags.get("restriction", "")))
        conditional = tags.get("restriction:conditional", "")
        if not rule and conditional:
            # Time-limited ban: without an evaluator it is applied at all times
            # (safe: may withhold a legal turn, never permits an illegal one).
            rule = conditional.split("@")[0].strip()
            skip("conditional_applied_always")
        if not rule:
            skip("not_a_car_restriction")
            continue
        members = relation.findall("member")
        frm = [m.get("ref") for m in members if m.get("role") == "from" and m.get("type") == "way"]
        to = [m.get("ref") for m in members if m.get("role") == "to" and m.get("type") == "way"]
        via_nodes = [m.get("ref") for m in members if m.get("role") == "via" and m.get("type") == "node"]
        via_ways = [m.get("ref") for m in members if m.get("role") == "via" and m.get("type") == "way"]
        frm = [f for f in frm if f in ways]
        to_present = [t for t in to if t in ways]
        if not frm or not (via_nodes or via_ways):
            # Clipped at the extract edge: the restricted movement cannot start inside it.
            skip("member_outside_extract")
            continue
        if via_nodes and via_ways or len(via_nodes) > 1:
            # Uninterpretable structure: blocked per object, not fatal for the map.
            block_into_via(frm, via_nodes, via_ways, "uninterpretable_structure_blocked")
            continue
        if not (rule.startswith("no_") or rule.startswith("only_")):
            # Unknown rule value (typo or unsupported scheme): blocked per object like an
            # uninterpretable structure; it no longer rejects the whole map (owner-approved).
            block_into_via(frm, via_nodes, via_ways, "unsupported_rule_blocked")
            continue
        if not to_present and rule.startswith("no_"):
            skip("member_outside_extract")
            continue
        to = to_present
        if (len(frm) > 1 or len(to) > 1) and (via_ways or rule.startswith("only_")):
            # Several from/to ways are only interpretable for via-node no_ rules; others
            # are blocked per object instead of rejecting the whole map (owner-approved).
            block_into_via(frm, via_nodes, via_ways, "several_from_to_blocked")
            continue
        if via_ways:
            if any(w not in ways for w in via_ways):
                skip("member_outside_extract")
                continue
            # Order the via ways end to end, starting where the from way joins them.
            f_ends = {ways[frm[0]][0][0], ways[frm[0]][0][-1]}
            node_now = None
            for w in via_ways:
                joined = f_ends & {ways[w][0][0], ways[w][0][-1]}
                if joined:
                    node_now = joined.pop()
                    break
            # A wrongly mapped relation (members not joined end to end) is blocked per
            # object like an uninterpretable one; it no longer rejects the whole map
            # (owner-approved fix after ACCESS-001/ONEWAY-002 run 39039003647).
            if node_now is None:
                block_into_via(frm, via_nodes, via_ways, "disconnected_via_way_blocked")
                continue
            a_node = node_now
            remaining = list(via_ways)
            chain: list[RoadEdge] = []
            disconnected = False
            while remaining:
                nxt = [w for w in remaining if node_now in (ways[w][0][0], ways[w][0][-1])]
                if len(nxt) != 1:
                    disconnected = True
                    break
                w = nxt[0]
                remaining.remove(w)
                end = ways[w][0][-1] if ways[w][0][0] == node_now else ways[w][0][0]
                part = via_way_chain(w, node_now, end)
                if part is None:
                    chain = []
                    break
                chain.extend(part)
                node_now = end
            if disconnected:
                block_into_via(frm, via_nodes, via_ways, "disconnected_via_way_blocked")
                continue
            b_node = node_now
            arrivals = incoming.get((frm[0], a_node), [])
            if not chain or not arrivals:
                skip("no_car_movement")
                continue
            if to and b_node not in set(ways[to[0]][0]):
                block_into_via(frm, via_nodes, via_ways, "disconnected_via_way_blocked")
                continue
            exits = leaving.get((to[0], b_node), []) if to else []
            if rule.startswith("only_"):
                exits = [o for o in outgoing.get(b_node, []) if o.edge_id not in {e.edge_id for e in exits}]
            for arrival in arrivals:
                for exit_edge in exits:
                    sequences.add((arrival.edge_id, *(c.edge_id for c in chain), exit_edge.edge_id))
            continue
        node = f"osm:{via_nodes[0]}"
        if node not in coordinates:
            skip("member_outside_extract")
            continue
        arrivals = [e for f in frm for e in incoming.get((f, node), [])]
        departures = [e for t in to for e in leaving.get((t, node), [])]
        if not arrivals:
            skip("no_car_movement")  # from way absent or not drivable towards the via node
            continue
        for arrival in arrivals:
            if rule.startswith("no_"):
                for departure in departures:
                    turns.add((arrival.edge_id, departure.edge_id))
            else:
                # Every other exit is banned; if the only permitted exit is absent
                # or not drivable, no exit remains (fail safe).
                permitted = {departure.edge_id for departure in departures}
                for other in outgoing.get(node, []):
                    if other.edge_id not in permitted:
                        turns.add((arrival.edge_id, other.edge_id))
    graph = RoadGraph(coordinates.keys(), edges, turns,
        journey_destination=access_context.destination_node if access_context else None,
        prohibited_sequences=sequences)
    return ImportedMap(
        graph=graph,
        coordinates=coordinates,
        access_requirements=access_requirements,
        metadata={
            "source_sha256": source_hash,
            "journey_scoped_access": access_context is not None,
            "source": provenance.source,
            "snapshot": provenance.snapshot,
            "region": provenance.region,
            "attribution": provenance.attribution,
            "vertices": len(graph.vertices),
            "directed_edges": len(graph.edges),
            "prohibited_turn_pairs": len(graph.prohibited_turns),
            "prohibited_turn_sequences": len(graph.prohibited_sequences),
            "restrictions_not_applied": dict(sorted(skipped.items())),
            "conditional_ways_withheld": conditional_ways,
            "uncertain_roads_opened_by_only_turn": len(opened_by_only),
            "limitations": "research-conditional-withheld-not-evaluated-no-real-world-legality-claims",
        },
    )
