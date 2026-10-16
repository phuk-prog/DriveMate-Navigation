# Numbered navigation trials

**Owner-approved prospective policy (16 October 2026):**
[DMN_PERMANENT_TESTING_POLICY.md](DMN_PERMANENT_TESTING_POLICY.md) supersedes
any earlier recommendations here about universal score-first rankings, running
only DMN on post-fix retests, or automatically improving without review. Future
tests rank each category by actual measured units; full and partial cohorts,
and verified and provisional source truth, remain separate. After explicit
approval of an improvement, newly run DMN **and every available applicable
competitor** on the complete affected comparable frozen set. Earlier entries
below are historical test records and are **not** retroactively rescored or
re-executed by this documentation change.

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

GPS-002 completed: run 38816950211 at
`38933527cb80ff09e0c756bb8717fdd6fe2945e2`, DMN 16/16, no matcher policy
changes. See GPS_002_RESULTS.md and references/gps002-stream-batch-20261015.json.
Only DMN was judged; other current endpoints are unsupported or lack lifecycle
harness/access, with per-case reasons. Normal CI now gates this frozen batch.
Next bounded work should add other applicable self-hosted engines to ROUTE-001,
then frozen routing access/turn/disconnection and rerouting cases. Preserve the
UK ambiguity promotion block and the remaining app/native streaming harness work.

## ROUTE-001 additional reference execution batch

The `[route001-refs]` bounded workflow executes OSRM 5.27.1, Valhalla 3.9.1,
GraphHopper 11.1 and openrouteservice 10.1.0 sequentially (max-parallel 1), plus
DMN on the same frozen four cases. Fixture, oracle, tolerances and acceptance are
unchanged. Retain BRouter's earlier actual execution with its own run SHA rather
than claiming it was rerun. Geometry is requested explicitly: OSRM full GeoJSON,
Valhalla polyline6, GraphHopper unencoded calculated points, ORS directions GeoJSON.
The decoder is checked against a published polyline test vector and truncation
controls. No ETA/profile-cost ranking is inferred from these unique-path cases.
A scorer now rejects incomplete judged outcomes instead of assigning a score to
unsupported cases; invalid/incomplete engine execution remains unavailable.
After this expansion, freeze separate access/turn/recalculation expectations
before tuning, preserving UK unresolved matching evidence and promotion block.

ROUTE-001 expansion completed: run 38818121643 at
`4b5cc0a72c82c71bf26cf8ac5a643f2ebd7b6185`, OSRM/Valhalla/GraphHopper/ORS
and DMN each 4/4. Combined with BRouter's prior executed 4/4, six systems tie
10/10 on the unchanged four-case synthetic one-way contract. Seven external
families remain unranked with exact per-case reasons. No engine policy changed.
See ROUTE_001_RESULTS.md and references/route001-expanded-20261015.json plus
route001-expanded-scorecard-20261015.json. Do not rerun unchanged heavy engines.
Next bounded stage: freeze and execute routing access/turn/disconnection and
rerouting-context cases. These harder cases have not yet been executed; the
four-case tie does not clear them, and does not clear the UK coverage block.

## ROUTE-002 frozen legality/recalculation stage

Eight hand-authored synthetic cases use a new explicit directed map and JSON
oracle: prohibited-turn detour, unrestricted fresh-origin control, motor_vehicle=no
shortcut bypass, disconnected destination, prohibited-access destination,
rerouting with an incoming prohibited turn, rerouting around a blocked link and
safe no-route when all legal detours are blocked. Expectations are analytical,
not independently surveyed/legal road truth. All declared legal simple path
variants are accepted: different provider turn costs must not become fake
legality failures. A road geometry must satisfy ROUTE-001's 2 m endpoint/path and
5 m length tolerances for one enumerated legal path. No-route requires an explicit
route-search refusal, never generic HTTP errors, missing maps or invented output.

Freeze `synthetic-route-002.xml` and `.json` before tuning. Five static cases are
shared by DMN, OSRM, Valhalla, GraphHopper, ORS and BRouter; execute all permitted
local engines sequentially (`[route002-refs]`, max-parallel 1). Rank only the five
fully judged shared cases, score `10 * passed / 5`, ties share rank. Preserve
all eight cases for every family. Three state cases use DMN incoming-edge or
arbitrary blocked-link state: existing external adapters cannot express the same
state and remain UNSUPPORTED for those cases, not failed. Seven unavailable
families remain unranked with per-case NOT_RUN reasons. An unresolved shared
case prevents ranking that engine on the full five-case cohort.

