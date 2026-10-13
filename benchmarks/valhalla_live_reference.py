"""Experimental Valhalla live reference, local-only and public-data-only.

No personal journeys, GPS recordings, external APIs or route geometry committed.
Valhalla serves an independently selected public OSM PBF subset on loopback.
This benchmark is NOT a fair ranking versus the DriveMate prototype: graph
access policies, edge snapping, costing and timing interfaces are different.

The real container's startup/build time is not included in request latency.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from time import monotonic, perf_counter_ns, sleep
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from benchmarks.provider_summaries import summarise
from benchmarks.public_uk_probe import _public_file, _scenarios
from engine import RouteNotFound, shortest_route
from engine.astar import astar_route, prepare_astar
from map_data import Provenance, import_osm_xml


HOST = "127.0.0.1"
PORT = 8002
ROUTE_URL = "http://127.0.0.1:8002/route"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        raise ValueError("Valhalla reference refuses redirects")


_OPENER = build_opener(_NoRedirect())


def _point(coords: tuple[float, float]) -> dict[str, float]:
    from math import isfinite
    if len(coords) != 2:
        raise ValueError("Invalid publicly derived graph point")
    lat, lon = coords
    if not isfinite(lat) or not isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("Out-of-range graph position")
    return {"lat": float(lat), "lon": float(lon)}


def route_request_body(start: tuple[float, float], end: tuple[float, float]) -> bytes:
    """Only send publicly derived graph points to a LOCAL routing container."""
    payload = {
        "locations": [_point(start), _point(end)],
        "costing": "auto",
        "directions_options": {"units": "kilometers"},
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def valhalla_local_request(body: bytes) -> dict:
    """No hostname, path, token, file, or data origin is configurable."""
    if not isinstance(body, bytes) or len(body) > 1000:
        raise ValueError("Public routing request outside 1 KB bound")
    request = Request(
        ROUTE_URL, body, {"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with _OPENER.open(request, timeout=15) as response:
            if response.status != 200:
                return {"route_unavailable": True}
            data = response.read(100_001)
    except HTTPError as exc:
        # Valhalla returns non-200 for no nearby routable edges.
        if 400 <= exc.code < 500:
            return {"route_unavailable": True}
        raise RuntimeError("Local Valhalla server returned an error") from exc
    except (URLError, ConnectionResetError, BrokenPipeError) as exc:
        raise RuntimeError("Local Valhalla connection failed after health readiness") from exc
    if len(data) > 100_000:
        raise ValueError("Valhalla response exceeds aggregate-only bound")
    parsed = json.loads(data)
    if not isinstance(parsed, dict):
        raise ValueError("Valhalla response must be a JSON object")
    return parsed


def wait_for_local_router(timeout_s: float = 150.0) -> None:
    """Require a completed HTTP health response, not a prematurely opened TCP port."""
    deadline = monotonic() + timeout_s
    url = "http://127.0.0.1:8002/status"
    while monotonic() < deadline:
        try:
            with _OPENER.open(url, timeout=3) as response:
                if response.status == 200:
                    response.read(16_384)
                    sleep(1.0)
                    return
        except (OSError, HTTPError, URLError, ValueError):
            pass
        sleep(0.75)
    raise TimeoutError("Valhalla /status never became responsive within the timeout")


def benchmark_valhalla_local(
    raw: bytes, *, snapshot: str, samples: int = 8, repeats: int = 5,
    request: Callable[[bytes], dict] = valhalla_local_request,
) -> dict[str, object]:
    if not 1 <= samples <= 24 or not 1 <= repeats <= 15:
        raise ValueError("Only small, bounded, public-data experiments allowed")
    imported = import_osm_xml(raw, provenance=Provenance(
        region="independently selected public UK road area",
        snapshot=snapshot, source="shared-public-OSM-subset",
        attribution="© OpenStreetMap contributors",
    ))
    graph = imported.graph
    prepared = prepare_astar(graph, imported.coordinates)
    dijkstra_ms: list[float] = []
    astar_ms: list[float] = []
    valhalla_ms: list[float] = []
    valhalla_no_route = 0
    scenarios_ok = 0

    for source, target in _scenarios(graph, limit=samples)[:samples]:
        try:
            start_ns = perf_counter_ns()
            dijkstra = shortest_route(graph, source, target)
            d_ms = (perf_counter_ns() - start_ns) / 1e6
            start_ns = perf_counter_ns()
            candidate = astar_route(graph, source, target, prepared=prepared)
            a_ms = (perf_counter_ns() - start_ns) / 1e6
        except RouteNotFound:
            continue
        if abs(dijkstra.estimated_seconds - candidate.route.estimated_seconds) > 1e-7:
            raise AssertionError("DriveMate's two routing algorithms disagree")
        body = route_request_body(imported.coordinates[source], imported.coordinates[target])
        measurements: list[float] = []
        available = True
        for _ in range(repeats):
            start_ns = perf_counter_ns()
            result = request(body)
            elapsed = (perf_counter_ns() - start_ns) / 1e6
            if not isinstance(result, dict):
                raise ValueError("Valhalla response is not JSON")
            if result.get("route_unavailable") is True:
                available = False
                break
            summary = summarise("Valhalla", result)
            if summary.distance_m <= 0 or summary.estimated_seconds <= 0:
                raise ValueError("Valhalla returned an invalid route summary")
            measurements.append(elapsed)
        if available:
            valhalla_ms.extend(measurements)
            dijkstra_ms.append(d_ms)
            astar_ms.append(a_ms)
            scenarios_ok += 1
        else:
            valhalla_no_route += 1

    if scenarios_ok == 0:
        raise AssertionError("No public graph test scenarios were routable in Valhalla")
    return {
        "classification": "public-road-experimental-different-routing-profiles",
        "same_public_osm_source_sha256": imported.metadata["source_sha256"],
        "snapshot": snapshot,
        "reference": "Valhalla 3.9.1 / local Docker route API",
        "real_valhalla_execution": request is valhalla_local_request,
        "head_to_head_valid": False,
        "comparability_limitations": [
            "Valhalla and prototype apply different car-access, costing and turn policies",
            "Valhalla may snap to a different nearby road than the prototype",
            "Valhalla latency includes loopback HTTP/JSON, while Python timers are internal searches",
            "Independent legal-road and lane correctness not yet validated",
        ],
        "scenarios_ok": scenarios_ok,
        "scenarios_unroutable": valhalla_no_route,
        "repeats_per_successful_scenario": repeats,
        "prototype_dijkstra_median_ms": round(median(dijkstra_ms), 6),
        "prototype_astar_median_ms": round(median(astar_ms), 6),
        "valhalla_local_http_median_ms": round(median(valhalla_ms), 6),
        "contains_personal_journeys": False,
        "approved_for_driving": False,
        "note": "Exploratory integration result only. No provider ranking; no geometry, coordinates or traces logged.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Valhalla localhost smoke on a public, non-personal map")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    raw = _public_file(args.input).read_bytes()
    wait_for_local_router()
    print(json.dumps(benchmark_valhalla_local(
        raw, snapshot=args.snapshot, samples=args.samples, repeats=args.repeats,
    ), indent=2))


if __name__ == "__main__":
    main()
