# Numbered navigation trials

The owner requested twelve external references plus DMN, exact case verdicts,
descending ranks, independent judgement, error diagnosis, improvements and
retesting. Begin with **GPS-001**, a deliberately small controlled correctness
trial. The previous UK map-generated geometry proxy remains separate.

## GPS-001 frozen acceptance

Six fixed scripted trajectories use an invented closed one-way road network.
Their expected positions and east/west direction are declared in
`benchmarks/fixtures/synthetic-gps-001.json` before changing the matcher. They
are not inferred from a DMN graph, a competing engine, or provider consensus.
This is an independent **analytical synthetic oracle**, not independently
surveyed UK road/GNSS evidence. The two fixture SHA-256 hashes bind each run.

Each case must return all four observations, each within 5 m of its declared
position, progressing in its declared direction. The six cases are east/west
clean movement, east/west lateral noise, and east/west movement across multiple
short graph links. For these unambiguous clean-input cases an abstention fails
the explicitly required-output check; it is reported as `missing_required_match`,
never as a confident wrong-road assignment. Partial responses cannot be aligned
by guessing their original indices. HTTP or setup errors are not engine verdicts.

All three checks must pass for a case to pass. The scoped synthetic score is
`10 * passed cases / 6`; sort descending and give equal scores equal ranks.
No averaging with other categories, timing or unavailable providers. This is a
finite functional contract, not an overall navigation-quality ranking. The
batch matching vs streaming interface distinction remains visible.

Every scoreboard includes the existing twelve external families and DMN.
OsmAnd, Organic Maps, BRouter and openrouteservice currently lack an integrated
permitted adapter for this GPS test; no claim that these products cannot navigate
is made. HERE, Mapbox, TomTom and Google lack configured permitted credentials
and same-fixture interfaces; no paid calls are authorised. Waze has no permitted
automated replay interface. All nine remain UNRANKED/NOT RUN with reasons. Adding
adapters is a separate capability task; names are never substituted by mocks.

## Execute

```sh
python -m benchmarks.navigation_trial --engine DMN --output results/gps001-DMN.json
python -m benchmarks.navigation_trial --reports results/gps001-DMN.json --output results/gps001-scorecard.json
```

The bounded `[gps-001]` research PR workflow executes version-pinned actual
OSRM, Valhalla and GraphHopper sequentially (`max-parallel: 1`) against the
identical invented road fixture and observation JSON. Engine results include
each case's checks, errors, missing observations and exact failure reasons.
No provider result counts as executed until its job and artifact are checked.

Preserve the original failing DMN run before implementing a fix. Retest the
same cases, safety regressions and separately authored counterexamples. A case
viewed during diagnosis is not claimed as a blind holdout, even if its original
fixture split says `held_out`. Independent real-world legality, physical-road
identity, GNSS calibration and device navigation still require other evidence.
Never claim universal superiority; use better tested references to identify
specific deficits and aim to exceed them on harder, independently justified tests.

## Resume after UK topology investigation

The bounded diagnostic run 38810752808 at
`f17131dd2ea35b80b94657177074fbbd706aaa6a` identifies backward-adjacent alternatives
in all seven lost matches; it does not safely resolve them. Full evidence is in
`references/gps001-uk-topology-20261015.json`. Keep the 40-case coverage tradeoff
and promotion block open. Do not repeat this unchanged diagnostic automatically.
The next unblocked stage is GPS ambiguity/fault/recovery: freeze explicit
analytical cases and required abstention/recovery expectations before tuning,
then execute applicable permitted references sequentially and preserve interface
limitations per case. No surveyed UK truth has been obtained.

## Additional runnable reference: openrouteservice

The owner requested execution of previously unrun references or alternatives.
GPS-001 now has a self-hosted openrouteservice 10.1.0 **pointwise snapping**
adapter. Acceptance and fixture hashes remain frozen; no engine tuning or DMN
policy change is authorised by a missing result. This endpoint returns positions
in input order, with explicit null slots; a partial response is never aligned by
guessing. The same six position/output/progression checks apply. Observed
coordinate progression is not proof that ORS inferred legal driving direction;
this endpoint has no temporal inference. Do not extrapolate its score to that.

The bounded `[ors-gps001]` CI job uses the official v10.1.0 JAR, SHA-256
`46b83b353eaf8830a1b53cad91d027e00547cd9a00e86efddd64a45335bfb8e1`, Java 25,
the same invented map, driving-car, radius 20 m, no elevation, disabled tiny-network
pruning and no CH/LM/core preparation. No hosted API calls or keys. Startup or HTTP
errors are unavailable execution, never case failures or passes. Source contract:
https://github.com/GIScience/openrouteservice/blob/v10.1.0/ors-api/src/main/java/org/heigit/ors/api/controllers/SnappingAPI.java

BRouter can be self-hosted for routing, which needs its own frozen route contract;
OsmAnd and Organic Maps need executable app/native harnesses. Their GPS-001
adapter gaps remain work, not evidence of poor navigation. Commercial/Waze access
restrictions remain unchanged. The original twelve-family roster is preserved.

