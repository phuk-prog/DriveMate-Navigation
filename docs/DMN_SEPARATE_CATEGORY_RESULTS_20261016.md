# DMN — separate-category retest results (16 October 2026)

**Executed, original evidence unchanged.** [Successful research CI run 38899639703](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38899639703) at commit `342be01508f202b97076698a8e91db932d838b12`, job `116968411350`, [raw category-by-category test and failure artifact](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38899639703/artifacts/12045312476). The single CI worker invoked each category in a separate Python process, independently and sequentially to reduce minutes; no test file was omitted or double counted.

**472/472 real unit-test executions passed across 15 categories with runnable modules; eight categories were NOT_RUN (0 executable tests).** These are **software-unit results only**, not 472 real journeys, not independent road accuracy validation and not 23 winning navigation scores.

## All 23 separate categories — logical evidence order

| # | Category | Executed unit tests | Actual result | Interpretation |
|---:|---|---:|---|---|
| 1 | Map data and road graph | 39/39 | UNIT PASS | OSM graph, import and provenance checks; no independently surveyed UK road law. |
| 2 | Road legality and restrictions | 25/25 | UNIT PASS | Mapped one-way, access and turn restriction contract checks; legal truth provisional. |
| 3 | GPS positioning and road matching | 40/40 | UNIT PASS | Map-derived position/heading/candidate tests; no independent real GNSS accuracy. |
| 4 | GPS signal loss and recovery | 68/68 | UNIT PASS | Simulated invalid GPS, missed fixes and reacquisition; no phone/tunnel field proof. |
| 5 | Route computation and validity | 33/33 | UNIT PASS | Actual local route search and frozen input validation tests. |
| 6 | Route quality and preferences | 87/87 | UNIT PASS | Route length/time/cost and preference units, not independently optimal UK routes. |
| 7 | Route calculation speed | 4/4 | UNIT PASS | Timing-worker test methodology and algorithm units; no comparable cross-engine latency ranking. |
| 8 | Junction turns and maneuvers | 6/6 | UNIT PASS | Junction scorer and instruction contract tests; not road-truth verified. |
| 9 | Roundabout exits and paths | 10/10 | UNIT PASS | Synthetic roundabout exit/instruction controls only. |
| 10 | Lane counts and next-turn guidance | 0/0 | **NOT RUN** | Actual UK lane arrows, combined turn/through and best-lane advice not executed. |
| 11 | Route line and turn-point road adherence | 0/0 | **NOT RUN** | Full route-line drift, roundabout arc clipping, wrong-side turn point untested. |
| 12 | Wrong turns and rerouting | 15/15 | UNIT PASS | Rerouting controller state and wrong-turn policies; not full Android real drives. |
| 13 | Navigation instructions and timing | 0/0 | **NOT RUN** | No measured approach/at-turn/after-turn or adaptive spoken timing test. |
| 14 | Traffic, closures and dynamic replanning | 0/0 | **NOT RUN** | Live incident, closure and traffic response tests not executed. |
| 15 | Road section speed limits and alerts | 0/0 | **NOT RUN** | Speed-limit per-section, alert correctness and verified camera checks not executed. |
| 16 | Correct arrival and approach side | 12/12 | UNIT PASS | Arrival state/controller units, not verified driveway/property approach. |
| 17 | Offline routing, maps and updates | 8/8 | UNIT PASS | Host offline navigation package tests; Android downloads/updates not demonstrated. |
| 18 | Voice, Bluetooth and music ducking | 0/0 | **NOT RUN** | Android voice/Bluetooth music ducking not tested. |
| 19 | Failure handling, integrity and safety gates | 65/65 | UNIT PASS | Evidence integrity and readiness gate tests, not full app resilience. |
| 20 | Memory, CPU, energy and map size | 3/3 | UNIT PASS | Synthetic benchmark controls; no equivalent device CPU/RAM/battery measurements. |
| 21 | Complete press-navigate driving | 0/0 | **NOT RUN** | No end-to-end full UK map-replay with actual Android navigation. |
| 22 | Android emulator and app integration | 0/0 | **NOT RUN** | No Android emulator/device integration executed by this unit stage. |
| 23 | Competitor adapters and comparison integrity | 57/57 | UNIT PASS | Adapter contract checks are not live external engine comparisons. |

## Independent named frozen trial results — NOT combined with unit scores

The same green CI also executed its separately named frozen **DMN-only** batches (GPS-002, ROUTE-002, REROUTE-001, JUNCTION-001, ARRIVAL-001, OFFLINE-001, RESOURCE-001) and uploaded artifacts. These are distinct suites and separate *historical/new cohort types*. The successful unit step does **not** replace previously failed actual GPS-003, UK40 regression or other missing real-world gates.

