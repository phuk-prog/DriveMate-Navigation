# DMN engine-only approved improvement batch — final tested result

**16 October 2026, existing research branch.** The active scope is only the **DriveMate Navigation (DMN) engine**: no Android, app, emulator, UI, Bluetooth/audio, APK, or production DriveMate tests/changes.

- [Final strict engine-only unit workflow](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38904037336) — **SUCCESS**, 506/506 units, 21 distinct engine categories, 0 untested unit categories. [All per-category verdicts](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38904037336/artifacts/12046204399). This excludes the two earlier app-readiness unit tests and has no app-adoption report stage.
- [Frozen GPS-003/UK40 research variant comparison](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38903461428) — **SUCCESS**; [complete per-fix JSON artifact](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38903461428/artifacts/12046628920). Its same pinned historical Greater Manchester OSM extract and frozen oracle were hash-verified; original historical evidence stays untouched.

## 1. GPS comparison on equivalent frozen UK map-derived observations

| Measurement | DMN ★ default | DMN experimental opt-in | Outcome |
|---|---:|---:|---|
| GPS-003 complete stream cases passing | 8/24 | **24/24** | +16 |
| UK40 generating road-fragment matches | 17/40 | **22/40** | +5 |
| UK40 withheld (not safely assigned) | 23/40 | **18/40** | 18 unresolved |
| Confident wrong-road matches | 0 observed | **0 observed** | No recorded increase |

**Result scope:** actual DMN-versus-DMN-version comparison only; all GPS observations are **simulated using actual OSM road geometry**, so this is **PROVISIONAL map-source agreement**, not independently surveyed UK car GPS/road law. There is no executed common external-GPS-stream ranking for this experiment. Zero observed wrong edges in this limited source-generated replay cannot establish safety on real roads.

New GPS feature `experimental_adjacent_fragment_equivalence=True` is **off by default**. It is a bounded research hypothesis for suppressing a worse same-way, same-direction, gently bending, immediately adjacent mapped fragment only with good reported moving position, heading, mapped allowed connection and clear separation. The previous default `12 m` ambiguity guard and original frozen acceptance were not altered. Do not promote this candidate to the default without independent position/safety evidence and mandatory fresh affected competitor retesting.

## 2. All active engine categories, tested independently in driving order

| # | Navigation-engine category | Passed/total | Evidence meaning |
|---:|---|---:|---|
| 1 | Map data and road graph | 39/39 | Analytical/source/engine unit only: OSM graph, import and provenance checks; no independently surveyed UK road law. |
| 2 | Road legality and restrictions | 25/25 | Analytical/source/engine unit only: Mapped one-way, access and turn restriction contract checks; legal truth provisional. |
| 3 | GPS positioning and road matching | 48/48 | Analytical/source/engine unit only: Map-derived position/heading/candidate tests; no independent real GNSS accuracy. |
| 4 | GPS signal loss and recovery | 68/68 | Analytical/source/engine unit only: Simulated invalid GPS, missed fixes and reacquisition; no phone/tunnel field proof. |
| 5 | Route computation and validity | 33/33 | Analytical/source/engine unit only: Actual local route search and frozen input validation tests. |
| 6 | Route quality and preferences | 87/87 | Analytical/source/engine unit only: Route length/time/cost and preference units, not independently optimal UK routes. |
| 7 | Route calculation speed | 9/9 | Analytical/source/engine unit only: Timing-worker test methodology and algorithm units; no comparable cross-engine latency ranking. |
| 8 | Junction turns and maneuvers | 6/6 | Analytical/source/engine unit only: Junction scorer and instruction contract tests; not road-truth verified. |
| 9 | Roundabout exits and paths | 10/10 | Analytical/source/engine unit only: Synthetic roundabout exit/instruction controls only. |
| 10 | Lane counts and next-turn guidance | 4/4 | Analytical/source/engine unit only: Analytical OSM lane-arrow parser/unknown gates only; real UK lane signage and next-lane guidance unverified. |
| 11 | Route line and turn-point road adherence | 4/4 | Analytical/source/engine unit only: Route-vs-directed-graph geometry/turn-control tests only; no independent UK road-line survey. |
| 12 | Wrong turns and rerouting | 15/15 | Analytical/source/engine unit only: Rerouting controller state and wrong-turn policies; not full Android real drives. |
| 13 | Navigation instructions and timing | 4/4 | Analytical/source/engine unit only: Deterministic approach/turn timing confidence gates only; no Android voice timing. |
| 14 | Traffic, closures and dynamic replanning | 5/5 | Analytical/source/engine unit only: Simulated freshness/closure input policy only; no live traffic feed tested. |
| 15 | Road section speed limits and alerts | 3/3 | Analytical/source/engine unit only: OSM speed-unit and unknown handling only; road signs and enforcement unverified. |
| 16 | Correct arrival and approach side | 12/12 | Analytical/source/engine unit only: Arrival state/controller units, not verified driveway/property approach. |
| 17 | Offline routing, maps and updates | 8/8 | Analytical/source/engine unit only: Host offline navigation package tests; Android downloads/updates not demonstrated. |
| 18 | Failure handling, integrity and safety gates | 63/63 | Analytical/source/engine unit only: Engine reliability, privacy, benchmark integrity and no-false-ranking safeguards; app readiness excluded. |
| 19 | Memory, CPU, energy and map size | 3/3 | Analytical/source/engine unit only: Synthetic benchmark controls; no equivalent device CPU/RAM/battery measurements. |
| 20 | Complete navigation-engine journey | 3/3 | Analytical/source/engine unit only: Actual DMN core components on analytically invented geometry; no physical drive, app or Android. |
| 21 | Competitor adapters and comparison integrity | 57/57 | Analytical/source/engine unit only: Adapter contract checks are not live external engine comparisons. |