Use prior version-pinned engines/configuration families, the same invented map,
full geometry, no elevation and disabled tiny-network pruning. BRouter uses its
actual official builder and car-vario profile, with prepared-map/profile hashes.
Generic server failures, timeouts and ambiguous provider errors are UNRESOLVED or
unavailable, not passed no-route. Successful CI means execution/evidence checks
passed; inspect case verdicts before claiming a quality result. No DMN engine
policy has been changed to author this harness. Preserve the UK coverage block.

ROUTE-002 completed: baseline run38839461917 at
`061fe6187a389ba197c8d72b50506707ca85f0eb` executed all five permitted references
sequentially and DMN. Shared static cohort: DMN/OSRM/Valhalla/GraphHopper/ORS5/5,
BRouter3/5. Targeted BRouter retest38839878414 at
`e47ea4586faf2a3f2cc0e3c453b08b63fab5e78d` confirms relocated endpoints248.6093m
and78.6234m from unreachable exact destinations; it does not show prohibited-road
traversal. Map/oracle/acceptance unchanged. DMN also passes three state controls,
8/8 total. Full references remain unsupported for those state cases or not run
with reasons; common score uses five cases, not eight. See ROUTE_002_RESULTS.md
and route002-before/retest/scorecard-20261016.json. No DMN engine policy changed.
381 tests pass; normal CI now gates/retains DMN's eight cases. Do not repeat the
unchanged heavyweight cohort automatically. Next bounded stage: rerouting
controller lifecycle (off-route corroboration, cooldown, stale/cancelled result
suppression) before junction/roundabout/instruction/arrival/offline/resource work.
The UK coverage tradeoff and promotion block remain open.

## REROUTE-001 frozen lifecycle acceptance

Sixteen analytical synthetic cases in synthetic-reroute-001.json are fixed before
implementing the missing controller. Existing shortest_route recalculates paths,
but no module currently owns off-route corroboration, cooldown, pending callbacks
or session cancellation. This baseline capability is unavailable, not a failed
or zero-quality engine score. Existing GPS/ROUTE evidence remains unchanged.

Require two reliable off-route observations at least1000ms apart, maximum10000ms
observation age, minimum30000ms between request starts, one pending request,
maximum15000ms request lifetime, and current fresh off-route evidence before
installing a result. Returning on route, new weak evidence, stopping or changing
context cancels prior pending state. Duplicate/out-of-order/stale/future packets
cannot count as corroboration. Failed/no-route results preserve the active route.
Clock inputs are nonnegative monotonic milliseconds. Frozen cases include the
request-age boundary and recovery after bad samples, gaps, cooldown and context
changes. These are engineering contracts, not calibrated physical thresholds.

The harness must calculate actual DMN routes on the frozen ROUTE-002 map; it
simulates delivery times and reliability/on-route decisions explicitly. No fake
external result may be counted as execution. Batch OSRM/Valhalla/GraphHopper,
ORS snapping/directions and BRouter routing endpoints do not expose this full
controller lifecycle, so their integrated interfaces are UNSUPPORTED per case.
The remaining seven families lack lifecycle harness/access and remain NOT_RUN.
Keep all twelve plus DMN visible; only a complete judged16-case controller cohort
can receive `10 * passed / 16`, and it is not a competitor quality ranking.
No Android service, real route-progress/GPS integration or device readiness is
established by this isolated research component. Keep UK promotion blocked.

