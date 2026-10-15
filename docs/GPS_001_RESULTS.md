# GPS-001 — first numbered comparison, fixes and retest

**Scope: synthetic controlled GPS output contract only.** Expected positions
and east/west motion are fixed by an independently declared analytical fixture,
not by DMN or competitor output. This is not independently surveyed UK accuracy,
lane identity or legal-road evidence. See [the frozen protocol](DMN_NUMBERED_TRIALS.md).

## Executed evidence

- [Baseline run 38806731805](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38806731805), research commit `94cf97c1fe66df30ec1f6078707ed82dcd64c1e8`.
- [Retest run 38807314302](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38807314302), research commit `3581693e66c8854bc3a9cba6d6b2692a2454c0bd`.
- Both completed successfully and actually executed OSRM 5.27.1, Valhalla 3.9.1 and GraphHopper 11.1 sequentially; injected doubles are never ranked.
- [Before](../references/gps001-before-20261015.json), [after](../references/gps001-after-20261015.json), [all-twelve coverage and scorecard](../references/gps001-scorecard-20261015.json).

Every case requires all four observation slots, each position within 5 m of its
predeclared truth, and strictly forward observed progress. A missing required
match fails completeness; it is not a confident wrong-road verdict. All checks
must pass. Score = ten times passed cases divided by six; ties share rank.

## Highest-to-lowest retest scoreboard

| Rank | System/configuration | Score /10 | Pass | Fail | Unsupported | Not run |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1= | **DMN improved temporal** | **10** | **6** | **0** | 0 | 0 |
| 1= | OSRM 5.27.1, tidy=false | 10 | 6 | 0 | 0 | 0 |
| 1= | Valhalla 3.9.1, auto/map_snap | 10 | 6 | 0 | 0 | 0 |
| 4 | GraphHopper 11.1, car/gps_accuracy=10 m | 3.333 | 2 | 4 | 0 | 0 |
| — | openrouteservice 10.1.0, pointwise snapping | — | 4 | 0 | 2 | 0 |
| — | OsmAnd | — | 0 | 0 | 0 | 6 |
| — | Organic Maps | — | 0 | 0 | 0 | 6 |
| — | BRouter | — | 0 | 0 | 0 | 6 |
| — | HERE | — | 0 | 0 | 0 | 6 |
| — | Mapbox | — | 0 | 0 | 0 | 6 |
| — | TomTom | — | 0 | 0 | 0 | 6 |
| — | Google Maps | — | 0 | 0 | 0 | 6 |
| — | Waze | — | 0 | 0 | 0 | 6 |

[Expanded scorecard with every case and exact run provenance](../references/gps001-expanded-scorecard-20261015.json).
OSRM/Valhalla/GraphHopper results are retained from the executed retest; DMN and
ORS were executed in run 38814980108 on the identical map and oracle hashes.
No claim that all engines were rerun at the newest source SHA is made.

Eight families remain not run for GPS-001. OsmAnd and Organic Maps need app/native
replay harnesses. BRouter has a self-hostable routing engine, requiring a routing
contract and map builder adapter. These are implementation gaps, not proof of poor
products. HERE/Mapbox/TomTom/Google have no configured permitted credentials and
same-fixture interface. Paid access is not authorised. Waze has no permitted
automated replay interface. All remain unranked with per-case NOT_RUN reasons.

### Additional executed reference: openrouteservice

[Run 38814980108](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38814980108)
on `e80e54a9b4ea3195dede7bcba727c3c65ad8f156` used the official integrity-checked
10.1.0 JAR on Java 25, driving-car, radius 20 m, pointwise snapping, tiny graph
pruning disabled, no elevation or CH/LM/core preparation. This tests output
positions and observed progression, not temporal inference or direction legality.