The new categories have working unit checks for lane-tag turn/through representation, geometry/turn-point conformance and corner-cutting, reliable approach-turn guidance timing, traffic/closure input freshness, per-road speed evidence and **complete engine replay** comprising route selection, GPS matching, wrong-turn rerouting, guidance decisions and arrival. All are engine source/software tests; the current end-to-end engine replay uses *invented analytical roads*, **not** a real UK drive or app integration.

## 3. Engine rankings and actual timing — evidence boundaries

The previously executed [ROUTE-004](ROUTE_004_RESULTS.md) (not rerun in this batch) remains the only six-engine common **12-case mapped one-way** cohort: DMN ★, OSRM, Valhalla, GraphHopper, openrouteservice and BRouter are tied **1= at 12/12** under the **provisional map-source direction** contract, not independently verified UK road law. Do not use this historical result as a new benchmark.

**No fresh fair cross-engine routing-speed order was generated.** Historical DMN in-process Python request measurements and external loopback HTTP on different GitHub workers have incompatible boundaries. The new timing comparability unit gate rejects such data. To publish highest-to-lowest calculation milliseconds/p95, independently run each applicable engine on the same cases/map/profile/hardware and equivalent request boundary, with valid actual routes and distinct timing tables. Likewise do not claim GPS/lanes/roundabouts/live traffic external-engine rankings without executing applicable independent cohorts.

## 4. Remaining confirmed issues and proposed engine improvements

| Priority | Fault or missing evidence | Next engineering step |
|---|---|---|
| High | 18/40 UK40 road-fragment outcomes remain withheld by the opt-in candidate | Examine case-level data/candidate geometry, include unrelated parallel roads and reversals, and maintain anti-wrong-road safety constraints |
| High | No independent real UK road-law/vehicle GNSS ground truth | Freeze source-dated real Manchester road/junction cases and acquire independent, lawful corroboration without guessing |
| High | No compatible GPS streaming competitor cohort | Test applicable engines on one separately frozen shared position/heading contract; keep streaming-only functionality separate if unavailable |
| High | Calculation time lacks comparable cross-engine hardware/API scope | Execute dedicated same-worker timed route trials with millisecond median/p95, cold/warm/setup, correct/total and per-case failures |
| High | Lane, traffic, speed limit, instruction and geometry checks remain analytical | Extend them with independently verified real UK map/junction/lane/road restriction evidence |
| Medium | Complete journey engine test is currently an analytical graph | Expand to full real-UK-road source-backed press-navigate **engine** replay with actual route geometry, induced wrong-turn/replan and destination-side arrival |
| Medium | Reference engines have different supported APIs/profiles | Retain full-cohort versus partial-cohort rankings and never invent unavailable results |

**Review gate:** Unit success is not road-navigation certification. Proposed improvement remains **disabled in default DMN**, no navigation behaviour was promoted, and no DriveMate app work happened. Further safety trials and any change enabling the GPS research candidate require owner review; a subsequent approved active behavioural change requires fresh retests of DMN **and every available applicable competitor** over the full affected frozen shared cases.

**Project state:** Implemented source/tests and finished two successful GitHub workflows; no merge or release performed.

## Subsequent GPS dual-matcher CI execution — 16 October 2026

[Both-method shadow rerun and its full per-case evidence](DMN_GPS_SHADOW_RESULTS_20261016.md) supersedes no earlier evidence. The unchanged default retained 8/24 GPS streams and 17/40 UK40 source matches, while the isolated research matcher returned 24/24 and 22/40. Unit checks increased from 506 to **511/511** (all 21 engine categories passed). No newly confident wrong-road selections were observed. This remains simulated/map-derived research; original matcher remains authoritative. No production/Android work.
