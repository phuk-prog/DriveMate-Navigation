"""Lightweight, informational benchmark; never invent competitor results."""
from __future__ import annotations

import argparse
import json
import statistics
import time

from engine import shortest_route
from .fixture import load_fixture


def measure(repetitions: int = 30) -> dict:
    if not 1 <= repetitions <= 100000:
        raise ValueError("Repetitions outside allowed range")
    graph, start, end, expected = load_fixture()
    observed_ns = []
    route = None
    for _ in range(repetitions):
        began = time.perf_counter_ns()
        route = shortest_route(graph, start, end)
        observed_ns.append(time.perf_counter_ns() - began)
        if route.edge_ids != expected:
            raise AssertionError("Synthetic fixture did not follow the expected legal route")
    sorted_ns = sorted(observed_ns)
    p95 = sorted_ns[max(0, (95 * len(sorted_ns) + 99) // 100 - 1)]
    return {
        "engine": "DriveMate Navigation prototype",
        "fixture": "synthetic-junction",
        "data_is_real_world": False,
        "competitor_comparisons": 0,
        "benchmark_valid_for_real_world": False,
        "repetitions": repetitions,
        "route_edge_ids": list(route.edge_ids),
        "route_distance_m": route.length_m,
        "estimated_trip_seconds": route.estimated_seconds,
        "latency_median_ms": round(statistics.median(observed_ns) / 1e6, 6),
        "latency_p95_ms": round(p95 / 1e6, 6),
        "note": "Synthetic smoke test only; CPU and CI conditions vary. No claim of navigation speed or safety.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=30)
    args = parser.parse_args()
    print(json.dumps(measure(args.repeat), indent=2))


if __name__ == "__main__":
    main()
