"""Run strictly local OSRM MLD against synthetic/non-personal public graph routes.

No paid API or remote router. Real measurements require an independently
prepared public OSM extract in the ignored results/ directory. Both engines
consume that same OSM subset, but their car profiles, snapping and HTTP
overhead are NOT equivalent; this report must NEVER rank routing correctness.

This module never logs or serialises origin/destination coordinates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
from statistics import median
from time import monotonic, perf_counter_ns, sleep
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, build_opener

from engine import RouteNotFound, shortest_route
from engine.astar import astar_route, prepare_astar
from map_data import Provenance, import_osm_xml
from benchmarks.public_uk_probe import _public_file, _scenarios

OSRM_PORT = 5000
BASE_URL = "http://127.0.0.1:5000"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Local OSRM adapter refuses HTTP redirects")


OPENER = build_opener(NoRedirect())


def local_route_url(origin: tuple[float, float], target: tuple[float, float]) -> str:
    """Construct a loopback-only URL from map graph points, never from a user."""
    def point(p):
        if len(p) != 2:
            raise ValueError("Invalid graph coordinate")
        lat, lon = p
        from math import isfinite
        if not all((isfinite(lat), isfinite(lon), -90 <= lat <= 90, -180 <= lon <= 180)):
            raise ValueError("Invalid graph position")
        return f"{lon:.7f},{lat:.7f}"
    return f"{BASE_URL}/route/v1/driving/{point(origin)};{point(target)}?overview=false&steps=false&alternatives=false"


def local_osrm_request(url: str) -> dict:
    if not url.startswith(BASE_URL + "/route/v1/driving/"):
        raise ValueError("OSRM must be queried via fixed localhost endpoint only")
    with OPENER.open(url, timeout=12) as response:
        if response.status != 200:
            raise ValueError("Local OSRM returned an unexpected HTTP status")
        payload = response.read(100_001)
    if len(payload) > 100_000:
        raise ValueError("OSRM response too large for aggregate-only benchmark")
    try:
        data = json.loads(payload)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("OSRM returned invalid JSON") from exc
    if not isinstance(data, dict) or data.get("code") not in ("Ok", "NoRoute", "NoSegment"):
        raise ValueError("OSRM returned an unsupported routing status")
    return data


def wait_for_local_router(timeout_s: float = 35) -> None:
    deadline = monotonic() + timeout_s
    while monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", OSRM_PORT), timeout=1):
                return
        except OSError:
            sleep(0.5)
    raise TimeoutError("Local OSRM did not start within the time limit")


def benchmark_osrm_local(raw: bytes, *, snapshot: str,
                         samples: int = 8, repeats: int = 5,
                         request: Callable[[str], dict] = local_osrm_request) -> dict[str, object]:
    if not 1 <= samples <= 24 or not 1 <= repeats <= 15:
        raise ValueError("Small bounded public-data experiment only")
    graph_data = import_osm_xml(raw, provenance=Provenance(
        region="independently selected public road area", snapshot=snapshot,
        source="same-public-osm-extract-as-osrm", attribution="© OpenStreetMap contributors"))
    graph = graph_data.graph
    prepared = prepare_astar(graph, graph_data.coordinates)
    timings_python = []
    timings_astar = []
    timings_osrm = []
    successful_scenarios = 0
    no_route_count = 0
    for start, finish in _scenarios(graph, limit=samples)[:samples]:
        try:
            t = perf_counter_ns()
            original = shortest_route(graph, start, finish)
            d_time = (perf_counter_ns() - t) / 1e6
            t = perf_counter_ns()
            candidate = astar_route(graph, start, finish, prepared=prepared)
            a_time = (perf_counter_ns() - t) / 1e6
        except RouteNotFound:
            continue
        if abs(original.estimated_seconds - candidate.route.estimated_seconds) > 1e-7:
            raise AssertionError("DriveMate graph algorithms disagree")
        if not original.edge_ids:
            continue
        url = local_route_url(graph_data.coordinates[start], graph_data.coordinates[finish])
        good = True
        for _ in range(repeats):
            t = perf_counter_ns()
            response = request(url)
            elapsed = (perf_counter_ns() - t) / 1e6
            if response.get("code") != "Ok":
                good = False
                break
            routes = response.get("routes")
            if not isinstance(routes, list) or not routes:
                raise AssertionError("OSRM reported Ok but no route")
            route = routes[0]
            if not isinstance(route, dict) or not isinstance(route.get("distance"), (float, int)) or not isinstance(route.get("duration"), (float, int)):
                raise ValueError("No aggregate route metrics from OSRM")
            timings_osrm.append(elapsed)
        if good:
            successful_scenarios += 1
            timings_python.append(d_time)
            timings_astar.append(a_time)
        else:
            no_route_count += 1
    if not successful_scenarios:
        raise AssertionError("No shared scenario was routable; comparison cannot be assessed")
    return {
        "classification": "experimental-profile-and-snapping-mismatch",
        "valid_head_to_head_comparison": False,
        "reason_not_comparable": [
            "OSRM car.lua access/turn costing differs from DriveMate prototype",
            "OSRM snaps to its own graph; graph nodes/segments may not correspond",
            "OSRM times include local HTTP/JSON overhead; Python timings do not",
            "Route legality not independently verified",
        ],
        "same_osm_input_sha256": graph_data.metadata["source_sha256"],
        "snapshot": snapshot,
        "public_data_only": True,
        "personal_journeys_used": False,
        "external_engine": "OSRM MLD local Docker image",
        "third_party_engine_executed": True,
        "scenarios_osrm_ok": successful_scenarios,
        "scenarios_osrm_unroutable": no_route_count,
        "repeats_per_successful_scenario": repeats,
        "drive_mate_dijkstra_search_median_ms": round(median(timings_python), 6),
        "drive_mate_astar_search_median_ms": round(median(timings_astar), 6),
        "osrm_local_api_request_median_ms": round(median(timings_osrm), 6),
        "verified_safe_for_driving": False,
        "note": "No automatic winner ranking; different cost models and timed code paths.",
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Local, public-only OSRM smoke; no personal routes")
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--snapshot", required=True)
    p.add_argument("--samples", type=int, default=8)
    p.add_argument("--repeats", type=int, default=5)
    a = p.parse_args()
    raw = _public_file(a.input).read_bytes()
    wait_for_local_router()
    result = benchmark_osrm_local(raw, snapshot=a.snapshot, samples=a.samples, repeats=a.repeats)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
