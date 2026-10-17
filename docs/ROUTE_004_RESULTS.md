# ROUTE-004 — real-map one-way source-rule baseline

**Status: COMPLETED / PROVISIONAL, owner review pending.** This document consolidates the **already completed** [GitHub Actions run 38873690712](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38873690712) at source commit `9fa0e2a7ac71b25d597b664d7a8e9cbf1de30f04`. No routes have been recomputed for this report. The frozen original source and observations are preserved in that run and the compact [per-engine evidence summary](../references/route004-baseline-20261016.json). The new report **does not** change a matcher, router, acceptance rule or existing failed case.

## What was tested

- **Category:** mapped one-way driving-direction compliance (**not** a generic navigation, GPS, or route-speed score).
- **Map:** pinned historical 1 September 2026 Greater Manchester OSM archive, bounded central-Manchester extract. Six numeric-first eligible ways selected **before engine execution**. Each has one permitted-direction request and one reverse-direction request, identical exact endpoints for all engines: **12 total judged cases per engine**.
- **Checks:** require a route on allowed direction; both endpoints within **8 m**; positive finite route distance and estimated travel time; no *detected direct* route traversal backwards along the selected one-way segment. A reverse-direction NO_ROUTE would have passed the frozen rule, but **all executed reverse requests returned a route** (detour).
- **Deliberate limits:** map-specified `oneway=yes`, source-map agreement only, not verified live road law. Conditional-tag objects/dependants were filtered for **every** engine; turn restrictions, access truth, bicycle/bus exceptions, lane guidance, and illegal turns on other edges are **not** judged by this frozen contract.
- **Map provenance:** archive SHA-256 `b7188b22501b878fddba6e06a90bb44ce6c2d721333e0ca57e10a1a82b568807`; extracted XML SHA-256 `75701973da8551497229f091d142a4231420a22ef220ad165ec52534c3798727`; shared frozen manifest SHA-256 `59876011741fc3c22b13d2075460659649e36659e6149aec2c6bf6a55af442a5`. Original run link above; CI engine/version/job/artifact references in the [structured evidence](../references/route004-baseline-20261016.json).

| Frozen way case | Street | OSM way ID | Class | Direction tag | Cases |
|---|---|---:|---|---|---|
| ROUTE-004-001 | Cobourg Street | 796758 | residential | `yes` | allowed + reverse |
| ROUTE-004-002 | Port Street | 3650028 | residential | `yes` | allowed + reverse |
| ROUTE-004-003 | Spear Street | 3650076 | residential | `yes` | allowed + reverse |
| ROUTE-004-004 | Oldham Street | 3650081 | tertiary | `yes` | allowed + reverse |
| ROUTE-004-005 | York Street | 3663326 | tertiary | `yes` | allowed + reverse |
| ROUTE-004-006 | Fountain Street | 3663335 | tertiary | `yes` | allowed + reverse |

## A. Provisional source-map direction ranking — identical complete cohort

**Actual category measurement: 12 judged source-map direction/route-output cases passed.** Highest to lowest; **all six are tied at rank 1**. The optional 10/10 correctness score is not combined with timing, route quality, or any other navigation category. Because road-law truth is **not independently verified**, there is **no verified legality ranking** from this run.

| Rank | Engine | Passed / total | Failed | Unresolved | Observed median request ms¹ | Nearest-rank p95 ms¹ |
|---:|---|---:|---:|---:|---:|---:|
| 1= | **DMN ★** | 12/12 | 0 | 0 | 0.110 | 0.695 |
| 1= | OSRM | 12/12 | 0 | 0 | 1.039 | 2.275 |
| 1= | Valhalla | 12/12 | 0 | 0 | 2.627 | 52.683 |
| 1= | GraphHopper | 12/12 | 0 | 0 | 7.938 | 103.329 |
| 1= | openrouteservice | 12/12 | 0 | 0 | 3.720 | 103.507 |
| 1= | BRouter | 12/12 | 0 | 0 | 31.531 | 325.733 |

¹ Timing columns are descriptive only, **NOT a cross-engine speed ranking**. DMN uses in-process Python routing, whereas five external engines use warm local HTTP/serialization interfaces; jobs ran on distinct matrix workers, and setup/cold boundaries are not equivalent. Sample size is 12 requests per displayed engine. The nearest-rank p95 with 12 observations equals the largest observation and is not a stable p95 estimate. DMN's displayed timings come from the OSRM job; DMN was also recomputed in the other four reference jobs, showing median per-job times of OSRM 0.110 ms, Valhalla 0.089 ms, GraphHopper 0.098 ms, openrouteservice 0.070 ms, BRouter 0.104 ms. Full timings and raw case values are in the evidence summary.

**Full comparable cohort:** DMN ★ + OSRM 5.27.1 + Valhalla 3.9.1 + GraphHopper 11.1 + openrouteservice 10.1.0 + BRouter 1.7.10, all matched by identical frozen case IDs and hashes. **Partial shared-subset cohort: none** for this run. **Ten-external-engine target not met**: only five external engines completed this same contract.

## B. Exact per-case outcomes, kept separate from issues