REROUTE-001 completed: fixture freeze50236e5eb5e40c17aa30502d002e82565c03ef7a;
first implementationdf2c1e45e8117f5b90f2fa1d5390e74173f131be preserved a reproduced
stale-corroboration fault. Fixed1824621281fa4d9343a69260cd93c1fa0a956198,
CI38847369324:16/16 frozen cases plus3/3 additional controls,389 tests. Additional
controls were2/3 before the fix and are not blind holdouts. There was no prior
controller: availability baseline is UNAVAILABLE, never an invented0/16 score.
See REROUTE_001_RESULTS.md and reroute001-before/first-implementation/after JSON.
No external controller cohort is executed; all twelve remain visible with exact
unsupported/not-run reasons. This new isolated research controller suppresses
stale callbacks but does not physically cancel/serialize computation or integrate
Android/GPS/progress yet. Next bounded stage: junction/roundabout/instruction
cases and applicable actual maneuver references; then arrival/offline/resources
and integration. Keep the UK coverage tradeoff/promotion block open.

## JUNCTION-001 frozen acceptance

Five synthetic cases fix two90-degree turns and directed roundabout exits1–3
before guidance implementation. Oracle paths use explicit invented coordinates.
Incoming-only feeder at the first exit and motor_vehicle=no spur between first
and second exits must not count. Only accessible outgoing spokes count once per
visited junction; prohibited turns cannot count. Principal maneuvers must exactly
match the oracle; start/arrival/continue and the paired roundabout-exit instruction
are administrative. Other unexpected turn instructions fail. Require the existing
ROUTE-001 geometry checks (2m endpoints/path,5m length,0.5m progress).

Run actual DMN and all five available reference directions interfaces sequentially
with instructions enabled. Retain raw maneuver fields. Rank only complete judged
five-case cohorts,10*passes/5 with ties. All12 external families remain visible.
Missing execution is NOT_RUN; unparseable output is UNRESOLVED, never a pass.
DMN currently has no maneuver generator: availability baseline UNAVAILABLE, not0/5.
No voice timing, lane guidance, multi-lane exit counting, real-map legal truth or
Android integration is established. UK coverage/promotion remains blocked.

JUNCTION-001 completed: freeze6761d694d9eeabd1e3df648f77f9c6c5012b1a12;
initial sequential reference run38853990046 at90f51f43c90d59b260fc88a873843ff4deb7c478;
confirmation38854474267 at2996b127760764131530596e156c5a3e58ea0930.
DMN/OSRM/GraphHopper/ORS5/5 tied10/10; BRouter4/5 (8/10), Valhalla3/5 (6/10).
BRouter truncates the right-turn path111.195m before destination; Valhalla reports
exit2 for exits1 and3 despite correct paths. Both failures repeat with raw
coordinates retained. All12 external families remain visible; seven unranked
with per-case access/harness reasons. DMN's new isolated generator passes5/5
and nine additional safety controls;405 tests. No baseline generator existed,
so never call its baseline0/5. See JUNCTION_001_RESULTS.md and junction001 JSON.
Next bounded stage: frozen arrival safeguards, then offline reliability/resources
and integration. No voice/lane/device/road-readiness claims. Preserve unresolved
UK17/0/23 evidence and promotion block. Do not repeat unchanged heavyweight runs.

## ARRIVAL-001 frozen acceptance

Twenty analytical synthetic arrival cases are frozen before implementing the
missing controller. Reuse JUNCTION-001's invented map and actual DMN routes from
node1 to north3/south4. Progress, reliability and on-route assessments are supplied
explicitly by the replay; they are not measured GPS or integrated map matching.
Arrival requires destination distance<=20m, remaining route distance in[0,25]m,
accuracy<=15m, reliable/on-route=true and two qualifying observations separated
by>=1000ms. Both observations must remain<=10000ms old at receipt time. Duplicate,
out-of-order, stale/future or invalid observations clear provisional evidence.
A too-close-in-time qualifying sample cannot move the original corroboration
anchor. Negative/unknown progress, excessive accuracy, unreliable/off-route fixes
and distance outside the radius withhold and clear provisional evidence. A long
gap restarts corroboration. A stopped session cannot arrive; destination/route
change starts fresh; arrival emits once and stays latched until begin/stop.
Clock values are nonnegative monotonic milliseconds. Thresholds are engineering
contracts, not physically calibrated arrival guarantees.

