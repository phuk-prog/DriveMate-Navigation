# DMN GPS safety fixes: executed public UK map replay

15 October 2026. [Research PR 3](https://github.com/phuk-prog/DriveMate-Navigation/pull/3)
contains the [junction travel-time](DMN_TEMPORAL_TRANSITION_SAFETY.md) and
[directed progress](DMN_DIRECTED_PROGRESS_SAFETY.md) safeguards. The earlier
documents preserve the original local-only evidence; this report records the
subsequent real-engine executions, not field navigation or a release.

## Exact execution evidence

| Run | Tested research commit | Result |
| --- | --- | --- |
| [UK temporal + OSRM](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38804343539) | `0b48f5c516a74bf622198705147c5ecbe24fd550` | SUCCESS; 337 tests; both requested replays executed |
| [Valhalla](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38804677374) | `0eb7e5de1d705a126756f84eadf4bf3ca2040c23` | SUCCESS; 337 tests; live reference executed |
| [GraphHopper](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38804941177) | `4bfbda9f470434383bd321aa5adb74938b3070b2` | SUCCESS; 337 tests; live reference executed |

Runs were sequential. Matcher code, fixtures and adapters were unchanged between
them; intervening commits retained aggregate evidence only. The source is pinned
Geofabrik `geofabrik-260901`, contributor-anonymized public Greater Manchester
OSM geometry. Every report has the same source XML SHA-256:

`b3a883ae9b7c85072d24afeee7a1079aea00c22264516a0e1e71d49221ad27d5`

Complete aggregate JSON outputs, extracted from completed job logs, are retained
in [the evidence register](../references/dmn-gps-safety-replay-20261015.json).
The corresponding run artifacts retain the original aggregate reports for their
configured retention periods. No map files or generated GPS observations were
committed. No new workflow, dependencies, paid APIs or production app changes
were needed. This uses the existing research CI because local shell networking
was unavailable.

## Forty two-reading trajectories on real map geometry

| Candidate | Planned | Correct generating directed edge | Confident wrong | Withheld |
| --- | ---: | ---: | ---: | ---: |
| DMN single-fix | 40 | 17 | 0 | 23 |
| DMN temporal with both safeguards | 40 | 24 | 0 | 16 |

All 40 injected implausible-speed controls were rejected; all 40 weak-accuracy
controls were withheld. There were 31 usable initial anchors. Withholding remains
unresolved positive road identification, not a successful match.

## Common final-position geometry proxy: twelve four-reading scenarios

Each system receives the same twelve generated trajectories. The shared metric
is whether its safely aligned final snapped position is within 5 m of the
generating OSM segment. The source map is the oracle for this proxy only.

| Candidate/reference | Planned | Near generating geometry | Farther than 5 m | Withheld or unalignable |
| --- | ---: | ---: | ---: | ---: |
| DMN single-fix | 12 | 6 | 0 | 6 |
| DMN temporal with both safeguards | 12 | 8 | 0 | 4 |
| OSRM Match 5.27.1 | 12 | 12 | 0 | 0 |
| Valhalla trace_attributes 3.9.1 | 12 | 9 | 1 | 2 |
| GraphHopper Match 11.1 / Java 25 | 12 | 3 | 0 | 9 |

DMN temporal's separate exact generating-edge check was 8 correct / 0 confident
wrong / 4 withheld in each reference run. External outputs do not supply an
equivalent DMN directed-edge identity, so their edge correctness is **unresolved**.
All near outputs had both a reverse segment and another segment with the same
OSM way ID nearby; no distinct OSM-way alternative was counted in this cohort.
None of this verifies road direction, lanes or independent legal truth.

Do not confuse final-point coverage with complete trace coverage: OSRM safely
aligned 40/48 input observations, leaving 8 unmatched; Valhalla aligned 44/48,
with 43 within 20 m of input and one farther away. GraphHopper aligned 12/48,
with 5 no-match cases and 4 cases whose partial output could not safely be
aligned. These are separate measures with their own denominators.

The experimental multi-hypothesis DMN tracker, separately evaluated in the
OSRM run, returned 6 correct / 0 confident wrong / 6 withheld, losing two
positive decisions relative to the established temporal matcher and rescuing
none. It is not promoted based on this result.

## Interpretation and remaining work

The measured temporal counts match the earlier historical cohorts; this batch
detected no aggregate regression after the two safeguards. It did not execute
the old and new implementations side by side on this map, and does not prove
per-case equivalence or a real-world accuracy improvement. The controlled
synthetic fault reproductions remain the direct before/after safety evidence.

No new out-of-ten rank is justified. Profiles, graph processing and matching
interfaces differ, source-generated fixes are not independently surveyed GPS,
and HTTP timings are not comparable with in-process Python runtimes.
These two scenario cohorts cannot be added into a single accuracy percentage.

The next discriminating work is per-scenario diagnosis of the four withheld
temporal cases, common source-way/direction crosswalks for external outputs,
and harder public-map cases around folds, parallel carriageways and ambiguous
junctions. Preserve abstention unless evidence supports a unique assignment.
Independent legal truth, real GNSS/sensors, multi-edge journeys, arrival, lanes,
voice and Android/device resource validation remain **unresolved or not tested**.
Production DriveMate is unchanged; this draft PR is not merged or released.
