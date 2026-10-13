"""Entirely fabricated equatorial grid; NOT a person's location or recorded route."""
from __future__ import annotations

from engine import RoadEdge, RoadGraph


def grid(size: int = 14) -> tuple[RoadGraph, dict[str, tuple[float,float]], str, str]:
    if not 2 <= size <= 100:
        raise ValueError("Grid size must be 2..100")
    vertices = [f"v-{x}-{y}" for x in range(size) for y in range(size)]
    # Fabricated geodesic-compatible coordinates near the equator, not UK data.
    points = {f"v-{x}-{y}": (x * 0.001, y * 0.001)
              for x in range(size) for y in range(size)}
    edges = []
    for x in range(size):
        for y in range(size):
            source = f"v-{x}-{y}"
            for nx, ny in ((x + 1, y), (x, y + 1)):
                if nx >= size or ny >= size:
                    continue
                target = f"v-{nx}-{ny}"
                # 112 m exceeds the great-circle distance of each 0.001° segment.
                edges.append(RoadEdge(f"{source}>{target}", source, target, 112.0, 40.0, "allowed"))
                edges.append(RoadEdge(f"{target}>{source}", target, source, 112.0, 40.0, "allowed"))
    return RoadGraph(vertices, edges), points, "v-0-0", f"v-{size-1}-{size-1}"
