# Owner-directed real-map validation programme

The owner clarified the requirement: future comparison cases use real licensed
public road maps and source-backed road facts. Only injected GPS observations
are simulated. Invented road grids/loops remain historical/internal regression
controls; their previous scores do not satisfy this requested real-map programme.
Do not erase, relabel or extrapolate those earlier results.

## Run DMN independently, then compare equivalent isolated runs

DMN is tested on its own against a frozen expected result. Another engine never
decides that expected result. For a real one-way street, verify the real map's
one-way information and, for a real-world legality verdict, the dated responsible
authority's traffic order/signage evidence. Obeying supplied map tags is a useful
map-contract check, but does not prove the map reflects current physical law.

The identical real-map snapshot, profile/time, endpoints, GPS observation bytes,
timestamps and tolerances go to each applicable engine. Run each heavyweight
engine separately and sequentially, with its own process/map state. Cold/warm
preparation/request timings are distinct. Compare speed on equivalent hardware,
workload and transport; do not rank in-process Python against an unrelated HTTP
measurement. Record ambient variation, resources, errors and the actual run SHA.
No competitor service is a dependency of DMN routing or its correctness oracle.

## At least ten actually runnable external references

The objective is DMN plus at least ten distinct external families per applicable
competitive cohort. Retained evidence initially established five external static
routing/maneuver executions: OSRM, Valhalla, GraphHopper, ORS and BRouter. REF-006
has additionally executed Itinero and REF-007 has executed Routino on the real pinned Greater Manchester map. These seven
are not ten and do not constitute a shared real-map/GPS-quality cohort. CH/MLD and DMN search variants
never inflate family count. No claim to an industry “top ten” is supported by
adding ten names or generically ranking apps with different responsibilities.

The initial expansion path adds executable adapters for OsmAnd, Organic Maps,
Itinero, libosmscout and Routino, each subject to exact version/dependency/licence
review and an actual relevant smoke execution. These are candidates, not claimed
executions. Primary Itinero README/LICENSE and libosmscout README/LICENSE were
inspected through public GitHub. Itinero's pinned source is Apache2.0 and documents
OSM import, routing and instructions; libosmscout documents C++ offline routing
and LGPL terms. Routino's primary website could not be retrieved here, so its
licence/build capability is not marked verified. Replacement engines must be
found when an adapter cannot legitimately execute the target category. Candidate
approval is not a mocked pass or proof that every feature is implemented.

**Only applicable, actually executed engines appear in the active test/ranking.**
Unsupported/unavailable engines are excluded from that table, with reasons kept
in a separate audit. This follows the owner's later instruction and does not
retroactively alter older frozen scorecards that listed all families. Original
HERE/Mapbox/TomTom/Google/Waze availability records remain in the audit; no paid,
credentialed or unsupported access is authorized. A category short of ten remains
explicitly underfilled. Continue adapter work or report a concrete blocker; never
substitute a shared DMN policy wrapper and claim it tests ten native controllers.
DMN-only regression work can continue while the comparative cohort is built.

`benchmarks.applicable_cohort.rank_applicable` implements active-only ranking,
separate exclusions, exact cohort/hash matching, no invented engine execution,
and a minimum-ten flag. Future comparison calls require a real-map source
manifest; an invented-map manifest is rejected. Explicit historical mode can
reformat retained results without claiming a new run. The readiness auditor
checks cited actual reports instead of trusting engine names or execution claims.

## Logical batches and exact checks

