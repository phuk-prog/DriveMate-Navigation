# ROUTE-001: six executed systems on frozen one-way routing

[Expanded successful run 38818121643](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38818121643)
at `4b5cc0a72c82c71bf26cf8ac5a643f2ebd7b6185` actually executed OSRM 5.27.1,
Valhalla 3.9.1, GraphHopper 11.1 and openrouteservice 10.1.0 **sequentially**, plus
DMN. BRouter's original
[successful run 38815930888](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38815930888)
at `f8e7cc3d4e5bb07b82ca9a7cbbba88ee7eac420d` is retained with its own SHA;
it was not rerun in the expansion. Map, oracle and tolerances are identical.

This is a frozen four-case synthetic analytical routing contract, separate from
GPS-001. No real-road, physical GPS, turn-sign or independent legal truth was
measured. Source-map agreement does not establish independent road legality.

| Rank | Engine/configuration | Pass | Fail | Score /10 |
| --- | --- | ---: | ---: | ---: |
| 1= | BRouter 1.7.10 / default car-vario | 4 | 0 | 10 |
| 1= | DMN / shortest_route | 4 | 0 | 10 |
| 1= | GraphHopper 11.1 / car CH | 4 | 0 | 10 |
| 1= | OSRM 5.27.1 / car.lua MLD | 4 | 0 | 10 |
| 1= | Valhalla 3.9.1 / auto | 4 | 0 | 10 |
| 1= | openrouteservice 10.1.0 / driving-car fastest | 4 | 0 | 10 |

Score = `10 * passed / 4`, equal scores share rank. These six systems are the
only executed systems for this cohort. OsmAnd and Organic Maps remain unranked
because app/native routing harnesses are not integrated; HERE, Mapbox, TomTom and
Google Maps lack configured permitted same-fixture access; Waze has no established
permitted automated routing interface. All twelve external families plus DMN are
retained in the scorecard with per-case NOT_RUN reasons; none receives zero quality.

| Case | Expected | DMN | BRouter | OSRM | Valhalla | GraphHopper | ORS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ROUTE-001-east-direct | East along bottom, 444.712 m | PASS | PASS | PASS | PASS | PASS | PASS |
| ROUTE-001-west-direct | West along top, 444.712 m | PASS | PASS | PASS | PASS | PASS | PASS |
| ROUTE-001-bottom-reverse-detour | Follow cycle, 956.142 m | PASS | PASS | PASS | PASS | PASS | PASS |
| ROUTE-001-top-reverse-detour | Follow cycle, 956.142 m | PASS | PASS | PASS | PASS | PASS | PASS |

Every PASS satisfies all frozen requirements: endpoints within 2 m, returned
vertices and three interior samples per segment within 2 m of the declared path,
forward path progress with 0.5 m numerical tolerance, total geometry length within
5 m. Expected paths were declared analytically before running BRouter, not taken
from DMN or competitor output. The rectangular cycle gives each request a unique
simple directed path. Tests also reject wrong-way shortcuts and reversed endpoints.
No shortest-time, profile-cost, ETA or general navigation quality ranking is inferred.

Map SHA-256: `4ed7819767ccd553a86e5a74f4184a905e5913c8088ad2020893a21e2a19ebc2`.
Oracle SHA-256: `bcee6b5700f6d29fc218b27b8aab2569cfbc9c9b4604a2df740c8715b72592e7`.
[Expanded per-case scorecard and source SHAs](../references/route001-expanded-scorecard-20261015.json),
[new actual engine reports](../references/route001-expanded-20261015.json),
[original BRouter reports and prepared-map/profile hashes](../references/route001-brouter-20261015.json).

OSRM and Valhalla containers retain their pinned digests from the workflow.
GraphHopper's official Maven JAR is checked against its published SHA1; it uses
Java 25, car.json CH, tiny-network threshold 0 and calculated unencoded geometry.
ORS uses the integrity-checked official 10.1.0 JAR (SHA-256
`46b83b353eaf8830a1b53cad91d027e00547cd9a00e86efddd64a45335bfb8e1`), Java 25,
no elevation, no CH/LM/core and tiny-network pruning disabled. All consume the
same invented road map. Valhalla polyline6 decoding is verified against a known
polyline vector and malformed-input controls; coordinate-order tests cover all
GeoJSON interfaces. No hosted calls, credentials or personal location data.

No DMN routing failure or competitor advantage was reproduced on these four
cases, so no routing policy was changed. A scorecard bug was reproduced and
fixed: an incomplete judged outcome now rejects the cohort instead of assigning
an apparent full-cohort score. All 372 unit tests, compile, privacy checks and
ordinary CI passed. The reusable skill's unified_preflight script remains absent
and unavailable, not passed. The UK coverage tradeoff remains unresolved and
promotion remains blocked.

## Work still needed

- Diagnose the seven lost UK matches with additional justified evidence; do not
  force their generating-edge labels into confident output.
- Freeze and run GPS ambiguity, bad-fix, gap and recovery cases.
- Freeze the next routing fixture before tuning: access restrictions, prohibited
  turns, disconnected roads, incoming-turn context and blocked-link rerouting.
  Then execute applicable references on each supported cohort sequentially.
- Implement executable OsmAnd/Organic Maps harnesses or evaluate other runnable
  open-source families, keeping components and full apps clearly distinguished.
- Verify rerouting, junctions/roundabouts, instructions, arrival, offline failures
  and resource use in separately bounded stages. Device readiness needs actual
  Android evidence; synthetic Python tests cannot establish it.
