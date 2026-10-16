# ROUTE-003 shared real-map baseline

ROUTE-003 executed **6 systems: DMN plus 5 external engines** on three identical
synthetic endpoint pairs from the pinned Greater Manchester public OSM extract.
All six supplied a complete route, endpoints within 5 metres, positive finite
distance and positive finite ETA for all three cases. They therefore tie at
10/10 for this narrow output contract.

| Rank | System | Passed | Failed | Unresolved | Score /10 | Median calculation ms |
|---:|---|---:|---:|---:|---:|---:|
| 1= | DMN | 3 | 0 | 0 | 10.000 | 0.027190 |
| 1= | OSRM | 3 | 0 | 0 | 10.000 | 1.075801 |
| 1= | Valhalla | 3 | 0 | 0 | 10.000 | 5.181559 |
| 1= | BRouter | 3 | 0 | 0 | 10.000 | 7.272329 |
| 1= | GraphHopper | 3 | 0 | 0 | 10.000 | 8.694816 |
| 1= | openrouteservice | 3 | 0 | 0 | 10.000 | 8.812027 |

The result rank uses `10 * passed / 3`; timing is not part of the score. DMN's
measurement is an in-process Python route search. External measurements are warm
loopback HTTP requests including serialization. The millisecond figures show the
observed boundaries exactly but do **not** form a fair cross-engine speed rank.
Cold startup, map preparation, Android execution, memory and battery were outside
this test.

## Per-case observations

| System | Case 001 ms / m / ETA s | Case 002 ms / m / ETA s | Case 003 ms / m / ETA s |
|---|---:|---:|---:|
| DMN | 0.063228 / 150.635 / 15.494 | 0.025778 / 52.642 / 5.415 | 0.027190 / 52.642 / 5.415 |
| OSRM | 2.314548 / 151.000 / 21.800 | 1.075801 / 52.700 / 7.600 | 1.052403 / 52.700 / 7.600 |
| Valhalla | 45.418472 / 150.000 / 13.572 | 5.181559 / 52.000 / 4.741 | 4.815397 / 52.000 / 4.741 |
| BRouter | 164.492697 / 151.000 / 26.000 | 7.272329 / 53.000 / 17.000 | 6.720823 / 53.000 / 15.000 |
| GraphHopper | 87.845523 / 150.629 / 18.076 | 8.694816 / 52.630 / 6.316 | 7.721144 / 52.630 / 6.316 |
| openrouteservice | 212.549679 / 150.600 / 18.100 | 8.812027 / 52.600 / 6.300 | 7.851867 / 52.600 / 6.300 |

Every row passed the same five checks: complete geometry, start within 5 metres,
end within 5 metres, positive finite distance, and positive finite ETA. No route
failure or endpoint-contract fault was found. The ETA spread is material: on case
001 it ranges from 13.572 to 26 seconds. That is profile-model disagreement, not
evidence that the shortest ETA is correct; no observed journey time exists here.

## Failures and exclusions

The first BRouter attempt in run
[38870925774](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38870925774)
stopped before routing because `all.brf` was absent. Run 38871396349 then exposed
string-valued numeric fields. The adapter was corrected without changing the map,
cases or acceptance rules; the BRouter-only run
[38871562075](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38871562075)
passed 3/3. Both setup failures remain evidence.

Itinero, Routino, OsmAnd, Organic Maps, HERE, Mapbox, TomTom, Google Maps and Waze
are unranked with exact reasons in the JSON record. Missing engines receive no
zero score and no invented result. The minimum-ten external common cohort remains
unmet.

## What this baseline does not establish

These three short paths come from one small map area and do not cover sharp turns,
roundabouts, motorway exits, rural or long routes, closures, simulated traffic,
wrong turns, rerouting, GPS quality, or route legality. OSM agreement is not an
independent statement of current UK road law. The baseline cannot establish the
fastest legal route or general navigation superiority.

No verified DMN defect was found in this limited contract, so no DMN tuning is
justified from these results. The next proposed improvement to the **test**, for
owner review, is a larger independently sourced legality cohort with varied route
types, followed by a separate frozen traffic/closure test where equivalent engine
interfaces exist. DMN remains `NOT_READY_FOR_LIVE_NAVIGATION`.

Full structured evidence, versions, hashes, per-case timings and exclusions are
in [`references/route003-baseline-20261016.json`](../references/route003-baseline-20261016.json).