| Frozen case | ORS outcome | Exact evidence |
| --- | --- | --- |
| GPS-001-east-clean | PASS | 4/4 returned, all within 5 m, east progress |
| GPS-001-west-clean | PASS | 4/4 returned, all within 5 m, west progress |
| GPS-001-east-noise | UNSUPPORTED | HTTP 404 / ORS 8010: observation outside imported graph bounds |
| GPS-001-west-noise | UNSUPPORTED | HTTP 404 / ORS 8010: observation outside imported graph bounds |
| GPS-001-east-multilink | PASS | 4/4 returned, all within 5 m, east progress |
| GPS-001-west-multilink | PASS | 4/4 returned, all within 5 m, west progress |

The alternating noise extends outside this invented graph's bounding box. ORS
rejects those requests rather than returning matched observations. They remain
visible as unsupported, not failed position claims, and **no full-six score is
assigned**. Four passes out of four supported cases are not a six-case 10/10.
The map and inputs were not enlarged or altered to hide this limitation. The
other three executed references and DMN delivered alignable output for these
noise cases, except GraphHopper's previously recorded output omissions.

Two initial executions stopped on HTTP 404 before producing a complete report;
these failures and the later response-code diagnosis are retained in
[the ORS evidence](../references/gps001-ors-20261015.json). The adapter now
continues only for the explicit 8010 input-domain rejection. Other HTTP or setup
errors still abort as unavailable, never scored as case failures or passes.
A reproduced scorecard bug that ranked incomplete cohorts was fixed and tested:
unsupported cases now prevent a full-cohort score while preserving actual passes.
All 360 local unit tests, compile, privacy checks and execution CI passed.
The skill's `scripts/unified_preflight.py` is absent in this research repository;
it was unavailable, not passed. No DMN matching policy changed in this stage.

## Exactly what passed or failed

| Case | DMN before | DMN after | OSRM after | Valhalla after | GraphHopper after |
| --- | --- | --- | --- | --- | --- |
| East clean, one short segment | FAIL: 1/4 matched | PASS | PASS | PASS | FAIL: no four-point alignment |
| West clean, one short segment | FAIL: 1/4 matched | PASS | PASS | PASS | FAIL: no four-point alignment |
| East with alternating lateral noise | FAIL: 1/4 matched | PASS | PASS | PASS | FAIL: no four-point alignment |
| West with alternating lateral noise | FAIL: 1/4 matched | PASS | PASS | PASS | FAIL: no four-point alignment |
| East across several short links | FAIL: 2/4 matched | PASS | PASS | PASS | PASS |
| West across several short links | FAIL: 2/4 matched | PASS | PASS | PASS | PASS |

Every PASS above means **4/4 complete, 4/4 positions within 5 m, and correct
observed direction**, not merely one near final point. Returned positions in
these runs had errors below 0.00005 m (printed as 0.0000 m); this ideal synthetic
result is not real GNSS accuracy. No returned aligned position exceeded 5 m.
GraphHopper's four failures mean no safely aligned complete four-point sequence;
GPS-001 does not distinguish provider no-match from partial-output alignment in
those rows. Its internal cause remains unresolved, not a wrong-road assertion.

## Error review and implemented improvement

**DMN:** adjacent collinear pieces of one OSM way were incorrectly treated as
different plausible roads. Recognise only contiguous, same-way, same-heading
segments as one straight continuation; arbitrary labels, disconnected parallel
roads, opposing directions and diverging/different-way branches retain ambiguity.
The temporal matcher also allowed only one-edge movement. A bounded turn-aware
connector now permits up to eight intermediate links, at most 128 expanded
states, with allowed access, prohibited-turn checks and the original travel-time
bound. Exceeding the local search bound still withholds confidence.

The original DMN run returned only 8/24 observation matches and failed 6/6
complete cases. After the fix it returns 24/24 and passes 6/6. This closes the
verified deficit to Valhalla on these cases; it does **not** exceed the top ties
or establish universal superiority. The reverse validation case was already
observed in the baseline, so it is not claimed as a blind holdout.