Cases include positive corroboration, proximity without progress, parallel-road
proximity, outside radius, weak/unreliable recovery, stale/future/duplicate/order
interruptions, overshoot, unknown progress, gap, stop, destination change, single
arrival emission, threshold boundaries, minimum separation and delayed history.
No existing arrival controller is present: baseline UNAVAILABLE, not0/20.
Batch OSRM/Valhalla/GH/ORS/BRouter route endpoints expose static final instructions,
not equivalent live fix/progress arrival state; mark integrated interfaces
UNSUPPORTED per case. Seven other families lack permitted access or executable
app/native lifecycle harnesses: NOT_RUN. Retain all12 plus DMN. Only fully judged
20-case cohorts may receive10*passed/20; a solo DMN score is conformance, never a
competitor ranking. No heavyweight static router runs can substitute for this
state contract. Preserve UK17/0/23 ambiguity and promotion block.

ARRIVAL-001 completed: fixture freeze fb3f152ef75f8131c2e869f906f2a8300dd6fc6d,
implementation 3057a28c3dc50a9ecaa10f6ad0452832e1a29ea0, CI38857319048/job116831599535.
DMN20/20 frozen cases, nine additional controller safety groups and417 full tests
pass. The new isolated ArrivalController requires progress+proximity and two
fresh eligible observations, scopes state to a context token, clears unsafe
provisional evidence and emits arrival once. There was no prior controller;
baseline unavailable is never0/20. Replay makes21 actual DMN core route calls
but supplies synthetic GPS/progress/reliability; no Android/GNSS integration.
The five integrated static reference APIs are UNSUPPORTED for this live arrival
contract; seven other families remain NOT_RUN with exact per-case reasons. All13
remain visible. A DMN-only10/10 means conformance, not competitor superiority.
See ARRIVAL_001_RESULTS.md and references/arrival001-before/after/scorecard JSON.
Next bounded stage: offline integrity/coverage and failure recovery, then bounded
resource measurement and integration. Keep UK17/0/23 unresolved and promotion
blocked. Do not repeat unchanged heavyweight references or UK diagnostics.

## OFFLINE-001 frozen activation/integrity acceptance

Eighteen synthetic cases freeze a research in-memory package wrapper before
implementation. Input is immutable XML bytes and a caller-trusted manifest, not
a ZIP/file installer. Manifest schema1/format dmn-osm-xml-v1 must bind exact byte
length, lowercase SHA256, required node anchors and complete source attribution.
Reject unknown schema/format, mismatched size/hash, missing provenance/coverage,
malformed or unsupported XML and payloads above100000bytes in this replay. Verify
all integrity/coverage checks before replacing the active snapshot. A rejected
update preserves the prior snapshot and routes; a valid replacement changes
all snapshot state together. Recovery after rejection must work. Before first
activation return NO_ACTIVE. Missing node coverage returns NO_COVERAGE, distinct
from a known-node but disconnected/prohibited destination NO_ROUTE. Never snap
unreachable endpoints elsewhere, fabricate routes or fetch a fallback online.

MapA is ROUTE-002 and mapB JUNCTION-001, with independently declared route edge
sequences already frozen in their earlier analytical trials. Cases cover no map,
valid map, checksum, truncation, length, schema, format, provenance, malformed
XML, conditional tags, failed update, successful replacement, disconnected and
prohibited destination, unknown node, recovery, missing anchor and oversize.
Run actual import and route calculations in a Linux network namespace with no
default route in CI; local pure-Python results alone do not prove isolation.
No existing package activation wrapper is present: baseline UNAVAILABLE, not0/18.
SHA256 validates consistency against the trusted manifest, not authorship, map
freshness or legal truth. No signature/authentication, disk crash recovery,
concurrent update or Android/native offline readiness is established.

The integrated five external static directions APIs do not expose this DMN
package schema, transactional activation and exact node-ID coverage errors;
mark those interfaces UNSUPPORTED for this package contract, not failed offline
engines. Seven others lack permitted access or executable native/app harnesses:
NOT_RUN. Retain12 families plus DMN and per-case reasons. Only a complete judged
18-case cohort may receive10*passes/18; solo DMN conformance is not a competitor
quality ranking. Separate native package/network-isolated routing comparisons
remain unexecuted. Preserve UK17/0/23 ambiguity and promotion block.

