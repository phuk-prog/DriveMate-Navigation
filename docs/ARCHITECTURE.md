# DriveMate Navigation architecture

## Independence and component choice

This is a separate research repository, not an Android APK or a replacement for `DriveMate`. The architecture is **component-selective**, not wedded to one routing engine. Legally reusable components may be adopted after independent source and licence review; otherwise a provider is a documented reference or authorised benchmark.

## Planned boundaries

1. **Map ingestion:** reproducible OSM extraction with region, timestamp, attribution, checksum, conditional restrictions and provenance. No proprietary data leaks into the public graph.
2. **Directed road graph:** access status `allowed`, `prohibited`, `unknown`, turn restrictions, road side, restrictions conditional on date/time/vehicle; represent uncertain information without inventing permissions.
3. **Routing:** tested shortest-path reference, then better searches and preprocessed routing accelerators behind stable contracts. No performance assumptions before benchmarking.
4. **Location:** sensor fusion, uncertainty tracking, map matching, tunnels and road parallelism. Off-route detection cannot claim GPS certainty it does not have.
5. **Guidance:** legally supported turns, physical exit geometry, numbered exit evidence, lane validity, instruction timings and voice/Android Auto.
6. **Learning:** local/privacy-safe travel-time observations, better matching confidence, proposed optimisations and versioned models. Changes to legal access require independent verification.
7. **Evidence and rollback:** fixture provenance, independent ground truth for legality and lane claims, nightly/regional replay, deterministic baselines, before/after measurements and rollback.

## Current implementation

Only `engine/routing.py` is executable. It performs Dijkstra on directed edges and preserves incoming-edge context so a forbidden turn remains forbidden after rerouting. All speed estimates are input data, not assertions of legal speed limits. Unknown-access edges are excluded. A tiny synthetic fixture and tests establish these contracts.

The data graph is deliberately not derived from real roads yet. Do not interpret this software as safe for actual driving.

## Future Android integration

Measure native/Kotlin vs C++ or Rust and legal component reuse before choosing implementation language. Build an isolated Android benchmark first; do not generate release APKs from this repository. Consider map size, startup, RAM, battery, p50/p95/p99 reroute latency and safe failure behaviour when a map is incomplete.
