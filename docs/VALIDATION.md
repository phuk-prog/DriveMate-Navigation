# Benchmark and validation protocol

## Four independent kinds of evidence

1. **Correctness oracle:** labelled synthetic fixtures and independently checked real-world junction permissions. Provider consensus is not an oracle.
2. **Equivalent routing inputs:** matching map version/hash, vehicle dimensions, legal restrictions, departure time, live traffic inputs and avoid/preferences; record all differences.
3. **Performance:** same hardware, repeatable warm/cold runs, route distance, p50/p95/p99 latency, memory, storage, battery, and reroute detection vs calculation time measured separately.
4. **Robustness:** GPS dropouts, parallel road ambiguity, tunnels, wrong turns, nested roundabouts, disconnected maps, offline transitions and version migrations.

## Initial comparison contract

`benchmarks/comparison.py` now rejects direct timing comparisons when graph SHA-256, profile SHA-256, scenario, device, environment, run temperature or evidence classification differ. It prints timings only, never safety or correctness results. Tests use **fabricated sample latency values** that are not observed speeds of any competitor.

For real benchmarks, first build a shared import pipeline and independently check the road topology. External providers with proprietary or different map versions must be explicitly marked **not directly comparable**. No external routing engines have been executed in this repository yet. Offline parsers in `benchmarks/provider_summaries.py` discard all coordinates, trip details and geometry, and report aggregate length and estimated duration only.

## Prototype search comparison

A* and Dijkstra now run against the **same synthetic directed graph and turn restriction rules**, including tests for blocked roads, unknown access and nonnegative learned penalties. A* first validates its coordinate-based heuristic, falling back to zero (Dijkstra-style) if the geometry is incomplete or inconsistent. See `benchmarks/search_comparison.py`. The timings are Python-only, include different preprocessing work, and do not establish whether A* is faster on real UK maps or Android.

Local public-road preparation scripts are opt-in; no real road extract, user coordinates or GPS tracks are committed or fetched in CI.

## Acceptance gates

- Never accept a known illegal turn, wrong-way route or unsupported lane/roundabout claim in a validated case.
- Learning may optimise estimated time and preference models but must not grant new road permissions.
- Each candidate change must pass fixture, property-style, integration, replay and regression gates appropriate to its risk.
- Report unresolved evidence as **unknown**, including unverified exits.
- Retain a clean rollback target, map version and evidence provenance for every accepted change.
- This **public** repository cannot receive real drives, consented or otherwise. Any such work must be explicitly approved for a separate private environment; only safely synthetic or independently public non-personal fixtures are accepted here.

## Comparing the reference engines

All external engines listed in `benchmarks/reference-engines.json` are initially `not-integrated` or `access-and-terms-not-verified`; **do not report hypothetical scores as measured**. Providers using proprietary datasets or incompatible map snapshots may still be qualitative references but must not be presented as identical-data head-to-head results.

Do not query commercial services or download datasets without checking API terms, billing and redistribution rights. Never infer a legal junction movement from a competitor's suggested route alone.

## Public UK road smoke protocol (on-demand)

The project includes an opt-in GitHub Actions step guarded by a `[uk-road-smoke]` commit-message marker. This one run downloads the fixed historical `greater-manchester-260901.osm.pbf` public Geofabrik extract, then uses Osmium to clip an **independently selected public road area**, strip contributor metadata and remove downloaded files after the job. It performs only aggregate Dijkstra/A* experiments based on generated test scenarios. It never reads user journeys.

A successful job demonstrates **import of one small partial public UK road sample and shortest-time consistency**, not legally verified navigation. A failure to import due to unsupported turn restrictions is meaningful: the importer intentionally fails closed. This is not an OSRM/Valhalla/GraphHopper measurement. Those require their real engines and harmonised motorcar profiles.

## Routing performance follow-up

The first actual public-road smoke test imported a partial 2,023-node / 1,202-edge road graph and generated eight algorithm-agreement scenarios, but A* was around two orders of magnitude slower than Dijkstra because each route performed a fresh O(E) geometry check. A follow-up adds `prepare_astar()` to validate geometry once per immutable road-graph snapshot and reuse that preparation on each reroute. The experiment now reports one-time preparation cost separately from warmed routing cost, and measures unprepared A* as a regression reference.

The results remain too small and topologically unverified to select a production engine. The sample had zero imported prohibited-turn pairs. We must test much longer and legally verified junction routes.
