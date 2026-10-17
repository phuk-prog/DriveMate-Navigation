# ARRIVAL-001: corroborated arrival safeguards

DMN's new isolated arrival controller passes **20/20 frozen cases** (conformance
10/10). All417 tests pass in CI, including nine additional controller safety
controls and a scorecard-integrity test. There was no arrival controller at the
inspected baseline; availability was UNAVAILABLE, not an invented0/20 score.

This is a **synthetic analytical lifecycle test**, not independently surveyed
road truth or measured GNSS. The replay computes21 actual DMN core routes on
JUNCTION-001's invented map, checks their explicit edge paths, and supplies
synthetic positions, route-progress distances and reliability/on-route decisions.
It does not derive these assessments from GPS, map matching or Android services.

## Frozen acceptance and exact verdicts

Arrival requires two reliable on-route observations at least1000ms apart, each
at most10000ms old at receipt time, distance to destination<=20m, accuracy<=15m,
and remaining route distance in[0,25]m and no greater than route length. Both
samples must remain fresh when arrival is emitted. These are declared engineering
limits, not physically calibrated guarantees. Invalid/rejected, weak or off-route
samples clear provisional evidence. A subinterval sample cannot slide the anchor.
A session/route change resets evidence and changes its token; stop prevents arrival.
Arrival is emitted once and remains latched until begin/stop.

| Frozen case suffix | Required behavior | Result |
|---|---|---|
|corroborated|Candidate after first fix; arrive after second|PASS|
|near-destination-early-progress|No arrival with100m remaining despite proximity|PASS|
|parallel-road|No arrival from nearby off-route observations|PASS|
|outside-radius|No arrival outside20m|PASS|
|weak-accuracy-recovery|Weak fix clears candidate; two fresh good fixes recover|PASS|
|unreliable-recovery|Unreliable fix clears candidate; two good fixes recover|PASS|
|stale-interrupts|Reject stale packet; restart corroboration|PASS|
|future-interrupts|Reject future packet; restart corroboration|PASS|
|duplicate-interrupts|Duplicate cannot count; restart corroboration|PASS|
|out-of-order-interrupts|Older packet cannot count; restart corroboration|PASS|
|overshoot|Negative remaining distance cannot announce arrival|PASS|
|unknown-progress|Unknown progress cannot announce arrival|PASS|
|signal-gap|Expired first fix cannot corroborate later arrival|PASS|
|stop|Stopped session remains inactive|PASS|
|context-change|North candidate cannot carry into south destination|PASS|
|latched-once|Emit ARRIVED once; subsequent packets say ALREADY_ARRIVED|PASS|
|accuracy-boundary|Exactly15m accuracy remains eligible|PASS|
|remaining-boundary|Exactly25m remaining remains eligible when also nearby|PASS|
|minimum-time-separation|500ms sample cannot count or slide original anchor|PASS|
|delayed-history-expiration|Expire prior evidence against receipt clock, not sample clock|PASS|

Case IDs use the prefix`ARRIVAL-001-`. PASS includes correctly withholding or
rejecting arrival where the oracle requires it. WITHHELD means **no arrival
announcement because the current evidence does not qualify**; it is not an
unconfirmed positive arrival or a withheld test score. Every per-event expected
and actual status/check is retained in the executed report.

## Reference coverage and scoring

Only DMN has an executed comparable arrival lifecycle cohort. Its10/10 is
conformance, **not a competitive quality ranking**. Score=`10*passed/20` for a
complete judged cohort; unavailable/unsupported cohorts receive no score.
All twelve external families plus DMN and all twenty per-case reasons are in
[arrival001-scorecard-20261016.json](../references/arrival001-scorecard-20261016.json).