| Frozen case/direction | Road | DMN ★ | OSRM | Valhalla | GraphHopper | openrouteservice | BRouter |
|---|---|---|---|---|---|---|---|
| ROUTE-004-001-allowed | Cobourg Street | PASS | PASS | PASS | PASS | PASS | PASS |
| ROUTE-004-001-reverse | Cobourg Street | PASS | PASS | PASS | PASS | PASS | PASS |
| ROUTE-004-002-allowed | Port Street | PASS | PASS | PASS | PASS | PASS | PASS |
| ROUTE-004-002-reverse | Port Street | PASS | PASS | PASS | PASS | PASS | PASS |
| ROUTE-004-003-allowed | Spear Street | PASS | PASS | PASS | PASS | PASS | PASS |
| ROUTE-004-003-reverse | Spear Street | PASS | PASS | PASS | PASS | PASS | PASS |
| ROUTE-004-004-allowed | Oldham Street | PASS | PASS | PASS | PASS | PASS | PASS |
| ROUTE-004-004-reverse | Oldham Street | PASS | PASS | PASS | PASS | PASS | PASS |
| ROUTE-004-005-allowed | York Street | PASS | PASS | PASS | PASS | PASS | PASS |
| ROUTE-004-005-reverse | York Street | PASS | PASS | PASS | PASS | PASS | PASS |
| ROUTE-004-006-allowed | Fountain Street | PASS | PASS | PASS | PASS | PASS | PASS |
| ROUTE-004-006-reverse | Fountain Street | PASS | PASS | PASS | PASS | PASS | PASS |

Every PASS denotes only the five specific checks above; it is **not** independent road-law certification. See the compact [72-case individual metric record](../references/route004-baseline-20261016.json) for expected case IDs, actual verdicts, each returned distance, ETA, per-request calculation time, and reasons. The **five repeated DMN measurements** are labelled distinctly from the six independent systems; they are not five additional navigation engines.

## C. Issues, failures, uncertain facts — separate from the ranking

**Verified navigation-engine failures in the frozen judged contract: 0/72.** No confirmed DMN defect is established by this comparison. There are meaningful **limitations and provisional differences**:

| Priority | Finding | Evidence/classification | Recommended follow-up (approval required) |
|---|---|---|---|
| 1 | Independent one-way road-law truth missing on the six UK ways | **UNRESOLVED source-truth gap**: OSM tags cannot alone establish current lawful directions. | Check dated traffic orders, signed restrictions, roadworks/imagery as legally accessible; record source/date and conflicting facts. |
| 2 | Reverse-direction detector could miss a route travelling backwards through **multiple small geometry segments** | **Harness defect corrected prospectively on 17 October 2026**: the original detector required one jump from projection ≥0.8 to ≤0.2. Frozen analytical controls now require detection across multiple contiguous in-corridor points while rejecting forward travel, an off-corridor detour and an incomplete fragment. All 5/5 controls pass at `9da6f6737daa91e41238dde177f7dd93226cb2da`. No historical route was rescored and no real engine failure was inferred. | Use the corrected detector in a future freshly authorized comparable route execution; preserve this run's original verdicts. |
| 3 | Allowed-direction route need not actually use the nominated one-way edge | **Harness coverage gap**: existing checks require endpoint/distance/ETA, not full directed selected-edge coverage. | Define and freeze an explicit full-path containment/progression contract on known geometry; do not retroactively rescore this run. |
| 4 | Possible route-quality gap on York Street reverse direction | **PROVISIONAL, not an engine failure**: DMN 251.6 m and BRouter 251.0 m, against GraphHopper 170.9 m, OSRM 171.4 m, openrouteservice 170.8 m, Valhalla 184.0 m. Profiles differ and independent fastest-legal-route truth is absent. | In a **separate route-quality test**, verify that compared routes share legal constraints and independently assess shorter valid alternatives. |
| 5 | Turn prohibitions, roundabouts, GPS matching, speed-limit/traffic and lane conditions were not checked | **NOT TESTED** by ROUTE-004. Conditional-tagged objects and dependants were excluded from map input. | Keep these as separate named categories, not hidden within a one-way score. |

**Unsupported / not-run audit (not zero scores):** Itinero and Routino have different earlier 3-case real-map output probes, not this 12-case contract. OsmAnd and Organic Maps lack a completed equivalent native/app harness; HERE, Mapbox, TomTom and Google Maps lack permitted configured access for this common test; Waze has no established permitted automated interface. No competitor is silently substituted or assigned a synthetic verdict.

## D. Next improvements and review gate

**Do not change DMN navigation behaviour as a result of these passing source-map checks.** First review the source-truth and harness limitations above. An improvement to ROUTE-004 judgement would require your approval, a new frozen labelled experiment, and actual reruns rather than relabelling historical data. Separately, the previously documented **GPS-003** first-fix coverage deficit (16/24 failed streams) and older UK **17 correct / 0 confidently wrong / 23 withheld** replay remain higher-priority navigation investigations.

No DMN matcher thresholds have been weakened, no route code changed, no new comparator run started, and no live-app readiness claimed. Per the owner's permanent [six-rule policy](DMN_PERMANENT_TESTING_POLICY.md), **STOP for owner review** before fixes or any next test.

### Prospective detector correction evidence

The separately frozen `ROUTE-004-DETECTOR-1` analytical harness check passes
**5/5** cases: single- and multi-segment reverse traversal are detected; forward
travel, a route that leaves the 8 m corridor, and an incomplete reverse fragment
are not falsely marked as a complete forbidden traversal. Fixture SHA-256:
`3b2661d82a45f2751a6141dd68ea2b2b0d8a07f60e3326f2a088228514950791`.
[Exact case evidence](../references/route004-detector-controls-20261017.json).
This corrects only the prospective scorer. The six-engine table above remains
the immutable historical baseline and therefore has not been recalculated.

## Run/measurement links

- [Original successful GitHub Actions matrix and artifacts](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38873690712)
- [Per-case persistent compact JSON evidence](../references/route004-baseline-20261016.json)
- Original versioned data: job artifacts `route004-OSRM`, `route004-Valhalla`, `route004-GraphHopper`, `route004-openrouteservice`, `route004-BRouter`. The original artifacts' current expiry is 15 November 2026; job run links remain available subject to GitHub retention.
