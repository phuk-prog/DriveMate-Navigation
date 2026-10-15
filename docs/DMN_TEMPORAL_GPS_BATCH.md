# DMN fifth research batch — conservative temporal GPS road matching

**New component:** `gps/temporal_matcher.py` builds on the approved isolated GPS input gate and stateless directed-road candidate matcher. It uses previous unambiguously identified link, timestamp and legal directed graph continuity. It will only resolve an ambiguous GPS point when exactly ONE nearby heading/position-consistent directed road is reachable from an adequately recent confirmed link without traversing a mapped forbidden turn. Stopped, headingless, poor-accuracy, time-expired, disconnected, opposite-heading and legal-branch ambiguous events remain **UNKNOWN/AMBIGUOUS**. No phone sensor data is stored or uploaded.

**Test plan:** same pinned public Geofabrik Greater Manchester extract and **identical map-derived two-fix route snippets** for single-fix baseline and temporal candidate. Small component synthetic fixtures cover difficult branches, confirmed prohibited turns, duplicate/spike fixes, resets, long tunnel-like signal gaps and ambiguous parallel roads. The real-UK public-map experiment selects at most 40 legal directed consecutive-edge pairs, creates controlled coordinate fixes on those roads, and measures exact numerators/denominators: total selected, truly anchored first fixes, confident correct vs confident wrong vs withheld at second fix, safely rejected speed spikes, safely withheld weak fixes, and rescued previously ambiguous outcomes.

**Strict evidence caveat:** OSM-derived test truth is shared with the tested matcher, no surveyed real vehicle GPS. The public roads are real, but GPS observations are injected. No UK independent legal traffic oracle, sensor fusion, true speed display, phone power consumption, lane matching, full-navigation arrival, ten-engine comparison or 0–10 score. Maintain the research branch; production DriveMate and release APK untouched.

## First validation and explicit real-road experiment

[GitHub run 38742408817](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38742408817) **passed 176/176 Python unit/contract tests** after correcting a fixture which had placed an intended ambiguous road reading on a feeder. The first failure was a test-data positioning error, not evidence of incorrect live GPS behavior. Independent temporal module tests include legal restricted transitions, disconnected roads, close parallel roads, headingless stops, missed/stale/rejected fixes, and old-anchor expiry. The real public UK replay is being explicitly requested as a separate opt-in experiment; do not report its counts until verified in the Actions output.

## Verified first public UK two-fix comparison (15 October 2026)

**GitHub Actions:** [run 38742626225](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38742626225) — **success**, aggregate artifact `dmn-public-uk-temporal-gps-comparison`, pinned Geofabrik Greater Manchester 2026-09-01 public map extract SHA-256 `b3a883ae9b7c85072d24afeee7a1079aea00c22264516a0e1e71d49221ad27d5`. The unit suite was **176/176 passed**; it includes module/benchmark contract tests, NOT 176 independently judged GPS drives.

| Identical two-fix map-derived journey cohort | Single fix | New multi-fix |
|---|---:|---:|
| Geometry-generated two-edge UK scenarios examined | 40 | 40 |
| Correct confident directed-edge matches | 17 | **24** |
| Confidently incorrect road matches | 0 | **0** |
| Withheld or uncertain second readings | 23 | **16** |
| Extra formerly withheld situations correctly resolved | — | **7** |

**31/40** first readings were confidently anchored to the generated incoming road, so the temporal engine had valid prior information in only those scenarios. Both implementations used the **same original OSM source and test readings**. 40/40 obviously impossible reported speeds were rejected and 40/40 weak accuracy readings were not confidently snapped in the tested multi-fix paths. This is a **controlled route-topology algorithm comparison, not external-engine ranking or real GPS ground truth**.

**Gaps discovered:** 16 second readings remain withheld, including cases with inadequate initial anchors or multiple plausible legal turns. The next component test should use three to five readings, valid/invalid alternating fixes, frequent close parallel same-direction roads, tunnels/stacked junctions and independently checked movement rules. Add map-matching CPU, memory and correctness benchmarks, then integrate test-only Android emulator replays after navigation controller interfaces exist. Avoid performance estimates without identical host input.

**Protection:** the benchmark now has a nonregression gate: a change that creates *more confidently wrong* road matches on this identical cohort fails testing rather than hiding behind a higher match count. It also rejects inconsistent denominators. This gate is an engineering safety minimum, **not proof that 0 wrong in this tiny controlled sample means 0 wrong in real driving**.
