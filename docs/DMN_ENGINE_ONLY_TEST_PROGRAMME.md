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


### Strict engine-only CI exclusion

The legacy `tests/test_app_readiness.py` remains in repository history for audit
but is explicitly excluded from active category execution; the separate
`tools.app_readiness` and adoption-artifact stage have been replaced by an
engine comparison evidence-integrity check. No Android app, Bluetooth or
production readiness test runs as part of this engine-only programme.


## Final tested research-batch results

[View verified **strict engine-only** result and GPS before/after](DMN_ENGINE_ONLY_RESULTS_20261016.md): 21 separately executed engine categories, 506/506 unit checks passing, no legacy app tests, pinned Manchester GPS-003 default 8/24 versus research option 24/24, UK40 default 17/40 versus research option 22/40, 0 confidently wrong-road selections in these simulated test cases. The opt-in GPS candidate is **off by default**, 18 UK40 withheld remain and independent real-road validation is outstanding.

## Both GPS matchers retained — parallel research evidence

The conservative DMN matcher remains the **authoritative/default** navigation result.
The opt-in adjacent-fragment matcher remains available as a shadow comparison and
is never silently selected for guidance. The test helper
`gps/shadow_comparison.py` feeds each observation into **separate temporal
matchers**, returning the baseline answer and the experimental answer. Any
shadow-only error is exposed without replacing the baseline.

Independent GPS-matching unit tests execute in the normal 21-category CI suite.
For changes to the GPS matcher, temporal matcher, comparison benchmark or
diagnostic workflow, the bounded historical GPS-003/UK40 workflow runs both
variants on the same pinned map and frozen observations. Its artifact now records
every changed stream, individual GPS update and UK40 case, including original
versus experimental road IDs. Other categories do not become GPS tests and
unrelated documentation commits do not trigger historical map downloads.

**No navigation behaviour is disabled or replaced.** No Android app, APK or
production project is involved. A shadow improvement in map-generated data does
not justify enabling it for navigation or relaxing an existing safety gate.
