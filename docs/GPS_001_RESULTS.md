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

| Rank | System/configuration | Score /10 | Pass | Fail | Not run |
| --- | --- | ---: | ---: | ---: | ---: |
| 1= | **DMN improved temporal** | **10** | **6** | **0** | 0 |
| 1= | OSRM 5.27.1, tidy=false | 10 | 6 | 0 | 0 |
| 1= | Valhalla 3.9.1, auto/map_snap | 10 | 6 | 0 | 0 |
| 4 | GraphHopper 11.1, car/gps_accuracy=10 m | 3.333 | 2 | 4 | 0 |
| — | OsmAnd | — | 0 | 0 | 6 |
| — | Organic Maps | — | 0 | 0 | 6 |
| — | BRouter | — | 0 | 0 | 6 |
| — | openrouteservice | — | 0 | 0 | 6 |
| — | HERE | — | 0 | 0 | 6 |
| — | Mapbox | — | 0 | 0 | 6 |
| — | TomTom | — | 0 | 0 | 6 |
| — | Google Maps | — | 0 | 0 | 6 |
| — | Waze | — | 0 | 0 | 6 |

The four unadapted open-source references lack an integrated, permitted GPS-001
replay interface; BRouter and openrouteservice are routing references without
an integrated observation-matching adapter here. This is not proof that their
products cannot navigate. HERE/Mapbox/TomTom/Google have no configured permitted
credentials and same-fixture interface. Paid access is not authorised. Waze has
no permitted automated replay interface; no scraping or consumer-app automation
was attempted. They are **UNRANKED**, not failed or assigned zero quality.

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

**Regression checks:** 349 local tests pass, including false parallel-road
confidence, prohibited intermediate turns, connector search limits, wrong-way
progress and impossible road-transition travel. All three retest jobs and the
ordinary research CI passed. Real-map regression still needs the separate
pinned UK replay after these new matcher changes; its result must not be
inferred from this synthetic score.

## Next tests

Diagnose short-observation alignment in the GraphHopper adapter; add harder
independent analytical counterexamples and separately corroborated UK-road truth.
Run pinned UK geometry regressions before promoting the matching change.
Then extend one category at a time into ambiguity, corrupt GPS, tunnels,
multi-junction movement, legal routing and arrival. Keep per-case facts and
provider setup gaps visible. No Android production changes, merge or release.
