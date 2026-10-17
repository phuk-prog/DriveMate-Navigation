# DMN GPS — all 18 remaining UK40 ambiguities: executed diagnosis

**16 October 2026 · Completed · Navigation-engine research only.** The bounded [pinned-map GPS diagnostic](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38915981032) succeeded at research commit `e6979d41c2a7ba8409eb35916344e825c06fb69b`, with [full per-candidate source-geometry JSON artifact](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38915981032/artifacts/12052362302). The independent [21-category engine-only checks](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38915980817) also succeeded; [category verdicts](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38915980817/artifacts/12052187547).

## Precisely measured outcome

The experimental same-way GPS candidate remains at **22/40 generating-fragment matches, 0 confidently wrong in these source-generated cases, and 18/40 withheld**. The unchanged default remains **17/40 correct, 0 confidently wrong, 23/40 withheld**. No previously source-correct default case was lost. This diagnostic does **not** convert the withheld 18 into passes.

Across **all 18 still-withheld cases**, the first position produced a trusted map-matching anchor (`MATCHED`), and the second position had **exactly two time-reachable candidates**; the original conservative ambiguity outcome was reproduced. All 36 competing directed edges belonged to **OSM way `32113418` (Moss Lane)**, and each candidate pair shares its direction flag. They are two mapped *segments*, not necessarily two independently different physical roads. Every last-fix reason remained `nearby_parallel_or_overlapping_roads`. **None of these 18 failures was caused simply by a missing initial anchor or zero reachable candidates.**

| Frozen UK case | Candidate A | Candidate B | First GPS anchor | Time-reachable candidates |
|---|---|---|---|---:|
| `TGP-001` | `w:32113418:10:r` | `w:32113418:11:r` | MATCHED | 2 |
| `TGP-002` | `w:32113418:10:f` | `w:32113418:9:f` | MATCHED | 2 |
| `TGP-004` | `w:32113418:16:r` | `w:32113418:17:r` | MATCHED | 2 |
| `TGP-005` | `w:32113418:16:f` | `w:32113418:15:f` | MATCHED | 2 |
| `TGP-007` | `w:32113418:19:f` | `w:32113418:18:f` | MATCHED | 2 |
| `TGP-009` | `w:32113418:20:r` | `w:32113418:21:r` | MATCHED | 2 |
| `TGP-010` | `w:32113418:21:f` | `w:32113418:20:f` | MATCHED | 2 |
| `TGP-011` | `w:32113418:19:r` | `w:32113418:20:r` | MATCHED | 2 |
| `TGP-012` | `w:32113418:20:f` | `w:32113418:19:f` | MATCHED | 2 |
| `TGP-013` | `w:32113418:21:r` | `w:32113418:22:r` | MATCHED | 2 |
| `TGP-014` | `w:32113418:20:r` | `w:32113418:21:r` | MATCHED | 2 |
| `TGP-015` | `w:32113418:21:f` | `w:32113418:20:f` | MATCHED | 2 |
| `TGP-016` | `w:32113418:26:r` | `w:32113418:27:r` | MATCHED | 2 |
| `TGP-018` | `w:32113418:25:r` | `w:32113418:26:r` | MATCHED | 2 |
| `TGP-019` | `w:32113418:26:f` | `w:32113418:25:f` | MATCHED | 2 |
| `TGP-021` | `w:32113418:26:r` | `w:32113418:27:r` | MATCHED | 2 |
| `TGP-025` | `w:32113418:35:r` | `w:32113418:36:r` | MATCHED | 2 |
| `TGP-040` | `w:32113418:41:f` | `w:32113418:40:f` | MATCHED | 2 |

**Source and measurement limits:** identical pinned historical public Greater Manchester OSM source and frozen UK40 synthetic GPS generation. Independent vehicle GNSS reference, actual signage/turn law, current road reconstruction status, lane geometry and realistic sensor-jitter truth were **not** verified. The diagnostic artifact includes each pair's edge IDs, lateral distance residuals, heading error, candidate scores, map connector lengths and time-reachability. Neither repeating an OSM way ID nor finding a graph path proves real-world continuity, permitted U-turns, or GPS safety.

## Meaningful failure and issue register

| Issue | Evidence | Decision gate |
|---|---|---|
| Ambiguity unresolved | 18/18 withheld with two time-reachable map fragments of the same OSM way | Must not mark any as correct or relax baseline distance/confidence thresholds |
| Inadequate independent road diversity | All 18 arose on OSM way `32113418` | Expand to independent real UK road geography after freezing independently supportable reference outcomes |
| Geometry/source truth | Generated point's producing edge is not surveyed ground truth; graph connectivity is not legal movement proof | Validate directed progress/turn restrictions against suitable dated sources |
| No new comparable external streaming engines | Diagnostic only uses default DMN and shadow DMN | Keep external GPS ranking as NOT_RUN rather than borrowing routing scores |

## Proposed next improvement — review before any matcher change

1. **Safe progress hypothesis:** distinguish genuine forward progress through short same-way segments from a backward return to an earlier segment, using actual directed anchor history and travel-time bounds. Report alternative hypotheses rather than force a match. Retain separate one-way carriageways and branches.
2. **Targeted real UK tests:** freeze independent roads with forward/reverse adjacent fragments, closely parallel service roads, slip roads, bifurcating junctions and sharp bends, then obtain dated independent ground-truth records where feasible. Do not invent verified labels.
3. **Additional adversarial controls:** stopped/weak/contradictory GPS, reverse trajectory, underpass and tunnel reacquisition, prohibited U-turns and movement along different same-direction carriageways. Keep confident wrong-road counts distinct from valid withheld outcomes.
4. **Approval and full retest:** obtain owner approval for the narrow change; keep conservative and experimental GPS matchers present, apply no silent production behavior change, then freshly rerun complete affected DMN/competitor common cases under the permanent six-rule policy. The available comparable competitor cohort needs a genuine supported GPS-matching contract.

**STOP for owner review.** No match logic, acceptance/oracle, app, APK or production repository was changed. No future behavior change is approved merely because the diagnostic and unit tests passed.