| Batch | Controlled GPS/conditions | What is checked |
|---|---|---|
|GPS quality|Clear fixes, noisy/low accuracy, stationary heading, intermittent samples, stale/future/order errors, gaps and jumps|Road/direction where justified; safe withholding; wrong-carriageway/bridge-level claims; trusted-state integrity; recovery time/distance|
|Route legality|Real one-way streets, prohibited turns, access and dated closures/conditional rules|Every edge/turn against frozen profile/time evidence; endpoint fidelity; legal recovery; missing coverage versus no-route|
|Wrong turn/reroute|Actual missed maneuver versus GPS drift, repeated deviations and delayed results|Trigger corroboration; detection delay separately from calculation; no illegal U-turn, oscillation or stale callback installation|
|Junction guidance|Real forks, merges, grade separation, motorway exits and roundabouts|Correct outgoing road, maneuver, exit count, geometry indices and sequence; no unsupported lane claims|
|Arrival|Nearby parallel road, wrong carriageway, early proximity, overshoot, weak fixes and destination changes|Progress plus proximity/freshness; no false arrival; single event per context; recovery|
|Offline/recovery|Network loss, missing/corrupt/partial map, interrupted replacement and reconnect|Actual local routing; retain known-good snapshot; clear error classes; no silent online fallback; freshness limits|
|Resources/long runs|Cold/warm short/long routes, repeated reroutes, sustained replay and wall-clock soaks|Correctness throughout; raw latency distributions; setup separated; CPU/RSS/allocation/storage growth; errors and leaks|
|Android emulator|GPS injection, coarse/precise permissions, background/screen-off, stop/restart and loss/recovery|Actual integrated DMN component, lifecycle and stale-guidance suppression; not merely successful location injection|

For GPS simulation freeze nominal locations on the real map and the exact error/
accuracy/speed/heading/time/gap schedule before observing results. Every engine
receives the same bytes/units. Cover plausible speeds and deliberate impossible
jumps; a noisy measurement must not silently become a confident wrong road.
Do not claim to emulate physical RF/multipath or battery/thermal behavior solely
by setting an accuracy field. Android emulator location injection is simulated
GNSS too, not a surveyed phone-reception measurement.

Requested emulator tests may need private ephemeral debug/test APKs; they are
separate from a release, signing change or standalone replacement DMN app.
Actual engine integration and a usable emulator/harness are prerequisites. None
exists in this workspace yet: adb/emulator and research Android project were
absent at inspection. No emulator, physical phone, release APK or production
repository modification is claimed by this programme update. The existing
DriveMate repository may be inspected if needed; do not publish private source.

## Evidence from real places

A case must bind source URL, licence, retrieval/document hash, map snapshot/hash,
jurisdiction, publication/effective/expiry dates, vehicle/time exceptions, expected
outcome and tolerances before tuning. Preserve disagreements as unresolved.
National Highways travel/closure information is a candidate for covered dated
roadworks/closures, not a universal turn-law or GNSS-accuracy oracle. Responsible
local authorities' traffic orders and appropriately licensed independent geometry
may supply other facts; each actual record must be obtained and checked first.

Free direct retrieval of National Highways travel updates, OS Open Roads and
Routino's website was blocked by this environment's proxy with HTTP403. No source
facts, current legal restrictions, datasets or licences were inferred from those
failed reads, and no paid retrieval API was used. Source URLs remain candidates
in the registry, not verified road cases. A later bounded public-source acquisition
may use permitted access; do not evade access controls or scrape personal traces.

REF-006 now stages a real-map Itinero executable probe. It uses the pinned existing
Geofabrik Greater Manchester260901 source/hash, the established public bbox and
three deterministic public-node pairs, selected before Itinero executes. Require
complete finite geometry and both exact endpoints within5m; retain every failure.
This demonstrates routing interface readiness only, not a GPS stream test, dated
road legality or ten-engine superiority. The case-selection manifest is frozen
in its run artifact before calculation; never discard a case after seeing output.
The full road source is real; no invented road layout is used in this probe.

## Scale, ranking and improvement loop

Start with small explicit source-backed cases. Run all applicable engines and DMN
baseline before tuning. Diagnose an actual DMN deficit, reproduce it, fix it,
then rerun changed cases, full safety regressions and additional controls.
Track every reproduced fault/capability gap in the improvement register below.

After the harness/oracle is proven, expand GPS variations with recorded seeds
and bounded resumable shards toward millions. The current new-revision execution
count is **zero**, not a million. Separate unique real-world base cases, generated
variants, repeated measurements, engine executions and independently verified road
facts. A million noisy variants of a few roads are not a million independent road
validations. Use explicit time/memory/request limits, failure retention, checkpoints
and stop conditions; no unbounded expensive experiment is authorized.