Executed outcome: run 38814980108 at `e80e54a9b4ea3195dede7bcba727c3c65ad8f156`
completed all six ORS requests: four PASS, two UNSUPPORTED (explicit ORS 8010
outside-graph-bounds rejection). Full-cohort score remains unassigned; see the
expanded scorecard and GPS_001_RESULTS.md. A scorecard regression test now ensures
unsupported cases cannot receive a full score. Next additional original-roster
reference work is a separately frozen routing contract for self-hosted BRouter,
which may also enable ORS routing comparisons. Do not substitute snapping for
ambiguity, fault, temporal-recovery or legal-driving checks.

## ROUTE-001 frozen acceptance: BRouter integration stage

Four explicitly declared synthetic routes use a translated invented one-way
rectangular cycle. Bottom runs east, right north, top west, left south. Two
requests travel directly east/west; two request the opposite direction and must
follow the full permitted detour. Each simple directed path is unique. Expectations
are in `benchmarks/fixtures/synthetic-route-001.json`, fixed before BRouter
execution or matcher tuning. This is an analytical synthetic oracle, not
independent surveyed road or legal truth. GPS-001 rankings stay separate.

Require both endpoints within 2 m, all returned vertices and quarter/mid/three-quarter
segment samples within 2 m of the declared path, monotonically forward path
progress (0.5 m numerical tolerance) and path length within 5 m of expectation.
No ETA or performance ranking. Synthetic score: `10 * passed / 4`, ties share
rank. All twelve external families plus DMN retain per-case execution status.
Only BRouter and DMN are scheduled in this bounded integration stage; existing
OSRM/Valhalla/GraphHopper/ORS route adapters still need integration with this new
contract, so no cross-category GPS score is substituted for routing execution.

BRouter uses the official 1.7.10 release ZIP (SHA-256
`023fec3ba997758e8cd7ab9e1bae52e962af3f00b57683e3de86b84ffad01532`), Java 17,
car-vario defaults. Map builder stages follow upstream MapcreatorTest/OsmFastCutter,
PosUnifier and WayLinker using our invented PBF, no elevation data or downloads.
Missing filter profiles come from source commit
`4d2639af77ea5ed9c30d3e400764eb6f9e8522da`. Record JAR, profile, lookup and generated
segment hashes, exact run SHA and CI URL. Startup/import/HTTP errors remain
unavailable execution; no mocked or inferred route may count as a pass.

ROUTE-001 executed successfully in run 38815930888 at
`f8e7cc3d4e5bb07b82ca9a7cbbba88ee7eac420d`: DMN 4/4, BRouter 4/4, tied
10/10 on the frozen synthetic one-way cohort only. See ROUTE_001_RESULTS.md and
references/route001-brouter-20261015.json. Do not repeat this unchanged integration
run automatically. Complete remaining applicable reference adapters and harder
legal/access cases in bounded stages; preserve the independent GPS ambiguity and
UK coverage work rather than treating this small tie as road readiness.

## GPS-002 frozen batch: stream ambiguity, faults, gaps and recovery

Sixteen analytical synthetic cases and per-event expectations are declared in
`benchmarks/fixtures/synthetic-gps-002.json` before tuning; a separate invented
feeder joins only the northern of two parallel one-way roads. Road topology is
hand-declared, while clock/quality expectations come from explicit engineering
limits: anchor age 20 seconds, at most two unresolved samples, fix age 10 seconds,
physical plausibility screen 90 m/s, weak accuracy above 35 m. These limits are
contracts under test, not independently calibrated GNSS or road/legal truth.

Cases cover equally plausible first/repeated observations; a fresh feeder anchor;
single bad-speed and weak-accuracy recovery; burst expiry; long-gap withholding
and reacquisition; duplicate, out-of-order, stale and future timestamps; an
impossible jump; unavailable heading; stationary ambiguity; and session reset.
Require every declared event status, the expected directed way for positive
controls, no edge claim on withheld/rejected outputs, and unchanged trusted fix
where a packet is rejected. Every assertion must pass for its case to pass.
Score = `10 * passed / 16`; do not mix with GPS-001 or routing scores.

This is a streaming input-quality/history contract, not a batch position-snap
contract. Existing OSRM/Valhalla/GraphHopper batch APIs do not expose equivalent
reception clocks, resets or trusted stream state. ORS pointwise snap and BRouter
routing likewise cannot express it. Mark these integrated interfaces UNSUPPORTED
per case, not bad engines or fabricated fails. OsmAnd/Organic Maps need app/native
lifecycle harnesses; four commercial services lack configured permitted access;
Waze has no established permitted automation. Retain all twelve external families
plus DMN with exact per-case reasons. Only DMN has a judged cohort in this stage;
its numerical score is conformance, not a competitive quality ranking. Do not
run heavyweight batch routers merely to substitute positions for lifecycle checks.

Execute `python -m benchmarks.gps_fault_batch --output results/gps002-DMN.json`.
The normal research CI runs this small deterministic batch and preserves its
per-event report. Map and oracle SHA-256 bind each report. No matcher tuning is
warranted unless a fault is reproduced. UK coverage remains unresolved, and no
physical tunnel navigation or device readiness is established by a no-fix gap.
