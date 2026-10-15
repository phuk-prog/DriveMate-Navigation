# ROUTE-001: actual BRouter and DMN one-way routing

[Successful run 38815930888](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38815930888)
executed BRouter 1.7.10 and DMN at
`f8e7cc3d4e5bb07b82ca9a7cbbba88ee7eac420d`. This is a frozen four-case
synthetic analytical routing contract, separate from GPS-001. No real-road,
physical GPS, turn-sign or independent legal truth was measured.

| Rank | Engine/configuration | Pass | Fail | Score /10 |
| --- | --- | ---: | ---: | ---: |
| 1= | BRouter 1.7.10 / default car-vario | 4 | 0 | 10 |
| 1= | DMN / shortest_route | 4 | 0 | 10 |

Score = `10 * passed / 4`, ties share rank. These are the only two scheduled
engines in this bounded integration stage; this is not a twelve-engine routing
ranking or evidence of general equality. All twelve external families plus DMN
are retained in the machine-readable scorecard, with per-case NOT_RUN reasons.
The existing GPS-001 ranking is unchanged.

| Case | Expected | DMN | BRouter |
| --- | --- | --- | --- |
| ROUTE-001-east-direct | East along bottom, 444.712 m | PASS | PASS |
| ROUTE-001-west-direct | West along top, 444.712 m | PASS | PASS |
| ROUTE-001-bottom-reverse-detour | Follow cycle; avoid westbound shortcut, 956.142 m | PASS | PASS |
| ROUTE-001-top-reverse-detour | Follow cycle; avoid eastbound shortcut, 956.142 m | PASS | PASS |

Every PASS satisfies all frozen requirements: endpoints within 2 m, returned
vertices and three interior samples per segment within 2 m of the declared path,
forward path progress with 0.5 m numerical tolerance, total geometry length within
5 m. Expected paths were declared analytically before running BRouter, not taken
from DMN or competitor output. The rectangular cycle gives each request a unique
simple directed path. The oracle also rejects a deliberately wrong-way shortcut
and reversed direct route in verification tests.

The original release ZIP is integrity-checked; the full JAR, profiles, lookup and
prepared segment hashes are retained in
[complete execution evidence and scorecard](../references/route001-brouter-20261015.json).
Map SHA-256: `4ed7819767ccd553a86e5a74f4184a905e5913c8088ad2020893a21e2a19ebc2`.
Oracle SHA-256: `bcee6b5700f6d29fc218b27b8aab2569cfbc9c9b4604a2df740c8715b72592e7`.
BRouter used Java 17, 512 MB heap and a 30-second per-request limit; its own
OsmFastCutter, PosUnifier and WayLinker built segments from the same invented map,
without elevation downloads. No hosted provider calls or credentials.

There was no DMN fault reproduced and no competitor advantage on these four
cases, so no routing policy was tuned. All 364 unit tests, compile, privacy
checks and CI passed. The unified_preflight script prescribed by the reusable
skill is absent in this research repository and remains unavailable, not passed.
The UK matching coverage tradeoff is unresolved; promotion stays blocked.

## Work still needed

- Diagnose the seven lost UK matches with additional justified evidence; do not
  force their generating-edge labels into confident output.
- Freeze and run GPS ambiguity, bad-fix, gap and recovery cases.
- Add OSRM, Valhalla, GraphHopper and ORS to ROUTE-001 sequentially; then extend
  routing coverage to access restrictions, prohibited turns and disconnected roads.
- Implement executable OsmAnd/Organic Maps harnesses or evaluate other runnable
  open-source families, keeping components and full apps clearly distinguished.
- Verify rerouting, junctions/roundabouts, instructions, arrival, offline failures
  and resource use in separately bounded stages. Device readiness needs actual
  Android evidence; synthetic Python tests cannot establish it.
