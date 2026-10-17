# INTEGRATED-001: engine-only journey baseline

DMN passes **3/3** frozen synthetic integration cases at source
`d12af5cb0ef597985c56793e3e930ace78bffc2e`. This combines real research
components in one process; it is not an Android/app run, real UK journey,
physical GNSS test or independent road-law result.

| Case | Integrated behavior | Result | One local execution ms |
|---|---|---:|---:|
| clean-arrival | route → line adherence → GPS match → approach cue → corroborated arrival | PASS | 0.300141 |
| corroborated-reroute | two off-route observations → replacement route → atomic installation | PASS | 0.058578 |
| turn-restriction-detour | prohibited turn changes the complete route edge chain | PASS | 0.022974 |

The times are single local whole-case diagnostics with different work in each
case. They are not p50/p95 measurements and provide no speed ranking.

The analytical oracle was committed first at `aa99395`. Oracle SHA-256 is
`95c6732bee26b6fe1bebda40f8ffa085ce7d4a39839e61f088d7576fb405208b`;
canonical graph-definition SHA-256 is
`935b7a8d0daa7153c28f45625dc2c514867d7976b154a261d32694739834f4b5`.
[Exact DMN events and checks](../references/integrated001-dmn-20261017.json) and
[all-family interface audit](../references/integrated001-scorecard-20261017.json)
are retained.

DMN's isolated conformance score is 10/10 (`10 × 3/3`). It is the only judged
system, so there is **no competitive winner**. OSRM, Valhalla, GraphHopper,
openrouteservice and BRouter are UNSUPPORTED through the currently integrated
static endpoints because they cannot expose equivalent matcher, reroute-session
and arrival-controller state. OsmAnd, Organic Maps, HERE, Mapbox, TomTom,
Google Maps and Waze are NOT_RUN without a permitted equivalent full-lifecycle
harness. They receive no score.

No DMN fault was reproduced in this small cohort and no navigation behavior was
changed. The baseline still omits a roundabout in the same journey, bad/stale GPS
during active guidance, closure-driven replanning, offline package replacement
during a session, sustained execution, real-map legality, phone lifecycle and
physical GNSS. UK matching remains 17 correct, 0 confidently wrong and 23
withheld with seven unresolved regressions; promotion remains blocked.