OSRM, Valhalla, GraphHopper, openrouteservice and BRouter are UNSUPPORTED through
the integrated static routing/directions endpoints for every case: they cannot
accept equivalent live progress/quality, reception clocks and session state.
Their static destination/“arrive” instructions are not evidence that a driver
has arrived. No heavyweight static routing execution can substitute for this
contract; none was launched. This does not claim the products lack arrival logic.
The last actually executed static interface configurations remain OSRM5.27.1
car.lua/MLD, Valhalla3.9.1 auto, GraphHopper11.1 car/CH, ORS10.1.0 driving-car/
fastest and BRouter1.7.10 car-vario/timode3, from JUNCTION-001's version-pinned
workflow and recorded hashes. These versions are provenance for the current
integrated interfaces, not newly executed arrival engines.

OsmAnd and Organic Maps are NOT_RUN: executable app/native live-arrival harnesses
are missing. HERE, Mapbox, TomTom and Google Maps are NOT_RUN: no configured
permitted access and equivalent live-arrival harness. Waze is NOT_RUN: no
established permitted automated live-arrival replay interface. No credentials,
paid calls, proprietary data, personal traces or unsupported access were used.
There is no competitor arrival result to diagnose or claim to exceed here.
Previous scoped GPS/routing/junction rankings and their failures remain intact.

## Additional controls and diagnosis

Nine additional controller tests pass: invalid positions (NaN/infinity/range/
boolean/malformed), invalid progress/accuracy, old context token rejection,
pre-context timestamps, longitude wrap, exact evidence-age boundary, backward
receipt clock rejection, invalid policy parameters and atomic invalid begin.
These include multiple subcases and are engineering controls, not blind holdouts.
A separate scorecard test retains13 families and rejects incomplete DMN cohorts.
The two initial acceptance tests failed because the capability was absent, then
passed after implementation. All20 frozen cases and added safety controls pass;
no reproduced fault required changing their oracle or relaxing acceptance.

The delayed-history case explicitly exercises the prior rerouting lesson: a
sample timestamp2000ms delivered at12000ms cannot reuse evidence timestamp1000ms.
The earlier evidence is already11000ms old even though the timestamps are only
1000ms apart. Current code restarts corroboration and waits for two fresh eligible
samples. Thresholds, route/destination context and arrival state remain separate
from UI, voice, networking and storage.

## Provenance and reproduction

- Inspected research baseline:`a6c414927de6e657ab051f393a6ceace9bdbd948`.
- Fixture freeze:`fb3f152ef75f8131c2e869f906f2a8300dd6fc6d` before implementation.
- Executed implementation:`3057a28c3dc50a9ecaa10f6ad0452832e1a29ea0`.
- CI:[38857319048](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38857319048), job116831599535, success;417 tests, all20 cases, existing GPS/routing/rerouting/junction regression batches.
- Map SHA256:`8b9d409865dd0b272456c2b99575c8dd29d3459602db7016377889b9b00ab465`.
- Oracle SHA256:`c6b95ec811aef34ee1910a1d4d314141d63250190f8d9ec09434a990dd2bcc71`.
- [Availability baseline](../references/arrival001-before-20261016.json) and [executed report](../references/arrival001-after-20261016.json) bind controller/harness hashes, configuration, actual source SHA, job/run and per-event results. The CI artifact contains the complete report/coverage too.

Run`python -m benchmarks.arrival_lifecycle_trial --output results/arrival001-DMN.json`.
Local full tests, compile, privacy guard and whitespace checks passed. The canonical
`scripts/unified_preflight.py` is absent/unavailable and was never counted as
passed. Normal CI now gates and retains ARRIVAL-001 automatically. No prior
matcher/router/rerouting policy was changed. Remove the isolated controller and
its research gate to roll back this new capability; no production app was touched.

The UK evidence was re-read: the seven backward-adjacent candidate cases remain
unresolved; no new independent truth safely resolves them. The40-case result stays
17 correct/0 confident wrong/23 withheld. Promotion remains blocked. This isolated
arrival module is not wired to actual route progress, GPS, phone lifecycle or
Android navigation; no real arrival or road-readiness claim follows from these
passes. Next bounded stage: offline data integrity/coverage and failure recovery,
then bounded resource measurement and integration. Avoid repeating unchanged
heavy reference runs or the unresolved UK diagnostic without new evidence.
