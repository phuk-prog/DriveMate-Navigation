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

## OSRM MLD live reference smoke

Commit marker `[osrm-reference-smoke]` activates one **ephemeral**, public-data-only GitHub Actions experiment. It downloads the pinned standard Geofabrik Greater Manchester historical extract into runner temporary storage, creates one **shared** complete-ways public OSM subset, uses its stripped XML in the DriveMate prototype, and passes the **same subset PBF** into pinned OSRM v5.27.1 MLD (`osrm-extract` with `/opt/car.lua`, `osrm-partition`, `osrm-customize`, then `osrm-routed`).

The generated start/end graph nodes are deterministic **public-road sample points unrelated to any person's journeys**. Queries go only to localhost. Raw route geometry/waypoints are not logged or committed. The CI cleans up all downloaded maps and temporary routing artifacts.

The report deliberately states `valid_head_to_head_comparison=false` because OSRM and DriveMate have **different car access and costing policies, graph splitting, destination snapping, and timed code paths** (HTTP+JSON vs local Python). An OSRM MLD request latency must not be presented as directly equivalent to DriveMate algorithm runtime. This establishes a repeatable integration baseline, **not** a validated ranking or safe turn legality result. The benchmark has no paid API dependencies.

See [official OSRM backend documentation](https://github.com/Project-OSRM/osrm-backend), [OSRM Route API](https://github.com/Project-OSRM/osrm-backend/blob/master/docs/http.md) and [v5.27.1 image](https://github.com/orgs/Project-OSRM/packages/container/osrm-backend).

## Valhalla runtime integration (exploratory)

The commit marker `[valhalla-reference-smoke]` enables a one-time, capped experiment using Valhalla's **official** scripted Docker image version **3.9.1**, pinned to a published manifest SHA-256. The workflow uses the same historical Geofabrik Greater Manchester PBF as the OSRM smoke; it clips the same independently selected public test bounding box, strips contributor metadata in a temporary local XML conversion, starts Valhalla on loopback, and sends deterministic public graph endpoints from the synthetic walk generator.

Its output contains only aggregate request latency and success counts. The local API request latency includes Valhalla network/JSON overhead, and the DriveMate prototypes measure internal Python routing; profile rules and snapping also differ. Therefore **head_to_head_valid=false** regardless of which median appears numerically lower. The real provider run can fail when Valhalla declines short or incomplete extracts; this must remain a reported limitation, never be converted into a false success.

Sources: https://github.com/valhalla/valhalla/blob/master/docker/README.md and https://valhalla.github.io/valhalla/building/

### Health-check correction

An initial live Valhalla run failed with a connection reset immediately after the host socket became reachable. The live adapter now requires a **completed HTTP 200 from /status** before issuing routes, and adds bounded diagnostics on failure. Do not present unsuccessful runs as provider benchmark results.
