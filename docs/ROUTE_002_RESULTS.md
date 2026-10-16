# ROUTE-002: access, prohibited turns and route recalculation

**DMN passes 8/8 analytical synthetic controls.** On the five shared static cases,
DMN, OSRM, Valhalla, GraphHopper and openrouteservice pass 5/5 (tied 10/10).
BRouter passes 3/5 (6/10); the targeted retest confirms relocation of both
unreachable requested destinations. This is a narrow route/exact-destination
output contract, not general navigation superiority or independent road legality.

## Executed runs and frozen evidence

- [Baseline 38839461917](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38839461917), source `061fe6187a389ba197c8d72b50506707ca85f0eb`: all five external engines actually ran sequentially, plus DMN.
- [Targeted BRouter retest 38839878414](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38839878414), source `e47ea4586faf2a3f2cc0e3c453b08b63fab5e78d`, job 116777281142: exactly one external engine reran, plus DMN; no duplicate full matrix.
- [Original reports and prepared-map/profile hashes](../references/route002-before-20261016.json), [retest and endpoint geometry](../references/route002-retest-20261016.json), [combined all-family scorecard with run provenance](../references/route002-scorecard-20261016.json).

The invented XML and JSON expectations were frozen before reference execution or
engine tuning. Their basis is a hand-declared directed graph, explicit
motor_vehicle=no tags, a no_straight_on via-node relation and enumerated legal
simple paths. Provider agreement and source-map agreement are not independent
legal/physical road truth. All declared legal variants are accepted, so a longer
legal route caused by provider costing is not falsely failed.

Map SHA-256: `c2f908d9d0904e6aeb70cfd87c4b36d9af4871d5dd2da215dd37b55e076501cb`.
Oracle SHA-256: `ba4d350a828787d315e57cfc51dcc8aa153cefda671dba427d4df28a15a0d068`.
Both are identical in baseline and targeted retest. No case was removed, no
expected result relaxed and no DMN matching or routing policy was tuned.

## Highest-to-lowest shared-cohort ranking

Score = `10 * passed / 5` on the five explicitly listed shared static cases only;
equal scores share rank. Three state-specific checks stay visible but are not
mixed into the cross-engine denominator.

| Rank | Engine | Shared pass | Shared fail | Score /10 | Additional state cases |
| --- | --- | ---: | ---: | ---: | --- |
| 1= | DMN | 5 | 0 | 10 | 3 PASS |
| 1= | GraphHopper 11.1 | 5 | 0 | 10 | 3 UNSUPPORTED by current adapter |
| 1= | OSRM 5.27.1 | 5 | 0 | 10 | 3 UNSUPPORTED by current adapter |
| 1= | Valhalla 3.9.1 | 5 | 0 | 10 | 3 UNSUPPORTED by current adapter |
| 1= | openrouteservice 10.1.0 | 5 | 0 | 10 | 3 UNSUPPORTED by current adapter |
| 6 | BRouter 1.7.10 | 3 | 2 | 6 | 3 UNSUPPORTED by current adapter |

OsmAnd/Organic Maps lack executable app/native harnesses. HERE/Mapbox/TomTom/Google
lack configured permitted same-fixture access. Waze lacks an established permitted
automated routing interface. These seven families retain eight per-case NOT_RUN
reasons each and remain unranked, never zero-quality. The existing external
adapters do not express the same incoming-edge/arbitrary blocked-link state;
UNSUPPORTED describes those interfaces, not the complete products' capabilities.

## Exact case verdicts

| Case suffix | Frozen expectation | DMN | OSRM | Valhalla | GH | ORS | BRouter |
| --- | --- | --- | --- | --- | --- | --- | --- |
| prohibited-turn-detour | Avoid way10→way20; take a declared legal detour | PASS | PASS | PASS | PASS | PASS | PASS |
| fresh-origin-control | Return a legal route from the junction without incoming context | PASS | PASS | PASS | PASS | PASS | PASS |
| motor-access-bypass | Avoid explicitly prohibited shortcut way60 | PASS | PASS | PASS | PASS | PASS | PASS |
| disconnected-destination | Explicit no-route for disconnected exact destination | PASS | PASS | PASS | PASS | PASS | FAIL: relocated end |
| prohibited-target | Explicit no-route to target reachable only through prohibited access | PASS | PASS | PASS | PASS | PASS | FAIL: relocated end |
| reroute-incoming-turn | Retain incoming way10 restriction during recalculation | PASS | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| reroute-blocked-link | Exclude blocked way40, take remaining legal detour | PASS | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| reroute-no-legal-detour | Block both legal exits; return no-route | PASS | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |

Positive geometry must match one declared legal path: endpoints/path within 2 m,
forward progress with 0.5 m tolerance and length within 5 m of that path. A negative
control passes only for a documented route-search refusal. OSRM returned NoRoute;
Valhalla 442; GraphHopper ConnectionNotFoundException; ORS 2009. Generic server
errors, missing-map/no-segment errors or malformed geometry cannot pass as no-route.

## Diagnosis, comparison and retest

BRouter's retest returned:

| Case | Requested destination | Returned route end | End error |
| --- | --- | --- | ---: |
| disconnected-destination | synthetic (lat 1.003, lon 1.004) | (1.002, 1.002) | 248.6093 m |
| prohibited-target | synthetic (lat 1.002, lon 1.001) | (1.001496, 1.001496) | 78.6234 m |

Retained shapes follow allowed links toward relocated endpoints. This reproduces
an exact-destination contract failure, **not evidence that BRouter traversed
prohibited roads**. Its score remains 3/5 after diagnosis. DMN and four references
provide explicit no-route for these exact requested destinations. DMN takes graph
node IDs whereas reference interfaces snap input coordinates; this comparison
therefore includes endpoint/snap policy, not routing-search quality alone.

On the fresh-origin control, BRouter returned the longer 333.568 m legal detour;
other engines returned 111.178 m. Both satisfy the frozen legality contract and
pass. This case does not establish shortest-time quality or prove the provider's
internal reason for choosing the detour. No competitor advantage or DMN fault
was reproduced on this cohort, so an engine-policy change is not justified.

The verified harness improvements are route-end diagnostics and rejection of
malformed negative-route geometry as UNRESOLVED. Failing tests first reproduced
the missing diagnostics and malformed-geometry classification; all **381 tests**,
compile/privacy checks and targeted CI now pass. The reusable skill's
scripts/unified_preflight.py is absent from this research repository and remains
unavailable, not passed. Normal research CI now executes and retains DMN's eight
controls; its CLI fails if any DMN contract case fails. External execution CI
success alone does not mean every reference case passed.

## Remaining work

This verifies pure-core recalculation inputs, not a live rerouting controller.
Off-route evidence accumulation, cooldown, cancelling/suppressing stale route
responses, junctions/roundabouts, instructions, arrival, offline behaviour and
resource/device tests remain to be implemented or verified in bounded stages.
The next stage should freeze rerouting-controller lifecycle expectations before
implementation, using monotonic time and synthetic observations. Existing
coordinate-routing APIs cannot substitute for that controller's state.

The seven lost UK matches remain unresolved. Last UK map replay remains
17 correct / 0 confident wrong / 23 withheld; it was not rerun here. Its map-derived
labels are not surveyed truth, and this trial does not clear the promotion block.
No merge, release, APK, production DriveMate change or road-readiness claim.
