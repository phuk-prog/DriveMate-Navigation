# GitHub-hosted category benchmark

The user authorised moving this comparison into DriveMate-Navigation GitHub on
2026-10-14. This supersedes the earlier local-only boundary for this research
repository. The separate Android DriveMate repository remains untouched.

One branch-push workflow runs the candidate and GraphHopper, then isolated OSRM
and Valhalla jobs using the previously configured pinned image digests. All use
the same independently authored synthetic map. No national maps, personal drives,
paid services, SDK secrets or APKs are used. Results are uploaded as artifacts;
reference containers, caches and binaries are not source dependencies.

The initial cloud run covers three external routing engines. It does not claim
to execute all ten full applications. OsmAnd, Organic Maps, BRouter,
openrouteservice and commercial SDK adapters remain additional provisioning work.
Commercial authorisation and device replay requirements do not disappear merely
because the runner is GitHub-hosted.

Scores are divided into routing/legality, speed/rerouting, GPS matching,
GPS recovery, junctions/roundabouts, lanes, instruction timing and offline/resource
efficiency. Correctness score is ten times passed/applicable executed cases.
Warm service speed is a relative p95 score among measured configurations only.
Incomplete category coverage means no overall score or global ranking, not zero.
Runtime failures, unmappable geometry and unsupported adapters are kept distinct
from valid routing failures. Different cost models, response shapes, batch vs
live GPS, and small-map limitations are disclosed.

The existing main workflow and its original public-road smoke markers remain
unchanged. This benchmark is confined to its research branch and has no schedule.

## Direct comparison instead of testing complete apps

The user confirmed on 2026-10-14 that the goal is comparing **other navigators'
actual navigation results against DriveMate**, not installing their complete apps.
Therefore the Organic Maps Android emulator/startup smoke has been removed from
this comparison workflow. The previously failed emulator dependency job is NOT
a navigation accuracy defect and must not affect a navigator's score.

The category aggregator now creates `HEAD_TO_HEAD.md` and
`head_to_head.json` from **actual executed** DriveMate, GraphHopper, OSRM and
Valhalla artifacts, paired by matching scenario ID, dataset SHA-256 and authored
expected route. It reports which passed the *same synthetic scenario* rather
than implying whole-app performance or choosing a general winner.

The agreed ten consumer navigator targets are Google Maps, Waze, Apple Maps,
HERE WeGo, TomTom, Sygic, OsmAnd, Organic Maps, Magic Earth, and MapFactor
Navigator. These are **not** equivalent to the three engine baselines. Results
for these complete navigators require an authorised direct routing interface
or an actual recorded/tested navigation trace; backend similarity, marketing
claims and synthetic substitutes are not acceptable. Unknown access remains
**not tested** rather than zero or a fabricated score. No app copies/APKs,
UI comparisons or Android installations are required for this head-to-head
research phase.
