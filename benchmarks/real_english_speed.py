"""Measured warm HTTP routing on public English road geometry, never synthetic."""
import argparse
from contextlib import ExitStack
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
from statistics import median
from threading import Thread
from time import perf_counter_ns
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

from benchmarks.expanded_comparison import graphhopper
from engine.reconciled import prepare_navigation
from map_data import Provenance, import_osm_xml

LABELS = ("drivemate-python", "graphhopper", "osrm-mld", "osrm-ch")


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[math.ceil(fraction * len(ordered)) - 1]


def road_cases(prepared, graph, *, maximum=18):
    """Deterministic graph walks; never any user origin or recorded journey."""
    chosen = []
    vertices = sorted(v for v, edges in graph.adjacency.items()
                      if any(e.access == "allowed" for e in edges))
    step = max(1, len(vertices) // (maximum * 10))
    seen = set()
    for origin in vertices[::step]:
        node = origin
        visited = {node}
        metres = 0.0
        for _ in range(28):
            edges = [e for e in graph.adjacency[node]
                     if e.access == "allowed" and e.target not in visited]
            if not edges:
                break
            e = sorted(edges, key=lambda item: item.edge_id)[0]
            node = e.target
            visited.add(node)
            metres += e.length_m
            if metres >= 250.0:
                break
        if metres < 250 or node == origin:
            continue
        try:
            route = prepared.route(origin, node)
            if not route.edge_ids:
                continue
        except (ValueError, KeyError):
            continue
        pair = (origin, node)
        if pair in seen:
            continue
        seen.add(pair)
        chosen.append({"id": "england-%03d" % len(chosen), "source": origin, "target": node})
        if len(chosen) >= maximum:
            break
    return chosen


def start_candidate(prepared):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            try:
                query = parse_qs(urlparse(self.path).query)
                start, end = query["from"][0], query["to"][0]
                route = prepared.route(start, end)
                position = start
                points = [[prepared.coordinates[position][1], prepared.coordinates[position][0]]]
                for edge_id in route.edge_ids:
                    edge = prepared.source_edges[edge_id]
                    if edge.source != position:
                        raise ValueError("Discontinuous candidate route")
                    position = edge.target
                    points.append([prepared.coordinates[position][1], prepared.coordinates[position][0]])
                if position != end:
                    raise ValueError("Candidate returned wrong destination")
                payload = json.dumps({"ok": True, "coordinates": points}, separators=(",", ":")).encode()
                code = 200
            except (ValueError, KeyError, TypeError):
                payload = b'{"ok":false}'
                code = 422
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def query(engine, case, coordinates, candidate_port, gh_port):
    a, b = coordinates[case["source"]], coordinates[case["target"]]
    if engine == "drivemate-python":
        url = "http://127.0.0.1:%d/route?" % candidate_port + urlencode(
            {"from": case["source"], "to": case["target"]})
    elif engine == "graphhopper":
        if gh_port is None:
            raise ValueError("GraphHopper unavailable")
        url = "http://127.0.0.1:%d/route?" % gh_port + urlencode([
            ("point", "%s,%s" % a), ("point", "%s,%s" % b),
            ("profile", "car"), ("points_encoded", "false"), ("instructions", "false")])
    else:
        port = 5000 if engine == "osrm-mld" else 5001
        url = ("http://127.0.0.1:%d/route/v1/driving/" % port +
               "%s,%s;%s,%s?overview=full&geometries=geojson" %
               (a[1], a[0], b[1], b[0]))
    with urlopen(url, timeout=12) as response:
        raw = json.load(response)
    if engine == "drivemate-python":
        if not raw.get("ok"):
            raise ValueError("No candidate route")
        points = raw.get("coordinates")
    elif engine == "graphhopper":
        paths = raw.get("paths") or []
        points = paths[0].get("points", {}).get("coordinates") if paths else None
    else:
        routes = raw.get("routes") or []
        points = routes[0].get("geometry", {}).get("coordinates") if routes else None
    if not points or len(points) < 2:
        raise ValueError("Missing route geometry")
    def metres(u, v):
        return math.hypot((u[0] - v[1]) * 111195,
                          (u[1] - v[0]) * 111195 * math.cos(math.radians(v[0])))
    if metres(points[0], a) > 12 or metres(points[-1], b) > 12:
        raise ValueError("Endpoint snapping exceeds 12m; incomparable")
    if any(len(pt) != 2 or not all(math.isfinite(x) for x in pt) for pt in points):
        raise ValueError("Invalid route geometry")
    if sum(math.hypot((v[0] - u[0]) * 66000, (v[1] - u[1]) * 111195)
           for u, v in zip(points, points[1:])) < 100:
        raise ValueError("Unexpectedly short or incomplete route geometry")
    # Complete legality and orientation need an independent OSM reference judge.


def run(raw, jar, repeat, maximum, snapshot, use_osrm):
    imported = import_osm_xml(raw, provenance=Provenance(
        "Greater Manchester, England", snapshot,
        "Geofabrik historic public OSM PBF", "© OpenStreetMap contributors (ODbL 1.0)"))
    prepared = prepare_navigation(imported.graph, imported.coordinates)
    cases = road_cases(prepared, imported.graph, maximum=maximum)
    if len(cases) < 5:
        raise ValueError("Insufficient routable real-road cases; do not substitute synthetic roads")
    engines = ["drivemate-python", "graphhopper"]
    if use_osrm:
        engines += ["osrm-mld", "osrm-ch"]
    samples = {e: [] for e in engines}
    failures = {e: [] for e in engines}
    with ExitStack() as stack:
        gh_port = stack.enter_context(graphhopper(jar, {"osm": raw}, Path("results/real-england/graphhopper")))
        server, thread = start_candidate(prepared)
        stack.callback(lambda: (server.shutdown(), server.server_close(), thread.join(timeout=3)))
        for repetition in range(-3, repeat):
            for case in cases:
                ordered = engines if repetition % 2 else list(reversed(engines))
                for engine in ordered:
                    if repetition >= 0 and any(x["case"] == case["id"] for x in failures[engine]):
                        continue
                    try:
                        start = perf_counter_ns()
                        query(engine, case, imported.coordinates, server.server_port, gh_port)
                        elapsed = (perf_counter_ns() - start) / 1_000_000
                        if repetition >= 0:
                            samples[engine].append({"case": case["id"], "repeat": repetition,
                                                    "milliseconds": elapsed})
                    except (OSError, KeyError, ValueError, TypeError, IndexError) as exc:
                        if repetition >= 0:
                            failures[engine].append({"case": case["id"], "reason": str(exc)[:160]})
    expected = repeat * len(cases)
    summary = {}
    for engine in engines:
        values = [x["milliseconds"] for x in samples[engine]]
        summary[engine] = {
            "passed_requests": len(values), "total_requests": expected,
            "failures": len(failures[engine]),
            "complete": len(values) == expected and not failures[engine],
            "median_ms": median(values) if values else None,
            "p95_ms": percentile(values, .95) if values else None,
            "p99_ms": percentile(values, .99) if values else None,
            "max_ms": max(values) if values else None,
        }
    eligible = [e for e in engines if summary[e]["complete"]]
    ranked = sorted(eligible, key=lambda e: summary[e]["p95_ms"])
    return {
        "category": "real-English-roads-warm-http-speed",
        "source": "Geofabrik Greater Manchester historic public PBF",
        "source_snapshot": snapshot, "source_xml_sha256": sha256(raw).hexdigest(),
        "attribution": "© OpenStreetMap contributors, ODbL 1.0",
        "road_graph_vertices": len(imported.graph.vertices),
        "road_graph_edges": len(imported.graph.edges),
        "cases": [c["id"] for c in cases], "repeats": repeat,
        "warmups": 3, "implementations": summary, "failures": failures,
        "samples": samples,
        "speed_ranks_complete_only": [
            {"rank": i + 1, "engine": e} for i, e in enumerate(ranked)],
        "overall_navigation_rank": None,
        "external_route_legality_verified": False,
        "limitations": [
            "Public OSM road topology, not independent current legal-access verification.",
            "DriveMate is the prepared Python research router, not Android native routing.",
            "All measured services use warm local HTTP; distinct algorithms and costing.",
            "Endpoints, finite polyline and minimum returned distance are checked; full external route legality remains unverified.",
            "Only endpoint/shape-validated response-time ranks; not independently proved legal-route-speed ranks.",
            "No device battery, regional UK map, traffic or mobile benchmark claim.",
            "No personal routes or GPS logs; scenario endpoints are derived solely from public map.",
        ],
    }


def preflight(raw, snapshot, maximum):
    imported = import_osm_xml(raw, provenance=Provenance(
        "Greater Manchester, England", snapshot,
        "Geofabrik historic public OSM PBF", "© OpenStreetMap contributors (ODbL 1.0)"))
    prepared = prepare_navigation(imported.graph, imported.coordinates)
    cases = road_cases(prepared, imported.graph, maximum=maximum)
    if len(cases) < 5:
        raise ValueError("Not enough routable public-English-road cases; stop without benchmarks")
    distances = []
    for case in cases:
        route = prepared.route(case["source"], case["target"])
        distances.append(round(sum(prepared.source_edges[e].length_m for e in route.edge_ids), 1))
    info = {"status": "preflight_passed", "real_road_cases": len(cases),
            "vertices": len(imported.graph.vertices), "edges": len(imported.graph.edges),
            "route_lengths_m": distances, "source_xml_sha256": sha256(raw).hexdigest(),
            "warning": "Public topology; real-world legal permission not independently verified"}
    out = Path("results/real-england")
    out.mkdir(parents=True, exist_ok=True)
    (out / "preflight.json").write_text(json.dumps(info, indent=2) + "\n")
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--graphhopper-jar", type=Path)
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--repeat", type=int, default=20)
    ap.add_argument("--cases", type=int, default=16)
    ap.add_argument("--osrm", action="store_true")
    args = ap.parse_args()
    if not 3 <= args.repeat <= 100 or not 5 <= args.cases <= 80:
        ap.error("Invalid bounded workload")
    if not args.input.resolve().is_relative_to(Path("results").resolve()):
        ap.error("Real maps must stay inside ignored results/")
    if args.input.stat().st_size > 6_000_000:
        ap.error("Map exceeds bounded prototype importer limit")
    out = Path("results/real-england")
    out.mkdir(parents=True, exist_ok=True)
    raw = args.input.read_bytes()
    if args.preflight:
        print(json.dumps(preflight(raw, args.snapshot, args.cases)))
        return
    if args.graphhopper_jar is None:
        ap.error("--graphhopper-jar required for full run")
    preflight(raw, args.snapshot, args.cases)
    result = run(raw, args.graphhopper_jar,
                 args.repeat, args.cases, args.snapshot, args.osrm)
    (out / "speed.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"implementations": result["implementations"],
                      "ranks": result["speed_ranks_complete_only"],
                      "cases": len(result["cases"])}))

if __name__ == "__main__":
    main()
