"""Reject unfair competitor comparisons; no provider calls or fabricated results."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import median
from typing import Mapping


@dataclass(frozen=True)
class Measurement:
    engine: str
    engine_version: str
    graph_sha256: str
    profile_sha256: str
    scenario: str
    device: str
    environment: str
    run_kind: str  # cold | warm
    latency_ms: tuple[float, ...]
    classification: str = "unverified"  # synthetic | unverified | independently-validated

    def __post_init__(self):
        names = (self.engine, self.engine_version, self.graph_sha256,
                 self.profile_sha256, self.scenario, self.device, self.environment)
        if any(not t.strip() for t in names):
            raise ValueError("Benchmarks require explicit engine and environment provenance")
        if self.run_kind not in ("cold", "warm"):
            raise ValueError("Run kind must be cold or warm")
        if self.classification not in ("synthetic", "unverified", "independently-validated"):
            raise ValueError("Invalid evidence classification")
        if len(self.graph_sha256) != 64 or len(self.profile_sha256) != 64:
            raise ValueError("Graph and profile identifiers must be SHA256 hex digests")
        if any(ch not in "0123456789abcdef" for ch in self.graph_sha256.lower() + self.profile_sha256.lower()):
            raise ValueError("Invalid SHA256")
        if len(self.latency_ms) < 5 or any(not isfinite(v) or v < 0 for v in self.latency_ms):
            raise ValueError("Need >=5 finite, nonnegative measurements")


def _p95(items: tuple[float, ...]) -> float:
    values = sorted(items)
    return values[max(0, (95 * len(values) + 99) // 100 - 1)]


def compare(a: Measurement, b: Measurement) -> Mapping[str, object]:
    """Return comparable timings only after identical experiment inputs are verified.

    Speed measurements do not demonstrate road legality or route quality. This
    implementation does not ingest benchmarks from unverified vendor outputs.
    """
    checks = {
        "graph_sha256": a.graph_sha256 == b.graph_sha256,
        "profile_sha256": a.profile_sha256 == b.profile_sha256,
        "scenario": a.scenario == b.scenario,
        "device": a.device == b.device,
        "environment": a.environment == b.environment,
        "run_kind": a.run_kind == b.run_kind,
        "classification": a.classification == b.classification,
    }
    mismatches = sorted(k for k, match in checks.items() if not match)
    if mismatches:
        return {"comparable": False, "reasons": mismatches, "score": None}
    return {
        "comparable": True,
        "classification": a.classification,
        "note": "Timing-only comparison: neither correctness nor legal movement is validated by timing.",
        "measurements": {
            a.engine: {"median_ms": median(a.latency_ms), "p95_ms": _p95(a.latency_ms)},
            b.engine: {"median_ms": median(b.latency_ms), "p95_ms": _p95(b.latency_ms)},
        },
    }
