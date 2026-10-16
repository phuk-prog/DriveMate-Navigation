# DriveMate Navigation — engine-only test programme (active scope)

**Owner directive:** Only the independent **DMN navigation engine** is in scope. No Android application, user-interface, Bluetooth, music, speech synthesis, emulator, APK or production DriveMate repository test/build/release work. The older 23-category table is historical; the current active programme has the following **21 navigation engine categories**, each measured separately.

| # | Engine category | Unit test files | Evidence classification |
|---:|---|---:|---|
| 1 | Map data and road graph | 6 | OSM graph, import and provenance checks; no independently surveyed UK road law. |
| 2 | Road legality and restrictions | 4 | Mapped one-way, access and turn restriction contract checks; legal truth provisional. |
| 3 | GPS positioning and road matching | 7 | Map-derived position/heading/candidate tests; no independent real GNSS accuracy. |
| 4 | GPS signal loss and recovery | 8 | Simulated invalid GPS, missed fixes and reacquisition; no phone/tunnel field proof. |
| 5 | Route computation and validity | 4 | Actual local route search and frozen input validation tests. |
| 6 | Route quality and preferences | 9 | Route length/time/cost and preference units, not independently optimal UK routes. |
| 7 | Route calculation speed | 2 | Timing-worker test methodology and algorithm units; no comparable cross-engine latency ranking. |
| 8 | Junction turns and maneuvers | 1 | Junction scorer and instruction contract tests; not road-truth verified. |
| 9 | Roundabout exits and paths | 1 | Synthetic roundabout exit/instruction controls only. |
| 10 | Lane counts and next-turn guidance | 1 | Analytical OSM lane-arrow parser/unknown gates only; real UK lane signage and next-lane guidance unverified. |
| 11 | Route line and turn-point road adherence | 1 | Route-vs-directed-graph geometry/turn-control tests only; no independent UK road-line survey. |
| 12 | Wrong turns and rerouting | 3 | Rerouting controller state and wrong-turn policies; not full Android real drives. |
| 13 | Navigation instructions and timing | 1 | Deterministic approach/turn timing confidence gates only; no Android voice timing. |
| 14 | Traffic, closures and dynamic replanning | 1 | Simulated freshness/closure input policy only; no live traffic feed tested. |
| 15 | Road section speed limits and alerts | 1 | OSM speed-unit and unknown handling only; road signs and enforcement unverified. |
| 16 | Correct arrival and approach side | 1 | Arrival state/controller units, not verified driveway/property approach. |
| 17 | Offline routing, maps and updates | 1 | Host offline navigation package tests; Android downloads/updates not demonstrated. |
| 18 | Failure handling, integrity and safety gates | 11 | Evidence integrity and readiness gate tests, not full app resilience. |
| 19 | Memory, CPU, energy and map size | 1 | Synthetic benchmark controls; no equivalent device CPU/RAM/battery measurements. |
| 20 | Complete navigation-engine journey | 1 | Actual DMN core components on analytically invented geometry; no physical drive, app or Android. |
| 21 | Competitor adapters and comparison integrity | 10 | Adapter contract checks are not live external engine comparisons. |

## Evidence grades and reporting

- **UNIT_CONTRACT** means local Python correctness only. It does not prove driving accuracy, the right lane, independent road truth or a cross-engine winner. In the previous completed run, 506/506 engine category units passed at commit `be981f0` (see [GitHub Actions](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38902924203)).
- **MAP_PROVISIONAL** means actual map-derived case outputs, separately compared by named category only. Retain original GPS-003 8/24 and UK40 17/40 matcher coverage deficits until an executed test shows a real change. Independently VERIFIED physical UK-road evidence must be separately sourced.
- **MATCHED_EXTERNAL** means competitor engines actually executed exactly the same applicable category contract on equivalent frozen cases, with full and partial cohorts clearly separated.
- **TIMING_COMPARABLE** requires the same worker, map/profile, interface, route set, cold/warm stage and boundary. Old DMN in-process versus competitor HTTP timings are **observations only**, never a valid time ranking. No speed result can conceal an invalid, illegal, or confidently wrong route.
- **NOT_RUN / UNSUPPORTED** are not zeroes or passes. Preserve category gaps, individual failures, measured units and the precise source/CI link.

## Approved coordinated engine improvements

1. Opt-in same-way fragment GPS matching hypothesis, **disabled by default**, with conservative geometry, heading, quality and directed-turn guards. Unlike a real improvement, an opt-in variant is not eligible for production until it passes independent safety proof.
2. Frozen Manchester GPS-003/UK40 default vs opt-in experiment, writing new outputs only and preserving original immutable acceptance/hashes. Any confidently wrong edge is an explicit failure.
3. Separate OSM lane/turn-through tags, route-line/turn geometry checks, instruction decision/timing model, fresh vs stale closure policy, and per-section OSM speed evidence. These are engine-only policy and data contracts; not independent UK signage or live traffic verification.
4. Complete **engine** route/GPS/guidance/reroute/arrival analytical replay; no Android and no claims of real driving.
5. Calculation-time comparability screen rejects invalid mixed-interface or multi-host rankings. Full controlled cross-engine speed benchmarking is a separate named experiment, not a unit-test timing score.

**After each test:** present the individual case pass/fail list, highest-to-lowest comparative rankings only where actually measured, scoped timings, unknown truth, and **improvement suggestions last**. Before enabling the GPS variant or any navigation behaviour change beyond the isolated research experiment, stop and require owner review. Freshly rerun every applicable real competitor on the entire affected common frozen comparison if a behavioural change is approved.

Keep heavyweight external engines sequential and use version-pinned public sources. No changes to the private app, no APK, no merge without separate approval.
