# REAL-ONEWAY-001: pinned real-map direction contract

## Frozen scope before execution

This is an OSM map-contract check, not independent current road-law verification.
The only endpoint observations are simulated exact public map nodes; no personal
GPS traces, invented road networks or competitor outputs select the expectations.

Use the same Geofabrik Greater Manchester260901 archive as REF-006, archive SHA256
b7188b22501b878fddba6e06a90bb44ce6c2d721333e0ca57e10a1a82b568807 and XML SHA256
b3a883ae9b7c85072d24afeee7a1079aea00c22264516a0e1e71d49221ad27d5.
The established bbox is -2.270000,53.350000,-2.260000,53.360000, complete ways.
Source: https://download.geofabrik.de/europe/united-kingdom/england/greater-manchester-260901.osm.pbf
Attribution: OpenStreetMap contributors, ODbL.

Before invoking the importer or router, select the first six eligible one-way
ways by numeric OSM ID and the first nondegenerate segment on each. Include
explicit forward/reverse tags or implicit roundabout/circular direction; exclude
unsupported highway classes, conditional tags and explicit nonpublic motorcar
access. If six are unavailable or a fingerprint differs, fail setup; do not
substitute cases after observing output. Write the full raw-tag case manifest
and hash before execution. Six segments each supply an allowed and reverse
request: twelve observations, not twelve independent streets.

Required on each observation: allowed directed edge exists, forbidden counterpart
does not exist, returned route uses no forbidden selected directed edge. The
allowed-direction request must return a nonempty route. Reverse no-route may
pass direction safety only; this does NOT prove no legal alternative exists.
Failures remain in the report. Barriers or missing positive availability must
not be silently removed. Single calculation durations are raw nanoseconds, not
performance rankings. No overall optimality or arbitrary edge-law claim.

DMN executes independently. This bounded stage runs zero external engines and
has no comparative rank or out-of-ten score; it cannot satisfy the shared-ten
requirement. All independent authority-law verdicts remain UNRESOLVED.

## Source-access limitation

A fresh permitted direct read of https://www.data.gov.uk/ on 2026-10-16 returned
HTTP403 from the environment proxy. Earlier National Highways/OS source reads
were blocked too. No road restriction was inferred from these failed reads.
A dated official traffic order with schedule/map, jurisdiction and motorcar
exceptions is required to establish an independent real-world legal expectation.
This does not block the separately labelled supplied-map contract execution.

## Verification and execution status

Four analytical scorer controls reject a reverse import, a wrong-way route and
missing required positive route; reverse refusal cannot establish road law.
The complete local suite passes 450 tests; compile, privacy and whitespace checks
pass. The canonical scripts/unified_preflight.py is absent (UNAVAILABLE).
Actual real-map execution is pending CI; setup/selection failure is not a pass.
UK coverage remains 17 correct / 0 confident wrong / 23 withheld; seven cases
remain unresolved and app promotion stays blocked.

First CI attempt38866454548 at8256dffaba03f0375b52413ea74a6b3ecf9085b2
failed before case selection/routing: the ignored results directory was absent
on a fresh checkout. The archive download/hash check had succeeded. Added explicit
mkdir before any output; map hashes, selection and acceptance remain unchanged.
Retained references/real-oneway-setup-failure-20261016.json; zero cases executed.

Corrected setup run38866570406 atad2a149df06298f55e07a7ab71bb01210b14edfc
verified archive/XML fingerprints but the fixed bbox contained fewer than six
eligible distinct ways. The selector stopped before printing count or routing.
Retained references/real-oneway-inventory-failure-20261016.json. This is missing
case coverage, not demonstrated DMN wrong-way routing. The next bounded diagnostic
prints the unchanged selection and executes available requests, explicitly
INCOMPLETE_CASE_INVENTORY and failing CI when fewer than twelve observations
exist. The six-way requirement is unchanged; no map/case is substituted.