OFFLINE-001 completed: freeze2d7885db99d3588d26cea3243ffa7c756c74b5b1;
implementation/fix1fb644870e0b5886ef63a9750f1ef1e6afa652a4, CI38859329753,
job116837785614.18/18 package cases and425 full tests pass. The actual parser/
router ran in a separate Linux network namespace with zero default routes:
12 store requests,9 core calculations. Failed updates preserve the current map;
missing coverage differs from no legal route. New wrapper is in-memory Python,
not Android/native offline readiness or authenticated/crash-safe disk installation.
First local scorer incorrectly assigned an offline score without isolation; its
function/hash/failure evidence is preserved. Fixed scoring keeps unisolated runs
unranked; negative control and isolated cohort pass. All12 reference families
remain visible with18 per-case unsupported/not-run reasons. Solo DMN10/10 is
package conformance, not superiority. See OFFLINE_001_RESULTS.md and offline001
before/first-scorer/after/scorecard JSON. Next bounded stage: frozen resource
measurements (setup separate from requests), then integration/native offline
proof. Keep UK17/0/23 ambiguity/promotion block and existing reference failures.

## RESOURCE-001 frozen resource characterization

Nine analytical cases cover8/16/32-square fabricated bidirectional grids,112m
edges at40km/h, diagonal/reverse/row paths. Independently declared Manhattan
edge counts, length and time must agree with every returned path; verify graph
continuity/access as well. Compare three DMN configurations (one family):
Dijkstra, raw-coordinate A* and prepared A*. Ten untraced timed requests after
one warmup per case, with raw samples/median/nearest-rank p95; setup is separate.
Measure memory in separate fresh processes so tracing cannot contaminate timing.
Report Python allocation peaks and Linux process peak RSS with explicit units/
scopes. Fresh worker per size/configuration/phase,40s each and180s total bound.
Bind graph/source/oracle hashes, host/Python/clock metadata and actual run SHA.
No speed or memory pass threshold is invented; correctness is required, resource
values are informational and do not establish Android or country-scale readiness.

The five static OSM directions adapters cannot consume the identical arbitrary
112m/40km/h RoadGraph with these exact costs; no common resource adapter exists.
Mark resource workloads NOT_RUN with this reason, never zero-quality or passed.
Other seven retain explicit app/native/access blockers. Retain all12 plus DMN
and per-case outcomes. No cross-family performance rank from different models,
hardware or in-process versus HTTP timings. DMN variant timings may be compared
within the recorded process/host protocol, but are not separate engine families.
UK coverage/promotion block and all prior reference failures remain unchanged.

RESOURCE-001 completed: freeze9dd63134411b9562519d7bd6cf5abfe1a4b19ea6;
implementation83f3830ee346ba428e4d78ad09e528f40e28ba95, CI38861398588/
job116844266276. Nine cases across three DMN configurations, separate timing/
memory phases and324 actual searches pass;429 full tests. A reproduced redundant
heuristic-work control failed223>64 before caching and passes64<=64 after a
per-request cache. Destination isolation/safety regressions pass. Memory rises
about50KB on largest diagonal queries. Latencies are informational: unchanged
Dijkstra also drifted, so do not attribute the whole timing difference to cache.
No native/phone or cross-family resource ranking; all12 references retain nine
per-case NOT_RUN reasons. See RESOURCE_001_RESULTS.md and resource001 before-local/
after-local/ci JSON with raw samples, graph/source hashes and environment.
The owner authorized remaining stages; continue bounded research integration
next, then native/device/long-duration and independent-truth work as actually
available. No adb/emulator/research Android project is available here; device
checks are UNAVAILABLE, never passed. Independent road/legal/GNSS truth and
broader same-workload reference adapters remain work. Preserve UK17/0/23 and
promotion block; do not declare the programme complete or universally superior.

## Owner steering: real maps, controlled GPS, applicable replacement engines

