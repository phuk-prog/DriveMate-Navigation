# DMN modular navigation test architecture — 15 October 2026

**Owner requirement:** test every independently meaningful part of a navigation journey, not just road routing. Separate implementation into small, replaceable components so a poor GPS matcher can be upgraded without modifying route search, or a better map format can be introduced without rewriting the whole controller.

The [machine-readable module inventory](../config/dmn_navigation_modules.json) currently defines **14 summary areas**, **59 independent subsystem contracts** and **236 granular checks**. These check names are **planned acceptance questions**, not 236 completed tests or a minimum number of journeys. A scenario can apply to several checks. Add modules/checks where investigation reveals new failure modes.

## Layered programme

1. **Road truth/data** — dated source import, legality, graph version, UK car profile, official evidence conflicts, speed-limit sources, offline addresses and entrances.
2. **Routing and route quality** — correct directed graph, turn permissions, cost/ETA, alternative routes, road access, roundabouts and junction path geometry.
3. **Position and motion** — GNSS, speed, heading, accuracy, sensor fusion, confidence, parallel roads, bridge levels, signal loss and reacquisition.
4. **Navigation controller** — off-route detection, reroute timing, repeated wrong turns, turn/roundabout/lane instruction selection, driver speed-aware timing and arrival.
5. **Delivery and dependents** — map-line adherence, renderer sync, offline map/graph updates, speech/Bluetooth, resource use, startup, crash recovery and fallback.
6. **Independent assessment** — fair reference adapters, legality oracles, time/resource instrumentation, rerun/held-out evidence, counts and rankings.

Each module has its own `dmn.<module_id>` **proposed interface boundary**. This is a planning identifier, **not a claim** that a Python package of that name exists. Keep algorithms/data adapters behind versioned inputs/outputs, with a minimal test fixture, evidence provenance, capability declaration and cheap unit tests; run cross-component and complete-journey tests to catch failures across boundaries. Do not force a rewrite or premature abstraction merely to match these names. Existing historical `navigation_core` modules and tests on research branches must be mapped and reused where sound.

## Tests for every single behavior

Each check should ultimately be exercised through a tiered approach when applicable:

- **Module test:** one responsibility and precise pass/fail condition, including bad input and fallback.
- **Real UK source case:** pinned OSM/public map geometry plus reliable legal or speed evidence where available, not synthetic UK roads.
- **Adversarial replay:** independently generated non-personal GPS traces over that real geometry; include speed, heading, loss, jumps, drift, tunnels, parallel roads and repeated wrong turns. Label injected faults, never call them measured real-device GPS.
- **Cross-component replay:** route/position/match/reroute/guidance/arrival together on the same scenario and map snapshot.
- **External engine comparison:** exact same input and judged capability where executable; else NOT TESTED or NON COMPARABLE, never a fabricated score.
- **Android emulator checkpoint:** complete journey, offline, timing, lifecycle and audio where emulator supports it. Device GNSS, battery and physical Bluetooth effects remain UNKNOWN until real measurement later.

Record independently for each check: `case_id`, `module_id`, `check_id`, `candidate_version`, `map_hash`, `vehicle_profile`, `oracle`, `evidence_tier`, `outcome`, `elapsed_ms` if applicable, `notes`. Use **PASS, FAIL, UNKNOWN, UNSUPPORTED, NOT_RUN, NOT_COMPARABLE**, with an explicit difference between source uncertainty and a demonstrated error. A missing lane data source is UNKNOWN, **not** FAIL or PASS. Keep every result and failure across changes. A targeted patch reruns its own checks, adjacent component contract tests, previous failures, followed by held-out and full-drive regressions.

**Speed means three separate things:** vehicle speed/heading correctness, posted or conditional speed limits and warning behaviour, and algorithm/controller response latency. Keep these scores distinct. Distinguish travel ETA from computation time. GPS sources and true phone power use cannot be inferred from a host unit test.

## First executable pass and known limitations

The existing planning-branch code already has unit tests for a bounded OSM importer, legal directed edge routing, shortest-path consistency and reference adapter contracts. **It does not have a current GPS matcher or guidance engine in that branch** (`gps/README.md`, `guidance/README.md` say so), although later research branches contain separate candidate tests and code. Do not mark those modules green just because this inventory names them. The old UK public-road smoke imports only a small historic partial map and compares two **DMN search algorithms**; it is not the comprehensive complex-junction/GPS/ten-engine batch.

The first CI run should validate the entire modular inventory and execute available unit contracts. An explicitly enabled public-UK-road smoke may exercise the existing partial-map routing algorithms. Module cases that currently have no executable capability must appear as **NOT_RUN** until implemented or linked to verified historical artifacts. Subsequent test batches should add difficult UK junctions and independent legal evidence, actual reusable GPS-replay/controller harnesses, and comparable reference implementations before issuing a claimed winner.

Full offline car navigation is an acceptance target; keep the renderer unchanged as a baseline initially but **allow evidence-driven replacement** of road data, graph, map pipelines, GPS, display and any downstream component if that makes navigation better. The existing DriveMate app production branch remains untouched.

### Minimum report output
A **single compact scorecard** by the 14 summary groups, each 0–10 with descending comparable-engine rankings **only after** enough verified evidence and the scoring formula exist. Under it, module-level coverage `judged/planned`, failures, unknown/unrunnable and the link to exact rerunnable scenario evidence. An untested module has no score and cannot be called a win; work on other modules continues.
