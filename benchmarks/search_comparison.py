"""Single-graph Dijkstra vs A* experiment; does not benchmark other engines."""
from __future__ import annotations

import argparse
import json
import statistics
from time import perf_counter_ns

from engine import shortest_route
from engine.astar import astar_route
from .synthetic_grid import grid


def run(*, size: int = 14, repeats: int = 8) -> dict:
    if not 2 <= repeats <= 100:
        raise ValueError("Runs must be 2..100")
    graph, points, start, finish = grid(size)
    timings = {"Dijkstra": [], "A*": []}
    expansions = []
    for _ in range(repeats):
        t0 = perf_counter_ns()
        baseline = shortest_route(graph, start, finish)
        timings["Dijkstra"].append((perf_counter_ns() - t0) / 1e6)
        t1 = perf_counter_ns()
        challenger = astar_route(graph, start, finish, coordinates=points)
        timings["A*"].append((perf_counter_ns() - t1) / 1e6)
        if abs(baseline.estimated_seconds - challenger.route.estimated_seconds) > 1e-8:
            raise AssertionError("A* disagrees with legal shortest-time baseline")
        if not challenger.geographic_heuristic_used:
            raise AssertionError("Fabricated grid geometry should permit a safe heuristic")
        expansions.append(challenger.expanded_states)
    return {
        "classification": "synthetic",
        "valid_for_road_navigation": False,
        "actual_external_engine_runs": 0,
        "data_source": "fabricated-grid-not-real-geography",
        "grid_size": size,
        "vertices": len(graph.vertices),
        "directed_edges": len(graph.edges),
        "runs_each": repeats,
        "estimated_trip_seconds": round(baseline.estimated_seconds, 4),
        "A*_expanded_states_median": statistics.median(expansions),
        "routing_ms_median": {n: round(statistics.median(vals), 6) for n, vals in timings.items()},
        "disclaimer": "Python synthetic timings are not comparable to native routing engines or Android.",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--size", type=int, default=14)
    p.add_argument("--repeat", type=int, default=8)
    args = p.parse_args()
    print(json.dumps(run(size=args.size, repeats=args.repeat), indent=2))


if __name__ == "__main__":
    main()
