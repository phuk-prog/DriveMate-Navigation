# REROUTE-001: research rerouting lifecycle and stale-history fix

DMN now has an isolated research rerouting controller: corroborated off-route
requests, cooldown, one logical pending request, context/stop cancellation and
fresh-current-response installation. **16/16 frozen lifecycle cases and 3/3
additional adversarial controls pass.** An additional control reproduced a
stale-corroboration bug in the first implementation; the narrow fix and failing
evidence are preserved. This is not Android integration or real GNSS evidence.

## Immutable source and execution

- Live preimplementation source: `ac3668c35418cce92e7d1ed5c1d0befcc3a2a64e`. No lifecycle controller existed; capability was UNAVAILABLE, not zero-quality or a scored failure.
- [Frozen acceptance source](https://github.com/phuk-prog/DriveMate-Navigation/commit/50236e5eb5e40c17aa30502d002e82565c03ef7a): sixteen cases published before implementing the controller.
- [First implementation and reproduced fault](https://github.com/phuk-prog/DriveMate-Navigation/commit/df2c1e45e8117f5b90f2fa1d5390e74173f131be): frozen16/16; additional2/3. This intermediate version was tested locally; no CI pass is claimed for it.
- [Fixed source](https://github.com/phuk-prog/DriveMate-Navigation/commit/1824621281fa4d9343a69260cd93c1fa0a956198), [successful CI38847369324](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38847369324), job116800840072: sixteen frozen plus three additional pass, all389 unit tests pass.

[Availability baseline](../references/reroute001-before-20261016.json),
[first implementation's exact failing event evidence](../references/reroute001-first-implementation-20261016.json),
[fixed CI reports and all-family coverage](../references/reroute001-after-20261016.json).
Source hashes for the controller and harness are recorded inside each report.
No freeze case or threshold was relaxed to obtain the retest result.

## Frozen behaviour and results

Defaults are explicit engineering contracts: two reliable off-route samples,
at least1000ms spacing, maximum10000ms observation age, minimum30000ms between
request starts, maximum15000ms pending-request age. Time is nonnegative monotonic
milliseconds. These thresholds are not calibrated physical road/GNSS evidence.

| Frozen case suffix | Required behaviour | Retest |
| --- | --- | --- |
| corroborated-install | Two independent samples allow one fresh successful replacement | PASS |
| on-route-resets | Intervening on-route evidence breaks corroboration | PASS |
| weak-sample-resets | Weak evidence breaks corroboration; fresh samples recover | PASS |
| timestamp-rejection | Reject stale/future/duplicate/backwards packets as corroboration | PASS |
| independent-spacing | Rapid repeats do not count as independent samples | PASS |
| one-pending-request | Additional observations do not create duplicate pending work | PASS |
| cooldown-and-recovery | Respect30s cooldown; a long gap needs fresh corroboration | PASS |
| on-route-cancels | Returning on route suppresses a late replacement | PASS |
| weak-sample-cancels | New unreliable evidence suppresses pending installation | PASS |
| context-change | Old-context callbacks cannot replace the new session's route | PASS |
| stop-cancels | Stop clears active route and rejects late callbacks/observations | PASS |
| stale-evidence-result | Do not install using off-route evidence older than10s | PASS |
| request-timeout | Fresh observations do not extend a request beyond15s | PASS |
| request-age-boundary | A current fresh response at exactly15s may install | PASS |
| failed-route-preserves | Actual RouteNotFound preserves current route and cooldown | PASS |
| unknown-callback | Unknown token cannot clear the legitimate pending request | PASS |

Positive controls require successful route installation, so simply suppressing
all requests or callbacks cannot pass. Each case also checks every declared
intermediate request decision and expected installed route. Unit controls cover
clock rollback, malformed policies/samples and eligibility of replay evidence.

## Verified fault and narrow fix

The first implementation checked history expiry using the difference between
the two sample timestamps. The additional case supplies:

1. First sample timestamp1000, received at1000.
2. Second sample timestamp2000, delayed until monotonic time12000.

The second sample is exactly10000ms old and still eligible. The first sample is
11000ms old and has expired, yet the old timestamp-difference check treated the
pair as just1000ms apart and started a request. The failing unit test and event
trace reproduce this premature request.

The fix compares **request time minus the counted sample timestamp** against
maximum observation age. The delayed sample now starts a new evidence sequence;
a subsequent fresh independent sample can recover. The separate exact-boundary
control still permits a first sample exactly10000ms old. Unknown route progress
also correctly cancels pending installation. These three additional cases were
authored after inspecting the implementation; they are adversarial controls,
not blind holdouts.

| Cohort | First implementation | Fixed retest |
| --- | ---: | ---: |
| Original frozen lifecycle cases | 16/16 | 16/16 |
| Additional freshness/progress controls | 2/3 | 3/3 |

The added evidence does not turn the original UNAVAILABLE baseline into an
invented0/16 score. It demonstrates a new research capability and a reproduced
implementation fault fixed during development.

## Planner, oracle and interface limits

The harness actually imports the frozen ROUTE-002 map and calls DMN shortest_route
for initial, legal detour, replacement and unreachable paths. The retest makes
**41 actual local core route calculations** across the two cohorts; expected edge
chains are independently declared. Clock delivery and reliability/on-route
assessments are synthetic inputs. They are not sensor measurements, actual
asynchronous workers or mocked external-engine passes.

Map SHA-256: `c2f908d9d0904e6aeb70cfd87c4b36d9af4871d5dd2da215dd37b55e076501cb`.
Original oracle: `467f51d173abb37b34d0485b3bed4cccd2c09c287d18763b5489292d87a64cee`.
Additional oracle: `389d2eb25dd4a13e050dba56f582e7858175c8892dbd9c58ec3b4e8ad6e63fa4`.
All are identical before/after the freshness fix. Python3.11 runs CI; controller
configuration, source hashes and per-event checks are in the reports. Normal CI
now executes both cohorts, retains their artifact and fails for any case failure.
Compile and privacy checks pass. Cloud skills were unavailable in this invocation;
no missing skill/preflight was counted as passed.

The sixteen-case conformance formula is `10 * passed / 16`: DMN16/16 =10/10.
Only DMN has a judged controller cohort. No competitor quality ranking or
superiority claim follows. All twelve external families retain16 per-case reasons; the report also includes
separate all-family coverage for the three additional adversarial controls:

| Families | Controller interface status | Reason |
| --- | --- | --- |
| OSRM, Valhalla, GraphHopper, openrouteservice, BRouter | UNSUPPORTED | Current integrated routing/batch endpoints do not expose equivalent off-route evidence, session, cooldown and callback-installation state |
| OsmAnd, Organic Maps | NOT_RUN | Executable app/native lifecycle harness not implemented |
| HERE, Mapbox, TomTom, Google Maps | NOT_RUN | No configured permitted access and equivalent lifecycle harness |
| Waze | NOT_RUN | No established permitted automated lifecycle interface |

No heavyweight reference was rerun merely to substitute a path response for
controller state. Existing GPS-001/ROUTE-001/ROUTE-002 actual reference results
remain unchanged. Unsupported describes an integrated interface, not a claim
that those products cannot reroute.

## Remaining programme and promotion block

This component suppresses stale installation; it does **not** physically cancel
or serialize underlying route computations. Its future executor must own that.
It does not yet consume real matcher/progress output, run a location service or
emit active guidance. Android lifecycle/permission/offline/resource validation
remains unperformed. No production DriveMate files were changed.

Next bounded work: freeze shared junction/roundabout/instruction expectations and
execute applicable reference maneuver APIs, then implement justified DMN guidance
behaviour. Arrival, offline reliability, resources and controller integration
remain open. Do not repeat this unchanged lifecycle cohort as new research.

The UK coverage tradeoff remains unresolved: last map replay17 correct /0
confident wrong /23 withheld, including the seven backward-adjacent alternatives.
No UK replay or confidence loosening occurred here. Promotion remains blocked;
no merge, release, APK or road-readiness claim.
