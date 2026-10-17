"""Check a route line from any source against DMN's map rules (owner-approved, 17 Oct 2026).

The app receives routes from TomTom, OSRM and Valhalla; the tests showed such engines
making banned turns, driving one-way roads the wrong way and quietly ending somewhere
other than the destination. This reads the route's line onto DMN's road pieces and
reports:

FAIL  WRONG_WAY (a one-way piece driven against its direction), CLOSED_ROAD (a piece
      cars may not use: bus gate, busway, pedestrian, "no cars", closed barrier) or
      BANNED_TURN (a mapped turn restriction between consecutive pieces);
WARN  ENDS_FAR_FROM_DESTINATION (more than end_tolerance_m) or UNCERTAIN_ACCESS
      (private/unknown access piece, allowed only at the ends of a journey);
OK    otherwise. Parts of the line that cannot be read onto a road piece are counted,
      never guessed. Map-derived, not independent UK road law.

destination_side() says whether the destination point is on the left or right of the
final road piece (UK: left is the kerb side).
"""
from __future__ import annotations

from collections import defaultdict
from math import atan2, cos, degrees, hypot, radians

from .routing import RoadGraph


def _xy(p, ref):
    k = 111_320 * cos(radians(ref[0]))
    return ((p[1] - ref[1]) * k, (p[0] - ref[0]) * 111_320)


def _bearing(a, b) -> float:
    x, y = _xy(b, a)
    return degrees(atan2(x, y)) % 360


def _angle(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def _seg_distance(p, a, b) -> float:
    ax, ay = _xy(a, p)
    bx, by = _xy(b, p)
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
    return hypot(ax + t * dx, ay + t * dy)


def _metres(a, b) -> float:
    x, y = _xy(b, a)
    return hypot(x, y)


class RouteChecker:
    def __init__(self, graph: RoadGraph, coordinates, *, snap_m: float = 6.0, sample_m: float = 5.0,
                 end_tolerance_m: float = 50.0):
        if not isinstance(graph, RoadGraph):
            raise TypeError("Requires a RoadGraph")
        for v in (snap_m, sample_m, end_tolerance_m):
            if not isinstance(v, (int, float)) or v <= 0:
                raise ValueError("Invalid checker distance")
        self.graph, self.coords = graph, coordinates
        self.snap_m, self.sample_m, self.end_tolerance_m = snap_m, sample_m, end_tolerance_m
        self.by_pair = {(e.source, e.target): e for e in graph.edges.values()}
        self.grid: dict[tuple[int, int], set[tuple[str, str]]] = defaultdict(set)
        for (u, v) in self.by_pair:
            pair = tuple(sorted((u, v)))
            for lat, lon in (coordinates[u], coordinates[v],
                             ((coordinates[u][0] + coordinates[v][0]) / 2, (coordinates[u][1] + coordinates[v][1]) / 2)):
                self.grid[(round(lat * 2000), round(lon * 2000))].add(pair)

    def _piece(self, point, heading):
        """The directed piece under the point travelled along heading, or None."""
        key = (round(point[0] * 2000), round(point[1] * 2000))
        near = set()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                near |= self.grid.get((key[0] + dy, key[1] + dx), set())
        best = None
        for u, v in near:
            d = _seg_distance(point, self.coords[u], self.coords[v])
            if d > self.snap_m:
                continue
            forward = _angle(_bearing(self.coords[u], self.coords[v]), heading) <= 45
            backward = _angle(_bearing(self.coords[v], self.coords[u]), heading) <= 45
            if not (forward or backward):
                continue
            directed = (u, v) if forward else (v, u)
            if best is None or d < best[0]:
                best = (d, directed)
        return None if best is None else best[1]

    def check(self, line, destination=None) -> dict:
        """line: [(lat, lon), ...] in travel order; destination: (lat, lon) asked for."""
        if len(line) < 2:
            return {"verdict": "WARN", "issues": [{"kind": "EMPTY_ROUTE"}], "unread_share": 1.0}
        samples = []
        for a, b in zip(line, line[1:]):
            length = _metres(a, b)
            if length < 0.5:
                continue
            heading = _bearing(a, b)
            steps = max(1, int(length // self.sample_m))
            for k in range(steps):
                f = (k + 0.5) / steps
                samples.append(((a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])), heading))
        issues, pieces, unread = [], [], 0
        for point, heading in samples:
            piece = self._piece(point, heading)
            if piece is None:
                unread += 1
            elif not pieces or pieces[-1] != piece:
                pieces.append(piece)
        history: tuple[str, ...] = ()
        previous = None
        for piece in pieces:
            edge = self.by_pair.get(piece)
            if edge is None:  # only the other direction exists: a one-way driven backwards
                issues.append({"kind": "WRONG_WAY", "piece": list(piece)})
                history, previous = (), None
                continue
            if edge.access == "prohibited":
                issues.append({"kind": "CLOSED_ROAD", "piece": list(piece)})
            elif edge.access == "unknown":
                issues.append({"kind": "UNCERTAIN_ACCESS", "piece": list(piece)})
            if previous is not None and previous.target == edge.source:
                tail = self.graph.transition(history, edge.edge_id)
                if tail is None:
                    issues.append({"kind": "BANNED_TURN", "from": previous.edge_id, "to": edge.edge_id})
                    tail = (edge.edge_id,)
                history = tail
            else:
                history = (edge.edge_id,)
            previous = edge
        if destination is not None and _metres(tuple(line[-1]), tuple(destination)) > self.end_tolerance_m:
            issues.append({"kind": "ENDS_FAR_FROM_DESTINATION",
                           "metres": round(_metres(tuple(line[-1]), tuple(destination)), 1)})
        kinds = {i["kind"] for i in issues}
        verdict = ("FAIL" if kinds & {"WRONG_WAY", "CLOSED_ROAD", "BANNED_TURN"} else
                   "WARN" if kinds else "OK")
        return {"verdict": verdict, "issues": issues, "pieces": len(pieces),
                "unread_share": round(unread / len(samples), 3) if samples else 1.0}


def destination_side(coordinates, edge, point) -> str:
    """'left' or 'right' of the final road piece (source -> target) for the destination point."""
    a, b = coordinates[edge.source], coordinates[edge.target]
    bx, by = _xy(b, a)
    px, py = _xy(point, a)
    cross = bx * py - by * px
    return "left" if cross > 0 else "right"