- **GPS-003 (older pinned 2026-09-01 UK map, simulation):** **8/24 full streams passed, 16/24 first-fix failures**; 39 generating-edge matches, 0 confidently wrong, 33 withheld/rejected across 72 observations, 24/24 clear final recoveries; only DMN completed that original temporal contract. [Failure documentation](GPS_003_RESULTS.md) and [nine-case successful diagnostic, no navigation fix](GPS_003_CANDIDATE_DIAGNOSTIC_RESULTS.md).
- **UK40 map-derived temporal GPS (older):** 17/40 correctly matched source fragments, 0 confidently wrong, 23 withheld; seven regression losses remain unresolved, not secretly restored by green unit tests.
- **ROUTE-004 (older 12 identical mapped one-way routing cases):** DMN ★, OSRM, Valhalla, GraphHopper, openrouteservice and BRouter each **12/12** matched the same **provisional OSM** direction contract, ranking **1=** in **that category only**; this new CI did **not** rerun the external-engine comparison, so old results must not be presented as fresh. [Separate dated benchmark](ROUTE_004_RESULTS.md).
- **Routing calculation speed:** the retained ROUTE-004 benchmark measured warm in-process Python routing for DMN and warm local HTTP for competitors on separate CI jobs. It has actual millisecond measurements but **no fair cross-engine speed ranking**. See [original measurements and methodological limits](ROUTE_004_RESULTS.md). The `route_calculation_speed` category's 4/4 are **unit checks**, not four winning live-engine latency comparisons.
- **Junction/roundabout control:** historical synthetic `JUNCTION-001` compared actual eligible engines on five invented cases, but those are **not** independent real UK junction/roundabout or lane instructions. This CI's 6 junction and 10 maneuver tests are isolated Python correctness controls, not a new external benchmark.
- **Android / live navigation readiness:** NOT READY. Independently verified road law, GNSS, lane data, correct approaches, real traffic, cross-system fair timing, complete emulator drives and live safety gates remain unmet.

## Separate failures and coverage gaps

1. **Existing GPS availability problem remains:** 16/24 clear-first-fix stream failures are repetitions at two Moss Lane points. They involve an expected directed fragment and a backward-adjacent same-way fragment ~7.29 and 7.05 m away. No threshold, matcher or oracle was changed by the category runner.
2. **Seven UK40 loss cases remain ambiguous:** competing same-way backward fragments ~5.92–7.43 m away; the historical correct count dropped from 24/40 to 17/40. No confident wrong-road match is proved in this replay, but abstentions are not passes for required first-fix availability.
3. **Eight missing executable unit categories:** lanes, full route-line geometry, navigation instruction timing, live traffic, section speed limits, Android audio/Bluetooth, complete press-navigate journey and Android integration. Their unit results are **NOT_RUN**, not 0/10.
4. **Further evidence still missing beyond unit coverage:** independently verified current road legal movements, complete UK lane markings, on-device GNSS, safe dynamic closure reroutes, location-specific speed limits, real-world journey arrival and a same-worker/same-interface routing-speed comparator. Source-map conformity is not proof of road law.

## Evidence-based DMN improvement proposals — OWNER APPROVAL REQUIRED

1. **GPS reliability and safe first lock (highest priority):** design a tightly scoped *continuous same-way fragment* hypothesis with monotonic forward trajectory confirmation and retained conservative abstention for uncertain branch, reverse progress, parallel road and forbidden movement. **Do not blindly discard backward-adjacent candidates or relax the 12 m competitor band**. Freeze new side-by-side, slip road, tunnel, stationary, adverse-motion and reverse-journey controls, include all earlier GPS-003 and UK40 cases, and gather independent truth. Only after approval implement a bounded fix and freshly rerun DMN plus all genuinely applicable references on identical comparable contracts.
2. **Targeted missing real-road test capabilities:** implement separate public-UK source+verified-oracle/journey cases for full line adherence, roundabout exit numbers, lane source/movements, prompt timing, destination side and safe U-turn/turn legality. Each gets a distinct comparison and issue register.
3. **Real measurement fairness:** use identical worker/profiles/map/time boundaries and at least independently repeated valid routes before ranking computation time. Display median/p95 (ms), cold/warm/setup and route-distance/ETA separately. Comparators that cannot execute the identical contract are audited as not applicable.
4. **Android end-to-end and delivery:** only after navigation-core evidence supports it, run emulator navigation, offline map replacement, Bluetooth/music ducking, complete wrong-turn/reroute/arrival and resource measurement separately, with release robot gating. Leave the private production app/main and APK untouched.

**STOP for owner review.** No GPS matcher behavior, road legality threshold, existing frozen baseline/oracle, private DriveMate application, merge or APK was changed by this category rerun. No follow-up improvement has been implemented.