Future requested comparisons use real licensed public road maps and source-backed
facts; only injected GPS observations are simulated. Earlier invented-map checks
remain historical/internal controls and do not satisfy this real-map programme.
Target at least ten actually executed external engines per comparable cohort.
Unusable engines are excluded from active test/rank tables; record reasons in a
separate audit and build/find replacements rather than filling ranks with names.
Do not collapse five prior static executions into ten or claim generic feature
coverage. Test DMN independently against frozen evidence, then run other engines
separately on identical inputs; another engine never defines correctness.
See DMN_EXPANDED_VALIDATION.md and config/dmn-expanded-validation-programme.json
for detailed GPS/one-way/wrong-turn/junction/arrival/offline/resource/emulator
batches, truth/source rules, bounded million-variant expansion and improvement
register. New-registry generated-variant execution count is zero. New selector
requires a real-map source manifest and preserves historical frozen evidence.
Next bounded execution is REF-006: real Itinero source build and real pinned
Greater Manchester map, three preselected cases, finite route/5m endpoint contract.
No fabricated roads, legal/GNSS-truth verdict or ten-engine ranking is inferred.
Preserve the seven unresolved UK coverage cases and promotion block. Emulator
readiness is not asserted from location-injection scaffolding or host tests.

Owner asked how app adoption will be judged. DMN_APP_READINESS.md and
`python -m tools.app_readiness` now expose explicit evidence gates and current
NOT_READY_FOR_LIVE_NAVIGATION state. No aggregate score overrides UK coverage,
missing real-map/source-backed labels, incomplete ten-engine cohort, app
integration or unverified Android/native/lifecycle/performance evidence. DMN is
judged independently; references run separately against the same frozen oracle,
not as dependencies or hidden truth judges. Clear-fix output coverage and safe
bad-fix abstention are both required; do not reward an all-withheld engine.

REF-006 completed: actual Itinero source build and real Greater Manchester routes.
First setup38863763043 stopped before engine execution due to an XML-vs-PBF hash
scope error; correction preserved the exact prior XML fingerprint and acceptance.
Successful38864046561 at9c45c8417917f5d2eb51c1dbb68b0a0923fc7637 and confirmation
38864551063 atd38540e66aa175264e4534800a7d66a39ca47223 each pass3/3 finite route/
5m endpoint checks. Same request hash b4348997...; max endpoint error1.045m.
Itinero sourceb8a004.../package1.6.0-pre037/car uncontracted; SDK10.0.401, exact
resolved packages and assembly hashes retained. This is a sixth actual routing
family across prior scopes, not ten comparable real-map GPS engines. Simulated
signal-quality and independently labelled legality cases executed here: zero.
See REF_006_RESULTS.md and ref006 first-failure/real-map/confirmation JSON.
Next bounded stage: another executable applicable reference/replacement and
real-map source-backed GPS/one-way case bank; do not revert to invented roads
for the requested comparisons or silently count historical/mismatched cohorts.
Readiness reports now accompany normal CI; NOT_READY_FOR_LIVE_NAVIGATION and
all UK/app/native/source/cohort blockers remain explicit. No release or promotion.

### REAL-ONEWAY-001: real-map inventory failure retained (2026-10-16)

Pinned existing Manchester bbox has zero eligible one-way ways under the frozen
raw-tag selector. Diagnostic38866815919 executed zero routes and correctly failed
coverage; no score or comparative rank. See REAL_ONEWAY_001_RESULTS.md and
references/real-oneway-*.json for original setup failure, unchanged fingerprints,
empty inventory and source-access403 evidence. Select/freeze a suitable new real
area with authority evidence next; do not relabel this trial as passed. Ten-engine
cohort, independent law labels and UK seven-case promotion block remain open.

### REF-007: actual Routino real-map output probe and confirmation (2026-10-16)

Added an actual packaged CLI reference, motorcar/quickest, Routino3.4.1-1build1
amd64. Run38867638822 at6beb57c80cf0b45881dc71773fcf38919b494653 and pinned-package
confirmation38867883336 atde528931b5a509dc5b821953b2e70190c0cb32b1 each pass3/3
on the exact REF-006 public-map endpoint requests. Archive/XML/PBF/request hashes
verified; executable/configuration hashes identical. Max endpoint error2.254m
against5m, two returned vertices per route. These are endpoint/output probes,
not interior road law, GNSS stream, optimality or general navigation quality.
See REF_007_RESULTS.md and references/ref007-routino-*.json for all cases, versions,
licence/source/configuration hashes, raw bytes/commands, run SHAs and CI links.
Upstream package copyright: AGPL-3+; research CLI execution only, no app adoption.

