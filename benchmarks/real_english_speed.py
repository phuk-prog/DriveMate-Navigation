"""Measured warm HTTP routing on public English road geometry, never synthetic."""
import argparse
from contextlib import ExitStack
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
import subprocess
from threading import Lock
from pathlib import Path
from statistics import median
from threading import Thread
from time import perf_counter_ns
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from benchmarks.cloud_reference import polyline6

from benchmarks.expanded_comparison import graphhopper
from navigation_core.core import Vehicle
from navigation_core.native_adapter import encode, NativeResult
from navigation_core.validation.oracle import validate_route
from engine.reconciled import prepare_navigation
from map_data import Provenance, import_osm_xml

LABELS = ("drivemate-native-cpp", "graphhopper", "osrm-mld", "osrm-ch", "valhalla", "openrouteservice")
NOT_YET_COMPARABLE = {
    "brouter": "Requires .rd5 routing data built from the exact pinned Geofabrik extract; weekly published tiles are a different snapshot.",
    "routingkit-ch": "Algorithm adapter currently consumes candidate-imported transition graphs rather than an independently imported same-map service.",
    "pgrouting": "Algorithm adapter currently consumes candidate-imported transitions and lacks a comparable persistent HTTP route service.",
}



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


class NativeRouterSession:
    """Persistent compiled C++ routing build, map loaded once per benchmark.

    This class never computes a route in Python; Python only marshals input,
    calls the native binary, and checks that its returned path is continuous.
    The compiled native core reports its own algorithm-only nanoseconds.
    """
    def __init__(self, prepared, binary):
        path = Path(binary)
        if not path.is_file():
            raise ValueError("Compiled native navigation router missing")
        self.prepared = prepared
        self._lock = Lock()
        self._process = subprocess.Popen([str(path.resolve()), "--stream"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1)
        try:
            initial = encode(prepared.graph, [], tuple(
                list(prepared.node_ids.values())[:1] +
                list(prepared.node_ids.values())[-1:]))
            self._process.stdin.write(initial)
            self._process.stdin.flush()
            ready = self._process.stdout.readline().strip()
            if not ready.startswith("READY "):
                raise ValueError("Compiled router failed map-ready protocol: " + ready[:120])
            self.native_map_prepare_ms = int(ready.split()[1]) / 1e6
        except (OSError, ValueError, BrokenPipeError):
            self.close()
            raise

    def route(self, start, end):
        p = self.prepared
        if start not in p.node_ids or end not in p.node_ids:
            raise ValueError("Unknown public-road endpoint")
        a, b = p.node_ids[start], p.node_ids[end]
        with self._lock:
            if self._process.poll() is not None:
                raise ValueError("Compiled native router exited")
            self._process.stdin.write(f"alt {a} {b} 0 -1 -1 0\n")
            self._process.stdin.flush()
            line = self._process.stdout.readline().strip()
        parts = line.split()
        if not parts or parts[0] != "FOUND" or len(parts) < 5:
            raise ValueError("Native route was absent or malformed")
        cost, expanded, elapsed_ns, count = map(int, parts[1:5])
        ids = tuple(map(int, parts[5:]))
        if count <= 0 or len(ids) != count or elapsed_ns < 0:
            raise ValueError("Native route result count/time invalid")
        result = NativeResult(ids, cost, expanded, elapsed_ns)
        # Independently verify graph connectivity, restrictions and cost.
        validate_route(p.graph, a, b, Vehicle("car"), (), result)
        names = p.road_names(ids)
        location = start
        points = [[p.coordinates[location][1], p.coordinates[location][0]]]
        for name in names:
            edge = p.source_edges[name]
            if edge.source != location or edge.access == "prohibited":
                raise ValueError("Native path traverses a disconnected/prohibited road")
            location = edge.target
            points.append([p.coordinates[location][1], p.coordinates[location][0]])
        if location != end:
            raise ValueError("Native path ends at wrong node")
        return {"ok": True, "coordinates": points,
                "native_core_ns": elapsed_ns, "native_expanded_states": expanded,
                "implementation": "compiled-cpp"}

    def close(self):
        proc = self._process
        if proc.poll() is None:
            try:
                proc.stdin.close()
                proc.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                proc.kill()
                proc.wait(timeout=5)
        for stream in (proc.stdout, proc.stderr):
            if stream is not None:
                stream.close()


def start_candidate(prepared, native_binary):
    native = NativeRouterSession(prepared, native_binary)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            try:
                query = parse_qs(urlparse(self.path).query)
                start, end = query["from"][0], query["to"][0]
                result = native.route(start, end)
                payload = json.dumps(result, separators=(",", ":")).encode()
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
    return server, thread, native


def query(engine, case, coordinates, candidate_port, gh_port):
    a, b = coordinates[case["source"]], coordinates[case["target"]]
    if engine == "drivemate-native-cpp":
        url = "http://127.0.0.1:%d/route?" % candidate_port + urlencode(
            {"from": case["source"], "to": case["target"]})
    elif engine == "graphhopper":
        if gh_port is None:
            raise ValueError("GraphHopper unavailable")
        url = "http://127.0.0.1:%d/route?" % gh_port + urlencode([
            ("point", "%s,%s" % a), ("point", "%s,%s" % b),
            ("profile", "car"), ("points_encoded", "false"), ("instructions", "false")])
    elif engine in ("osrm-mld", "osrm-ch"):
        port = 5000 if engine == "osrm-mld" else 5001
        url = ("http://127.0.0.1:%d/route/v1/driving/" % port +
               "%s,%s;%s,%s?overview=full&geometries=geojson" %
               (a[1], a[0], b[1], b[0]))
    elif engine == "valhalla":
        url = Request("http://127.0.0.1:8002/route",
            data=json.dumps({"locations":[{"lat":a[0],"lon":a[1]},
                {"lat":b[0],"lon":b[1]}],"costing":"auto",
                "shape_format":"polyline6"}, separators=(",", ":")).encode(),
            headers={"Content-Type":"application/json"}, method="POST")
    elif engine == "openrouteservice":
        url = Request("http://127.0.0.1:8080/ors/v2/directions/driving-car/geojson",
            data=json.dumps({"coordinates":[[a[1],a[0]], [b[1],b[0]]]},
                separators=(",", ":")).encode(),
            headers={"Content-Type":"application/json"}, method="POST")
    else:
        raise ValueError("Unsupported speed engine")
    with urlopen(url, timeout=12) as response:
        raw = json.load(response)
    if engine == "drivemate-native-cpp":
        if not raw.get("ok"):
            raise ValueError("No candidate route")
        points = raw.get("coordinates")
    elif engine == "graphhopper":
        paths = raw.get("paths") or []
        points = paths[0].get("points", {}).get("coordinates") if paths else None
    elif engine == "valhalla":
        legs = raw.get("trip", {}).get("legs") or []
        points = [[lon, lat] for leg in legs
                  for lat, lon in polyline6(leg.get("shape", ""))] if legs else None
    elif engine == "openrouteservice":
        features = raw.get("features") or []
        points = features[0].get("geometry", {}).get("coordinates") if features else None
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
    # The route that the driver actually takes can be much SHORTER than the
    # 250 m graph walk used to select a distant endpoint. Rejecting every
    # returned polyline under 100 m falsely invalidated the *same two* real
    # Wigan cases for all five independent engines. Instead require a
    # non-degenerate route whose geometry covers the straight-line separation
    # of the two requested points (allowing 12 m snap at each end).
    def distance_m(u, v):
        mean_lat=math.radians((u[1]+v[1])*.5)
        return math.hypot((u[0]-v[0])*111195*math.cos(mean_lat),
                          (u[1]-v[1])*111195)
    route_metres=sum(distance_m(u,v) for u,v in zip(points,points[1:]))
    separation=math.hypot((a[1]-b[1])*111195*math.cos(math.radians((a[0]+b[0])*.5)),
                          (a[0]-b[0])*111195)
    if route_metres < max(5.0, separation-24.0):
        raise ValueError("Returned route geometry too short for its endpoints")
    # Complete legality and orientation need an independent OSM reference judge.
    if engine == "drivemate-native-cpp":
        if raw.get("implementation") != "compiled-cpp":
            raise ValueError("Only compiled-native DriveMate results can be ranked")
        return raw["native_core_ns"] / 1e6
    return None


def run(raw, jar, repeat, maximum, snapshot, use_osrm, use_valhalla=False, use_openrouteservice=False,
        native_binary=Path("navigation_core/native/router")):
    imported = import_osm_xml(raw, provenance=Provenance(
        "Greater Manchester, England", snapshot,
        "Geofabrik historic public OSM PBF", "© OpenStreetMap contributors (ODbL 1.0)"))
    prepared = prepare_navigation(imported.graph, imported.coordinates)
    # Delayed import shares the original eight and eight held-out public-road
    # endpoints exactly with the separate DMN GPS journey replay. The module
    # imports road_cases above, which is already defined when run() executes.
    from benchmarks.real_english_journey import select_case_cohorts
    cases = select_case_cohorts(prepared, imported.graph, maximum)
    engines = ["drivemate-native-cpp", "graphhopper"]
    if use_osrm:
        engines += ["osrm-mld", "osrm-ch"]
    if use_valhalla:
        engines.append("valhalla")
    if use_openrouteservice:
        engines.append("openrouteservice")
    samples = {e: [] for e in engines}
    failures = {e: [] for e in engines}
    with ExitStack() as stack:
        gh_port = stack.enter_context(graphhopper(jar, {"osm": raw}, Path("results/real-england/graphhopper")))
        server, thread, native = start_candidate(prepared, native_binary)
        stack.callback(lambda: (server.shutdown(), server.server_close(), thread.join(timeout=3), native.close()))
        for repetition in range(-3, repeat):
            for case in cases:
                ordered = engines if repetition % 2 else list(reversed(engines))
                for engine in ordered:
                    if repetition >= 0 and any(x["case"] == case["id"] for x in failures[engine]):
                        continue
                    try:
                        start = perf_counter_ns()
                        native_core_ms = query(engine, case, imported.coordinates, server.server_port, gh_port)
                        elapsed = (perf_counter_ns() - start) / 1_000_000
                        if repetition >= 0:
                            entry = {"case": case["id"], "repeat": repetition,
                                     "milliseconds": elapsed}
                            if engine == "drivemate-native-cpp":
                                entry["native_calculation_ms"] = native_core_ms
                            samples[engine].append(entry)
                    except (OSError, KeyError, ValueError, TypeError, IndexError) as exc:
                        if repetition >= 0:
                            failures[engine].append({"case": case["id"], "reason": str(exc)[:160]})
    expected = repeat * len(cases)
    summary = {}
    for engine in engines:
        values = [x["milliseconds"] for x in samples[engine]]
        native_times = [x["native_calculation_ms"] for x in samples[engine]
                        if "native_calculation_ms" in x]
        summary[engine] = {
            "native_median_calculation_ms": median(native_times) if native_times else None,
            "native_p95_calculation_ms": percentile(native_times, .95) if native_times else None,
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
        "selected_public_road_area": os.environ.get("ENGLAND_BBOX_NAME", "unspecified"),
        "attribution": "© OpenStreetMap contributors, ODbL 1.0",
        "road_graph_vertices": len(imported.graph.vertices),
        "road_graph_edges": len(imported.graph.edges),
        "cases": [c["id"] for c in cases],
        "cohort_sha256": sha256(json.dumps(
            [(c["id"], c["source"], c["target"]) for c in cases],
            separators=(",", ":")).encode()).hexdigest(),
        "route_cohorts": {kind: sum(c["cohort"] == kind for c in cases)
                          for kind in ("original", "heldout")},
        "repeats": repeat,
        "warmups": 3, "implementations": summary, "failures": failures,
        "samples": samples,
        "speed_ranks_complete_only": [
            {"rank": i + 1, "engine": e} for i, e in enumerate(ranked)],
        "overall_navigation_rank": None,
        "external_route_legality_verified": False,
        "not_tested": {
            **{engine: "Service not provisioned or readiness check failed on same-host runner"
               for engine in ("valhalla", "openrouteservice") if engine not in engines},
            **NOT_YET_COMPARABLE,
        },
        "engine_version_scope": {
            "drivemate-native-cpp": "compiled C++ navigation_core/native/router using persistent --stream protocol; prepared map",
            "graphhopper": "11.1, CH/LM disabled",
            "osrm-mld": "5.27.1 pinned Docker image, MLD",
            "osrm-ch": "5.27.1 pinned Docker image, CH",
            "valhalla": "3.9.1 pinned Docker image, auto costing",
            "openrouteservice": "9.7.1 Docker image, driving-car",
        },
        "limitations": [
            "Public OSM road topology, not independent current legal-access verification.",
            "DriveMate here is the compiled C++ navigation-core research build, not the Android app APK or device performance.",
            "The Python server marshals validated requests to one persistent compiled native process, not Python route search.",
            "Native in-core calculation times are separately recorded and exclude HTTP serialization/IPC.",
            "All measured services use warm local HTTP; distinct algorithms and costing.",
            "Endpoints, finite polyline, non-degenerate path and endpoint-relative minimum length are checked; full external route legality remains unverified.",
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
    from benchmarks.real_english_journey import select_case_cohorts
    cases = select_case_cohorts(prepared, imported.graph, maximum)
    if len(cases) != maximum:
        raise ValueError("Insufficient public-UK-road cases; never substitute synthetic geometry")
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
    ap.add_argument("--native-binary", type=Path, default=Path("navigation_core/native/router"))
    ap.add_argument("--graphhopper-jar", type=Path)
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--repeat", type=int, default=20)
    ap.add_argument("--cases", type=int, default=16)
    ap.add_argument("--osrm", action="store_true")
    ap.add_argument("--valhalla", action="store_true")
    ap.add_argument("--openrouteservice", action="store_true")
    args = ap.parse_args()
    if not 3 <= args.repeat <= 100 or not 8 <= args.cases <= 100:
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
                 args.repeat, args.cases, args.snapshot, args.osrm,
                 args.valhalla, args.openrouteservice, args.native_binary)
    (out / "speed.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"implementations": result["implementations"],
                      "ranks": result["speed_ranks_complete_only"],
                      "cases": len(result["cases"])}))

if __name__ == "__main__":
    main()