**OSRM adapter:** baseline tidy=true returned 2/4 observations in each short case
and 3/4 in each multi-link case; every case failed the required-output contract.
Changing only this trial's optional preprocessing to tidy=false restored 4/4 in
all six cases. This demonstrates an adapter-configuration cause for this trial,
not a general OSRM navigation defect. Historical UK benchmark options remain
unchanged. Both configurations' actual reports are retained.

**Regression checks:** the final 352 local tests pass, including false parallel-road
confidence, prohibited intermediate turns, connector search limits, wrong-way
progress and impossible road-transition travel. All three retest jobs and the
ordinary research CI passed. This does not mean all map-regression acceptance
checks passed: the distinct real-map outcome below remains unresolved.

## Additional UK regression — an open coverage cost, not concealed

The first UK replay after these changes reduced generating-edge positives from
24/40 to 17/40, with zero confident wrong assignments and 23 withheld. The
12-case cohort initially fell from 8 correct to 6. This was detected despite
successful CI because the pre-existing workflow did not gate historical coverage.
[Original regression](../references/gps001-uk-regression-20261015.json).

Sharing the candidate policy fixed an independently reproduced duplicate-road
case but did not restore those aggregate counts. The subsequent
[per-case diagnostic run](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38808750926)
identified exactly seven additional ambiguous cases, TGP-006, -008, -013, -015,
-016, -019 and -039. Each has one direct candidate but two time-reachable
candidates on the same OSM way. No other-way candidate was added in those seven.
[Full diagnostic evidence](../references/gps001-uk-diagnostics-20261015.json).

A further bounded guard retains an already best-supported direct fragment only
when alternatives are its immediate forward continuation on the same way;
different ways, reversed fragments and prohibited moves remain ambiguous. The
[latest executed run 38809228324](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38809228324)
restored the 12-case result to **8 correct / 0 wrong / 4 withheld**, but the
40-case result remains **17 correct / 0 wrong / 23 withheld**.
[Actual final UK reports](../references/gps001-uk-final-20261015.json).

The seven remaining cases require more topology/trajectory evidence. The old
24 positives are not independently surveyed truth, and the new abstentions are
not proof of better safety. Do not force confident matches just to recover a
historical number. **GPS-001 synthetic improvement is demonstrated; general
UK-map coverage improvement is not. This open tradeoff blocks promotion.**

## Bounded topology investigation (2026-10-15)

[Run 38810752808](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38810752808)
on `f17131dd2ea35b80b94657177074fbbd706aaa6a` executed the unchanged 40-case
cohort with additional read-only diagnostics. Source SHA-256 is unchanged.
All seven lost cases have a **backward-adjacent**, same-way, same-direction
alternative; the preferred direct candidate is the best spatial candidate in
each. Its residual is 0 m on these generated observations; alternatives are
5.9229–7.4274 m away, with heading differences 0.0095–7.5108 degrees.
The bounded graph search finds a connector from the direct segment back to the
alternative (41.8220–77.7906 m of intermediate links). This is graph reachability,
not proof that such a return movement occurred or is physically/legal-world valid.

The forward-fragment guard therefore does not apply. Selecting the generating
edge by its synthetic label or discarding the alternative solely to regain seven
matches would not establish a safe fix. No confidence policy was changed.
The result remains **17 correct / 0 confident wrong / 23 withheld**; all 40
impossible-speed and all 40 weak-fix checks withhold safely. **355 local and CI
unit tests pass**, including three new diagnostic topology tests. This run did
not rerun external engines or the separate 12-case cohort; their earlier evidence
remains intact. There is no new comparable ranking from this diagnostic stage.
[Full per-case evidence](../references/gps001-uk-topology-20261015.json).
The coverage tradeoff remains unresolved and promotion remains blocked.

## Next tests

Diagnose short-observation alignment in the GraphHopper adapter; add harder
independent analytical counterexamples and separately corroborated UK-road truth.
Run pinned UK geometry regressions before promoting the matching change.
Then extend one category at a time into ambiguity, corrupt GPS, tunnels,
multi-junction movement, legal routing and arrival. Keep per-case facts and
provider setup gaps visible. No Android production changes, merge or release.