Historical executed routing families now seven, not a shared ten-engine cohort.
Remaining candidates need actual applicable native execution; old unavailable
families remain audited without invented scores. Full453-test regressions pass;
no DMN logic change was justified by this output probe. UK17/0/23, seven unresolved
matches, missing independent one-way case bank and Android/integration/resource
readiness gaps remain blocking. Next bounded stage is another applicable reference
or independent source-backed real-map case acquisition; preserve existing failures.

### GPS-003 baseline and owner-confirmed review workflow (2026-10-16)

Real pinned map, three raw-selected segments of one way, eight streams each:
24streams/72updates. First attempt38869088303 stopped before matcher calls due to
tuple/list manifest comparison; corrected exact serialized-byte comparison with
regressions, without changing signals or acceptance. Actual baseline38869427281
atc6202e406450d6f9fbb8e01c7679193d92522358 fails16streams for required first-fix
availability (two positions repeated eight times);8streams pass. Counts39correct,
0confidentwrong,33withheld including12rejects; all24final clear observations pass.
Only DMN ran; no external rank/score is possible for this stream contract.
See GPS_003_RESULTS.md and references/gps003-*.json. Confidence policy unchanged.

Owner explicitly chose STOP AFTER BASELINE FOR REVIEW, then separately authorize
improvement/retest, and use currently available applicable engines rather than
waiting for ten. AGENTS.md records this standing rule. Before the next comparison,
freeze one shared real-map position/direction contract that actual external
matching engines support; do not substitute unmatched controller/routing APIs.
No automatic DMN tuning or next trial from this baseline is authorized yet.

### ROUTE-003 shared real-map route-output baseline (2026-10-16)

This owner-authorized baseline reuses the pinned Greater Manchester 260901
extract and the three endpoint pairs frozen before the REF-006 engine execution.
It measures complete route output, endpoint alignment, finite distance and ETA,
and calculation time for DMN, OSRM, Valhalla, GraphHopper, openrouteservice and
BRouter on identical inputs. The score is `10 * passed / 3`; incomplete cohorts
remain unranked and timing is reported separately because DMN in-process timing
and external warm loopback-request timing have different boundaries.

This stage does not claim current road-law truth, fastest-route superiority,
traffic performance, Android performance, or wrong-turn safety. OpenStreetMap
agreement is only source-map evidence. Itinero and Routino remain visible as not
run because their retained adapters do not expose the full shared distance, ETA
and timing contract. The baseline must stop for owner review before any DMN
change, retest, traffic stage or expanded route cohort.

Baseline runs38870925774 and38871562075 completed. DMN, OSRM, Valhalla,
GraphHopper, openrouteservice and BRouter each passed3/3 and tie at10/10 for the
narrow route-output contract. Median measured calculation/request times were
0.027190ms,1.075801ms,5.181559ms,8.694816ms,8.812027ms and7.272329ms
respectively; differing timing boundaries prevent a fair speed rank. Two BRouter
adapter/setup failures are retained. No verified DMN fault was found, no engine
tuning occurred, and the owner review gate is now active. See
ROUTE_003_RESULTS.md and references/route003-baseline-20261016.json.

### ROUTE-004 real-map one-way source-rule baseline (2026-10-16)

Owner authorized the next bounded baseline. It uses the pinned Greater Manchester
260901 archive and a central-Manchester extract large enough to contain eligible
one-way roads. Six ways are selected numerically from raw XML before any engine
runs; each contributes an allowed-direction and reverse-direction case. DMN plus
OSRM, Valhalla, GraphHopper, openrouteservice and BRouter receive the same exact
node endpoints. Required-route availability, endpoint alignment, finite distance
and ETA, and absence of direct traversal along the mapped forbidden direction are
judged. OSM tags remain source-map evidence rather than independent current road
law. Turn-restriction relations are outside this one-way-only cohort; unsupported
conditional objects and their dependants are removed for every engine rather than
interpreted. No UK17/0/23 ambiguity threshold or retained GPS case is changed.

DMN_RESULTS_OVERVIEW.md now consolidates retained per-case comparative rankings,
failures and actual measured milliseconds, clearly separating missing/unmatched
latency and historical synthetic controls. APP_VALIDATION_PROGRAMME.md extends
case/metric coverage to the whole app. Private app metadata/test-file discovery
was read-only; private source/inventory stays outside this public repository.
No app test execution, production code change, APK or adoption is claimed.