Score each complete genuinely comparable cohort:`10*passed/frozen judged cases`,
rank highest to lowest and share ties. Include exact expected/actual/error reason,
source/version/configuration, map/oracle hashes, run SHA/CI URL, runtime units,
coverage, confident wrong-road/illegal-turn/false-arrival counts and recovery.
Unknown evidence or execution errors are unresolved/unranked, never invented
passes. Missing required output from an executed supported contract is a failure.
Critical safety failures block promotion independently of an aggregate score.
No overall winner is created by mixing unmatched cohorts or hiding missing tests.

## Evidence-backed improvement register

| Item | Evidence/classification | Next required proof |
|---|---|---|
|Recover UK coverage safely|Verified unresolved regression:24/0/16 to17/0/23; seven backward-adjacent alternatives; GPS_001_RESULTS.md|Independent evidence or a safety-preserving resolution; no forced confidence|
|Reach ten applicable runnable references|Capability gap:seven static routing families across historical scopes, no common real-map ten-cohort|Build/execute remaining applicable replacements per category; exact profiles and snapshots|
|Real-map integrated GPS/progress pipeline|Integration gap:isolated controllers consume supplied assessments|Replay real-road geometry with frozen simulated signals through matching, progress, rerouting, guidance and arrival together|
|Independent real-road legality labels|Evidence gap:map tags/consensus alone insufficient|Obtain/check dated authority records and their scope before assigning verdicts|
|Native/offline/device integration and long runs|Unverified platform work; host Python package proofs are limited|Actual integrated emulator/native run, lifecycle/offline/recovery and sustained resource evidence|
|A* work/memory tradeoff|Verified cache223→64 calls; about50KB additional peak allocation; RESOURCE_001_RESULTS.md|Real-map resource retest; no blanket A* switch based on invented grids|
|Reference failure examples|BRouter endpoint truncation and Valhalla wrong exit counts on historical invented maps|Preserve source results; do not label them DMN defects or assume they recur on real roads|

Historical checks remain auditable. This programme is not complete, and no map/
road/device readiness has been established by a schema validator. Preserve the
UK promotion block and all failing/ambiguous evidence while continuing the
owner-authorized work in bounded executable stages.

## Executed REF-006 result and readiness view

The first setup attempt38863763043 at626cee45397a77a88905174e7fa39d21c42f1b98
stopped before engine execution: the known XML-subset fingerprint was mistakenly
checked against the full PBF archive. Root cause is recorded in
references/ref006-first-setup-failure-20261016.json; no case was passed or scored.
The correct XML scope was verified from public_temporal_gps.py's sha256(raw XML).

Corrected run38864046561 at9c45c8417917f5d2eb51c1dbb68b0a0923fc7637 built actual
Itinero source b8a004a831d353565572c7ba41b5a40c29d79360 (package metadata1.6.0-pre037,
assembly1.0.0.0), car/uncontracted. All three real-map output/endpoint cases pass,
maximum endpoint error1.045m. Map XML exactly matches prior b3a883... source; the
full archive's distinct SHA256 is b7188b22501b878fddba6e06a90bb44ce6c2d721333e0ca57e10a1a82b568807.
At the REF-006 stage, the six executed routing families included historical scopes and are not a shared
ten-engine cohort or a market-top-ten claim. No low-signal/streamed-GPS or
independently verified one-way legality verdict was inferred from this probe.
Full cases, map/oracle/source/assembly hashes and CI are in
references/ref006-itinero-real-map-20261016.json. A bounded confirmation pins
both archive and XML fingerprints and captures SDK/resolved dependency metadata.

DMN_APP_READINESS.md and tools.app_readiness show why DMN is not ready to replace
app navigation. The readiness inventory records each missing/blocked gate and
has no aggregate score that could hide a critical fault. Current live adoption
is blocked; reversible prototype research is separate from release readiness.
