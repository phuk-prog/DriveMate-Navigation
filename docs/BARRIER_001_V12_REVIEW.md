# BARRIER-001 v1.2 — access-evidence review

17 October 2026. Engine-only Category 1 test-harness review. **No change to DMN route legality, access policy, or the Android app.**

## Baseline retained unchanged

[BARRIER-001 v1.1](BARRIER_001_RESULTS.md), run
[39022934914](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39022934914),
remains the historical baseline: 94 testable of 110 sampled, 61 judged
(47 closed, 14 open). DMN 46 route-legal passes, zero illegal crossings,
15 no routes. OSM barrier/access tags are map-derived, not independently
verified road rights.

## What scoring v1.2 changes

The old `no_route_but_legal_route_exists` statistic treated a route through
an **unmarked gate** like a clearly usable public-car alternative. This
inflated the apparent missed-route problem by two cases:
`2092919405` (lift gate marked no) and `416565753` (block).
OSRM and/or Valhalla could turn round then pass through **other**
unmarked gates; DMN's conservative mid-route policy did not.

The v1.2 scorer retains the old unqualified count as historical/legacy data
but adds separate fields:

- `no_route_but_known_access_legal_route_exists`: comparators have a
  route that passes the existing OSM legality audit **without using other
  unmarked/restricted/conditional barrier crossings**.
- `no_route_with_only_uncertain_access_alternatives`: every qualifying
  comparator route relies on one or more such crossings, identified by
  engine and barrier ID.
- `passes_via_other_uncertain_barriers`: case evidence for comparators
  previously counted as plain legal passes.

These fields distinguish available **map-derived** routes, not independently
proved legal access on the ground. Existing raw verdicts and historical
results are preserved; the cohort, source and clip hashes are unchanged.
A pure scoring-contract fixture self-check is included. The v1.2
whole-cohort run is
[39026846188](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39026846188);
read its job summary for measured new results, not raw logs.

## Behavioural decisions deliberately left open

**Unmarked/restricted gates at trip endpoints (30 reported cases):**
28 journeys start on an uncertain service road, two finish beyond a private
gate. This sample does not establish public motorcar access. The current
DMN allowance for the road a trip starts or ends on is an access *policy*,
not proof that any unmarked/private gate may be crossed. Do not silently
convert unknown access into public permission, or call all 30 illegal.
Confirm ownership/access conditions and independently corroborate
important cases before adjusting the driving engine.

**Turning round before a closed barrier:** DMN currently blocks the adjacent
road section, which may exclude a lawful approach-and-return on a stub.
A future behaviour change should preserve a reachable stub up to the
barrier while never crossing it; it needs turn legality, physical
turnaround feasibility, independent case evidence, and a full fresh
frozen-cohort multi-engine retest. No such failure was established by
the existing 94-case cohort.

**Decision gate:** Do not modify driving behaviour just to reduce
`SAFE_NO_ROUTE` or increase a competitive score. Further access or turnaround
engine changes require separate evidence and owner approval.

## Validation requirements

- Execute every available comparable reference engine and DMN freshly on
  the frozen 94 testable cases when changing the scoring contract.
- Keep off-target, unknown-access, route-legality and no-route buckets
  distinct, and do not rank incomparable cold/warm timings.
- Keep v1.1 and v1.2 separate. No Android app build or APK.