ROUTE-004 results published from the retained 38873690712 artifacts (no new tests):
[Full provisional six-engine source-map direction comparison](ROUTE_004_RESULTS.md)
with 12/12 passing for DMN, OSRM, Valhalla, GraphHopper,
openrouteservice and BRouter; no verified current UK road-law labels.
All six tie in this narrowly judged contract. Observed request milliseconds
are preserved but cannot be ranked across unlike HTTP and in-process scopes.
The separate issues register identifies no proven engine failure, possible
multi-vertex reverse-path detection gaps, absence of required edge coverage,
and a provisional York Street reverse detour-length disagreement. Original
engine results and frozen tests remain unchanged. **STOP for owner review**;
GPS-003 and seven UK unresolved matches remain open, without matcher tuning.


### GPS-003 diagnosis of the two first-fix ambiguities (2026-10-16)

Read-only review of frozen [GPS-003 case data](../references/gps003-real-map-20261016.json)
and the older [UK 40-case topology data](../references/gps001-uk-topology-20261015.json)
was published in [the detailed GPS-003 investigation](GPS_003_INVESTIGATION_20261016.md).
Sixteen failing streams are eight repetitions each of two unanchored first-fix
ambiguous coordinates on one Moss Lane way; no confident wrong road and all24
final clear recoveries remain as recorded. Seven distinct historical UK lost
matches involve backward-adjacent same-way fragments with recorded residuals;
these are not sixteen additional independent roads. The report provides a
separate issue register, source limitations and a diagnostic-only proposal.
Zero comparable external GPS-003 stream executions; no synthetic ranking.
No test run, matcher change, confidence adjustment or promotion. **STOP FOR REVIEW.**


### GPS-003 candidate-geometry diagnostic completed (2026-10-16)

[Exact two first-fix and seven historical UK candidate identities/geometry](GPS_003_CANDIDATE_DIAGNOSTIC_RESULTS.md)
were recorded in successful [bounded diagnostic run 38880782913](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38880782913).
All nine checks reproduced the original ambiguous decisions; both GPS-003
competition pairs and all seven older UK losses are same-way backward-adjacent
fragments of OSM way32113418, not independently verified roadway/guidance truth.
No matcher fix, score modification, competitor rank or new route test was made.
**STOP and request owner approval before improvements.**

### GPS-004 adjacent-fragment directed-progress safety baseline (2026-10-16)

Ten analytical synthetic controls were frozen before matcher tuning and executed
in successful run [38918971210](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38918971210)
at `ef4d454972685759064907210cb14d4818e61b77`. Authoritative DMN passes 9/10;
the isolated non-guiding adjacent-fragment research matcher passes 10/10. The
single authoritative failure is reverse-directed progress from a trusted reverse
fragment to its immediate same-way successor: DMN withholds rather than returning
a wrong road. Backward motion, prohibited continuation, a different-way competitor,
stationary/headingless/weak fixes and a sharp bend retain conservative outcomes.
No external integrated endpoint exposes the identical stateful shadow contract,
so all twelve families retain explicit unsupported/not-run reasons and no
competitive rank. No default matcher logic changed. See GPS_004_RESULTS.md and
references/gps004-baseline-20261016.json. UK17/0/23 and shadow22/0/18 remain
unchanged; promotion is blocked. **STOP for owner review before the proposed
reverse-fragment behavioral improvement and required fresh full retest.**


## Owner-approved forward GPS progress experiment — completed 16 October 2026

The new [verified multi-region engine-only GPS result](DMN_GPS_DIRECTED_PROGRESS_RESULTS_20261016.md) documents default UK40 17/40 versus research **30/40**, frozen GPS-003 8/24 versus 24/24, and **Salford/Stockport/Oldham** real OSM-road geometry cohorts of **13/36 default versus 27/36 research**, with 18 additional backward-motion controls and 0 confidently wrong generating-edge selections observed. These are PROVISIONAL map-source and analytical controls; original frozen tests and both matcher paths remain available. [GPS run](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38924328629), [engine units](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38924328641) 527/527, [GPS-004](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38924328663). Conditional/restriction-linked ways were explicitly excluded from the GPS-only scored subset, not treated as safe. No default promotion. STOP for review.
