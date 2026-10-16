# DMN independent navigation test categories — 16 October 2026

**Owner's revised choice:** Execute each navigation piece as its own test contract, in logical driving order, with independent failures, timings, and actual head-to-head rankings **only for engines that ran the identical contract**. One GitHub CI worker runs the unit-test category subprocesses sequentially to save runner resources; this does not combine their results. This catalogue is not a claim that all real-world or competitor tests exist.

| Order | Category | Existing unit test files | Evidence limit |
|---:|---|---:|---|
| 1 | Map data and road graph | 6 | OSM graph, import and provenance checks; no independently surveyed UK road law. |
| 2 | Road legality and restrictions | 4 | Mapped one-way, access and turn restriction contract checks; legal truth provisional. |
| 3 | GPS positioning and road matching | 5 | Map-derived position/heading/candidate tests; no independent real GNSS accuracy. |
| 4 | GPS signal loss and recovery | 8 | Simulated invalid GPS, missed fixes and reacquisition; no phone/tunnel field proof. |
| 5 | Route computation and validity | 4 | Actual local route search and frozen input validation tests. |
| 6 | Route quality and preferences | 9 | Route length/time/cost and preference units, not independently optimal UK routes. |
| 7 | Route calculation speed | 1 | Timing-worker test methodology and algorithm units; no comparable cross-engine latency ranking. |
| 8 | Junction turns and maneuvers | 1 | Junction scorer and instruction contract tests; not road-truth verified. |
| 9 | Roundabout exits and paths | 1 | Synthetic roundabout exit/instruction controls only. |
| 10 | Lane counts and next-turn guidance | None — NOT_RUN | Actual UK lane arrows, combined turn/through and best-lane advice not executed. |
| 11 | Route line and turn-point road adherence | None — NOT_RUN | Full route-line drift, roundabout arc clipping, wrong-side turn point untested. |
| 12 | Wrong turns and rerouting | 3 | Rerouting controller state and wrong-turn policies; not full Android real drives. |
| 13 | Navigation instructions and timing | None — NOT_RUN | No measured approach/at-turn/after-turn or adaptive spoken timing test. |
| 14 | Traffic, closures and dynamic replanning | None — NOT_RUN | Live incident, closure and traffic response tests not executed. |
| 15 | Road section speed limits and alerts | None — NOT_RUN | Speed-limit per-section, alert correctness and verified camera checks not executed. |
| 16 | Correct arrival and approach side | 1 | Arrival state/controller units, not verified driveway/property approach. |
| 17 | Offline routing, maps and updates | 1 | Host offline navigation package tests; Android downloads/updates not demonstrated. |
| 18 | Voice, Bluetooth and music ducking | None — NOT_RUN | Android voice/Bluetooth music ducking not tested. |
| 19 | Failure handling, integrity and safety gates | 11 | Evidence integrity and readiness gate tests, not full app resilience. |
| 20 | Memory, CPU, energy and map size | 1 | Synthetic benchmark controls; no equivalent device CPU/RAM/battery measurements. |
| 21 | Complete press-navigate driving | None — NOT_RUN | No end-to-end full UK map-replay with actual Android navigation. |
| 22 | Android emulator and app integration | None — NOT_RUN | No Android emulator/device integration executed by this unit stage. |
| 23 | Competitor adapters and comparison integrity | 10 | Adapter contract checks are not live external engine comparisons. |

## How to read each result

- **UNIT_PASS / UNIT_FAIL**: actual separate Python unit tests executed; these measure software contract conformance, **not** real-world road truth, correct navigation under all conditions, or engine superiority.
- **NOT_RUN**: no implemented unit test assigned to this category; a gap requiring independently authorized implementation and a frozen oracle.
- **Real-UK provisional comparative ranking**: publish only where the same properly scoped frozen public-road case contract actually ran on multiple engines; show engines highest to lowest by the actual metric. GPS-003 was DMN-only, not a six-engine GPS stream comparison. ROUTE-004 has a separate five-external-engine common cohort with 12/12 provisional mapped-direction passes and 0 frozen failures.
- **Timing**: report actual milliseconds, setup and host boundaries, median/p95 and sample count; speed does not rank across DMN in-process and external HTTP/other CI-worker times.
- **Failures and proposed improvements**: enumerate exact failing cases; put evidence-backed improvement proposals at the **end** of every category report. Owner must authorize navigation behaviour changes before implementation; then freshly rerun DMN and all applicable competitors on identical affected frozen cases.

## Proposed GPS improvement, design-only — NOT IMPLEMENTED

The [bounded diagnostics](GPS_003_CANDIDATE_DIAGNOSTIC_RESULTS.md) demonstrated that first-fix GPS-003 alternatives on Moss Lane are two backward-adjacent fragments of the same way, 7.289 m and 7.048 m from the generated positions. Seven distinct older UK40 lost matches also have backward-adjacent same-way competitors.

**Design for review (no thresholds changed):** distinguish segment identity from physical road identity, require trusted *forward* progress evidence before treating backward adjacent segments as one supported continuing road, preserve separate real carriageways and branches, preserve mapped prohibited turns, and withhold instead of asserting a fragment when topology/road truth or recent GPS disagree. Never choose an edge because it is the generating fixture label. Do not loosen the universal proximity/confidence threshold. Candidate configurations and their safety trade-offs must be presented for approval before changing `gps/matcher.py` or `gps/temporal_matcher.py`.

**Necessary future independently frozen checks:** both original Moss Lane GPS-003 starting positions, all seven UK40 regression cases, actual route-level wrong-road and unsafe U-turn counterexamples, consecutive GPS along a bend, backward-progress trajectory, two nearby one-way roads, dual carriageways, slip/service roads, stationary fixes, multiple poor fixes, tunnel dropout and reconnect, and independently corroborated current UK road geometry/legal directions. Score withheld/unknown separately from confident wrong-road and correct first fix. After owner authorization of a behavioural change, retest all original cases and all applicable comparable external references rather than reuse previous competitor outcomes.

## Execution commands

```bash
python -m tools.category_test_runner --all --output-dir results/category-checks
python -m tools.category_test_runner --category gps_matching --output-dir results/category-checks
```

CI saves `results/category-checks/index.json`, `summary.md` and 23 separate category JSON case records as one audit artifact; no historical frozen source evidence is rewritten. CI's other, named independent DMN benchmarks remain in place. This unit suite does **not** launch heavyweight reference providers or create a fake all-engine ranking.


## Most recent executed category unit retest — 16 October 2026

[Executed unit results in logical order](DMN_SEPARATE_CATEGORY_RESULTS_20261016.md)
from [successful CI run 38899639703](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38899639703) show **15 categories with runnable tests, all 472/472 units passing**, and **eight categories explicitly NOT_RUN**, not passed. This result does not change the earlier 16/24 GPS-003 stream availability failure or the 17/40 UK matching regression. Cross-engine ratings and route-calculation milliseconds require separately executed comparable contracts; no new comparative ranking was run here. Proposed DMN improvements are listed at the end of the result report for owner review.
