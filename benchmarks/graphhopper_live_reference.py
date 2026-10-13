"""GraphHopper 11.1 local reference over independently selected public OSM data.

Only generated public-graph endpoints are requested; no personal GPS tracks,
addresses, journeys or private files. No raw request URL or response geometry
is logged or serialised. The output is exploratory and NOT a fair speed ranking
of different routing algorithms, vehicle profiles or API interfaces.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from time import monotonic, perf_counter_ns, sleep
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, build_opener

from benchmarks.provider_summaries import summarise
from benchmarks.public_uk_probe import _public_file, _scenarios
from engine import RouteNotFound, shortest_route
from engine.astar import astar_route, prepare_astar
from map_data import Provenance, import_osm_xml

INFO_URL = "http://127.0.0.1:8989/info"
ROUTE_ENDPOINT = "http://127.0.0.1:8989/route"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("GraphHopper adapter prohibits redirects")


_OPENER = build_opener(_NoRedirect())


def _valid_point(point: tuple[float, float]) -> str:
    from math import isfinite
    if len(point) != 2:
        raise ValueError("Invalid public graph point")
    lat, lon = point
    if not isfinite(lat) or not isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("Graph point outside coordinate bounds")
    return f"{lat:.7f},{lon:.7f}"


def route_url(start: tuple[float, float], finish: tuple[float, float]) -> str:
    """URL is fixed to localhost. Coordinates MUST come from a public OSM graph."""
    arguments = [
        ("point", _valid_point(start)), ("point", _valid_point(finish)),
        ("profile", "car"), ("points_encoded", "false"),
        ("instructions", "false"), ("calc_points", "false"),
    ]
    return ROUTE_ENDPOINT + "?" + urlencode(arguments)


def local_graphhopper_request(url: str) -> dict:
    if not url.startswith(ROUTE_ENDPOINT + "?"):
        raise ValueError("GraphHopper requests can only reach the fixed local endpoint")
    try:
        with _OPENER.open(url, timeout=12) as response:
            if response.status != 200:
                raise ValueError("GraphHopper route HTTP status was not successful")
            payload = response.read(100_001)
    except HTTPError as exc:
        # A nearby node may not snap or this partial data may be disconnected.
        if exc.code in (400, 404, 422):
            return {"route_unavailable": True}
        raise RuntimeError("Local GraphHopper HTTP routing failure") from exc
    except (URLError, ConnectionResetError, BrokenPipeError) as exc:
        raise RuntimeError("Local GraphHopper connection lost") from exc
    if len(payload) > 100_000:
        raise ValueError("GraphHopper response exceeds the allowed summary size")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Invalid GraphHopper response")
    return data


def wait_for_graphhopper(timeout_s: float = 160) -> None:
    """Wait for HTTP readiness, not merely a port accepting connections."""
    deadline = monotonic() + timeout_s
    while monotonic() < deadline:
        try:
            with _OPENER.open(INFO_URL, timeout=3) as response:
                if response.status == 200:
                    response.read(16_385)
                    return
        except (OSError, HTTPError, URLError, ValueError):
            pass
        sleep(0.8)
    raise TimeoutError("GraphHopper /info failed HTTP readiness within timeout")


def benchmark_graphhopper_local(
    raw: bytes, *, snapshot: str, samples: int = 8, repeats: int = 5,
    request: Callable[[str], dict] = local_graphhopper_request,
) -> dict[str, object]:
    if not 1 <= samples <= 24 or not 1 <= repeats <= 15:
        raise ValueError("Only small, bounded public-data routing experiments permitted")
    imported = import_osm_xml(raw, provenance=Provenance(
        region="independently selected public UK roads", snapshot=snapshot,
        source="same-public-OSM-subset-as-GraphHopper",
        attribution="© OpenStreetMap contributors",
    ))
    graph = imported.graph
    prepared = prepare_astar(graph, imported.coordinates)
    baseline_ms, astar_ms, service_ms = [], [], []
    successful, unavailable = 0, 0
    for origin, destination in _scenarios(graph, limit=samples)[:samples]:
        try:
            t = perf_counter_ns()
            baseline = shortest_route(graph, origin, destination)
            d_ms = (perf_counter_ns() - t) / 1e6
            t = perf_counter_ns()
            alternate = astar_route(graph, origin, destination, prepared=prepared)
            a_ms = (perf_counter_ns() - t) / 1e6
        except RouteNotFound:
            continue
        if abs(baseline.estimated_seconds - alternate.route.estimated_seconds) > 1e-7:
            raise AssertionError("Dijkstra / A* shortest cost parity failure")
        if not baseline.edge_ids:
            continue
        url = route_url(imported.coordinates[origin], imported.coordinates[destination])
        collected = []
        did_route = True
        for _ in range(repeats):
            t = perf_counter_ns()
            response = request(url)
            elapsed = (perf_counter_ns() - t) / 1e6
            if not isinstance(response, dict):
                raise ValueError("Invalid GraphHopper response type")
            if response.get("route_unavailable") is True or response.get("message") == "Connection not found":
                did_route = False
                break
            summary = summarise("GraphHopper", response)
            if summary.distance_m <= 0 or summary.estimated_seconds <= 0:
                raise ValueError("GraphHopper returned zero-length route for a nontrivial scenario")
            collected.append(elapsed)
        if did_route:
            successful += 1
            baseline_ms.append(d_ms)
            astar_ms.append(a_ms)
            service_ms.extend(collected)
        else:
            unavailable += 1
    if successful == 0:
        raise AssertionError("No generated public-road scenario routable by GraphHopper")
    return {
        "classification": "public-road-exploratory-different-graph-and-costing",
        "snapshot": snapshot,
        "same_public_osm_input_sha256": imported.metadata["source_sha256"],
        "reference_engine": "GraphHopper web-service 11.1 on local Java 25",
        "graphhopper_executed": request is local_graphhopper_request,
        "fair_engine_speed_ranking": False,
        "comparison_limitations": [
            "Different car access/costing and turn restrictions",
            "Different graph construction and location snapping",
            "GraphHopper includes local HTTP/JSON but prototype measures only internal Python search",
            "No independent evidence of legal road/lane/roundabout correctness",
        ],
        "graphhopper_scenarios_ok": successful,
        "graphhopper_scenarios_unroutable": unavailable,
        "route_requests_per_successful_scenario": repeats,
        "dijkstra_internal_search_median_ms": round(median(baseline_ms), 6),
        "astar_internal_search_median_ms": round(median(astar_ms), 6),
        "graphhopper_loopback_http_median_ms": round(median(service_ms), 6),
        "source_road_data_public": True,
        "personal_journeys_used": False,
        "verified_safe_for_driving": False,
        "note": "Aggregate timings only; not comparable benchmarks or legal-navigation validation.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Local public-only GraphHopper integration smoke")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    raw = _public_file(args.input).read_bytes()
    wait_for_graphhopper()
    print(json.dumps(benchmark_graphhopper_local(
        raw, snapshot=args.snapshot, samples=args.samples, repeats=args.repeats,
    ), indent=2))


if __name__ == "__main__":
    main()
