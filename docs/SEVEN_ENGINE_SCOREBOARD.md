# Seven-engine scoreboard — 17 October 2026 (result of record)

DMN is the engine under test. OSRM 5.27.1, Valhalla 3.9.1, GraphHopper 11.1,
openrouteservice 10.1.0, BRouter 1.7.10 and OsmAnd (nightly router, build hash in
each run) are yardsticks only: each builds its own graph from the same hashed OSM
clip; none is a data source. Every test is ranked on its own (no combined score).
Truth is map-derived (OSM snapshot `2a8ef8e1…`), not independent road law.
Runs at revision `6190d72`: [Category 2](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39051017088),
[B1](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39051017134),
[B2](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39051017075);
scores in [references](../references/seven-engines-20261017.json).

| Test (category) | DMN | OSRM | Valhalla | GraphHopper | openrouteservice | BRouter | OsmAnd |
|---|---|---|---|---|---|---|---|
| No-car roads, 44 closed (2) | **44 (1)** | 41 (3) | 42 (2) | 30 (=4) | 30 (=4) | 20 (7) | 23 (6) |
| One-way roads, 48 (2) | **48 (1)** | 47 (=2) | 47 (=2) | 45 (4) | 43 (=5), 1 wrong way | 37 (7) | 43 (=5) |
| Valid route, 57 (5) | 57 | 57 | 57 | 57 | 57 | 57 | 57 (all =1) |
| Turn instructions, 36 (8) | **36 (=1)** | 36 (=1) | 35 (6) | 31 of 36 (7) | 36 (=1) | 36 (=1) | 36 (=1) |
| Roundabout exits, judged (9) | **21/21 (1)** | 17/20 (7) | 20/20 (=2) | 20/20 (=2) | 17/17 (6) | 20/20 (=2) | 20/20 (=2) |
| Route line on the road (11) | n/a (OSM points) | 0 over 5 m | 0 | 0 | 0 | 0 | 0 |
| Lanes, judged (10) | **35/35 (1)** | 22/36 (3): 2 wrong, 12 none | n/a | n/a | n/a | n/a | 25/34 (2): 9 none |
| Speed limits, judged (15) | **61/61** | n/a in 5.27 | n/a | 68/68 | n/a | n/a | 65/65 |
| Speed, HTTP median ms, 7 common journeys (7) | 12.5 (5) | **1.2 (1)** | 3.5 (2) | 11.3 (4) | 9.3 (3) | 27.1 (6) | in-process 41.1 vs DMN 11.6 |
| Closures: valid detour, 24 (14) | **24 (=1)** | 23 (3) | 24 (=1) | 14 (=4)* | 14 (=4)* | 7 (7)* | 11 (6)* |
| Damaged maps, passed (17) | 16/18 (5): refuses 2 good real maps | 12/12 (=1) | 3/12 (=6)† | 3/12 (=6)† | 12/12 (=1) | 12/12 (=1) | 12/12 (=1) |
| Bad requests, passed/judged (18) | **12/12 (=1)** | 9/15 (7) | 9/14 (6) | 14/14 (=1) | 14/14 (=1) | 12/15 (5) | 12/14 (4) |
| Comparison integrity checks (21) | 54/54 | 53/54 | 54/54 | 48/54 | 48/54 | 45/54 | 48/54 |

Run D ([39055768229](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39055768229),
revision `0d56359`, [report](RUN_D_RESULTS.md)): no engine was seen to drive a closed road or serve a
route from a damaged map. *Partly unresolved: the harness could not fully read some 1–2 km
lines. †Never started on a damaged file within the wait; a quick error is unverified.
Category 21 rates the test set-up, not the engines.

Rule-breaking routes (Category 2 tests): DMN 0, OSRM 0, Valhalla 0, GraphHopper 1,
openrouteservice 2 (one drove the tested one-way road the wrong way), BRouter 2,
OsmAnd 2.

Notes: "judged" counts differ when an engine took a different road (not judged); for
lanes a missing answer counts against the engine (OSRM gave none in 12, OsmAnd in 9). BRouter and OsmAnd take only a start direction, so they more often start the
wrong way (off target, not a rule break). Speed limits all 100% where judged, so
not ranked. Harness fixes made today before these results: shared start/finish path
matching (simplified lines lost their first node), OSRM readiness wait, zero-length
joints in speed-limit reading, OSRM 5.27 has no limit output, OsmAnd departure step.
