# DMN — dual GPS matcher shadow comparison and independent engine retest

**16 October 2026, successfully executed.** [Full pinned historical GPS-003/UK40 run](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38914756822) (artifact [12051379163](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38914756822/artifacts/12051379163)), and [normal engine category test run](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38914756154) (artifact [12051448008](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38914756154/artifacts/12051448008)). Commit `1fa8804185294af84ed4ce6b089c8a6aa3e091ca` on the existing research PR. Neither run tested the Android app.

## Both GPS algorithms kept available

Two separate `TemporalRoadMatcher` states consume the same GPS observation; the conservative/default matcher remains authoritative, while the optional adjacency-fragment matcher is research-only. The shadow output logs both directed-road IDs, statuses and disagreements; it cannot promote an experimental result to guidance. The original matcher and its confidence/acceptance thresholds remain unchanged. A separate shadow failure is visible without concealing the baseline result. Tests now exercise this safeguard.

The bounded frozen-map GPS workflow runs automatically on GPS algorithm or corresponding harness changes, not on unrelated documentation. Hash-pinned historical OSM and unchanged oracles are reused. It does not confer independent GNSS/road-law truth.

## Exact new frozen-map comparison measurements

| Measurement | Default DMN ★ | Shadow research candidate | Interpretation |
|---|---:|---:|---|
| GPS-003 stream passes | 8/24 | **24/24** | +16 source-map stream passes |
| UK40 source-fragment correct | 17/40 | **22/40** | +5 source-map correct |
| UK40 withheld | 23/40 | **18/40** | 18 still unresolved |
| Confident wrong-road results | 0 observed | **0 observed** | No observed increase in sampled generated inputs |
| Changed GPS-003 stream outcomes | — | **16** | Per-case audit in new artifact |
| Changed GPS-003 individual event matches | — | **18** | Includes stream samples and reason/edge details |
| Changed UK40 matched cases | — | **5** | Per-case audit in new artifact |

**No independent real-road GPS truth** was used: the map geometry generated the simulated observations. Neither matcher has established real-world safety or superiority over independent competitors. The research candidate is not enabled in the authoritative navigation path.

## All existing engine categories rerun separately

The normal CI run executed **21/21 navigation-engine categories** with **511/511 Python unit checks passing**, including 53/53 tests in GPS positioning/matching and five new shadow-isolation checks. No Android app test, APK or integration work. These are software and analytical conformance checks, **not 511 real UK driving trials**. Full category case artifacts remain in the linked successful run.

## Ranked comparisons and next issues

The historical six-engine ROUTE-004 mapped one-way cohort remains a six-way first-place tie at 12/12 per engine and was **not freshly rerun** as part of this GPS-only change. Calculation-speed rankings for unlike in-process/HTTP and different-worker scopes are still **NOT COMPARABLE**, not a DMN speed victory.

Further improvements (not yet authorized for default behaviour): independently source UK vehicle/road truth; analyse the 18 still-withheld UK40 cases; add adversarial opposite-carriageway, reverse-progress, slip-road, roundabout and weak-GNSS trails; implement genuine applicable external map-matching comparisons under identical contracts; perform valid matched-scope route-speed trials. After any owner-approved default behavioural change, freshly rerun all applicable competitors on the complete affected common case set.

**STOP for safety review before promoting the shadow candidate.** No matcher was disabled and neither was removed. No production application, merge or APK was changed.
