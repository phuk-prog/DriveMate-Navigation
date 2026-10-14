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
