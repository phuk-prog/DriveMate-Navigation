# JUNCTION-001: synthetic junction and roundabout semantics

DMN now has an isolated principal-maneuver generator. It passes the five frozen
cases: left90°, right90°, roundabout exits1,2,3. There was no generator at the
inspected baseline184f7e795526eebbb3897d6a6fab1e382445f8f1; this is new capability,
not an invented improvement from0/5. Expected maneuvers were frozen before code.

These are analytical expectations on an invented directed road topology, **not
independently surveyed road or legal truth**. Geographic bearings determine the
two turns. Declared circulation and accessible outgoing spokes determine exit
numbers; neither competitor consensus nor DMN output defines the oracle. The
incoming-only feeder and prohibited motor-vehicle spur cannot count as exits.
Principal semantics are judged separately from wording, voice, timing and lanes.

## Comparable five-case ranking

Score=`10 * passed / 5`. All geometry and principal-maneuver checks must pass.
Equal scores share rank; the next rank reflects all tied entries above it.

| Rank | Engine | Left | Right | Exit1 | Exit2 | Exit3 | Passes | /10 |
|---|---|---|---|---|---|---|---|---|
|1|DMN|PASS|PASS|PASS|PASS|PASS|5/5|10|
|1|GraphHopper|PASS|PASS|PASS|PASS|PASS|5/5|10|
|1|OSRM|PASS|PASS|PASS|PASS|PASS|5/5|10|
|1|openrouteservice|PASS|PASS|PASS|PASS|PASS|5/5|10|
|5|BRouter|PASS|FAIL|PASS|PASS|PASS|4/5|8|
|6|Valhalla|PASS|PASS|FAIL|PASS|FAIL|3/5|6|

This is a scoped contract score, not overall navigation superiority. Seven other
external families remain UNRANKED/NOT_RUN on every case: OsmAnd and Organic Maps
need app/native maneuver replay harnesses; HERE, Mapbox, TomTom and Google Maps
lack configured permitted access and the same invented-map interface; Waze has
no established permitted automated replay interface. They are not zero-quality
engines. All thirteen systems, five case verdicts and reasons are retained in
[junction001-scorecard-20261016.json](../references/junction001-scorecard-20261016.json).

## Failures and confirmation

Valhalla3.9.1 reports roundabout_exit_count=2 and explicitly says “take the2nd
exit” for both J001-E1 and J001-E3. Expected counts are1 and3. Every geometry
check passes on both paths; the incorrect count is in the raw provider response,
not introduced by normalizing text. J001-E2 correctly reports2. A fresh pinned
build/retest reproduced all five verdicts. The internal cause remains unproven;
we have not changed Valhalla or treated this as a routing-legality failure.

BRouter1.7.10 returns J001-R only from(1,0.999) to(1,1), instead of reaching the
requested destination(0.999,1). It terminates111.195m short, returns111.178m versus
the oracle222.373m route length, and emits no voicehint. Endpoint, length and
required-turn checks fail; on-path and forward-progress checks pass. The fresh
build/retest retains exact coordinates and repeats this result. This establishes
endpoint relocation/truncation under the tested configuration, not a standalone
turn-sign classifier failure. The other four cases pass. No acceptance radius,
case, map or oracle was changed to accommodate either engine.

Competitors already provide structured turn/roundabout instructions, exposing
DMN's missing capability. DMN now matches the four best tested systems on this
small cohort. There is no observed deficit in its five outputs requiring a
policy relaxation. Its nine additional analytical controls also pass: partial
ring start/end, disconnected route, prohibited route edge, prohibited-turn and
unknown-access spoke exclusion, unknown metadata, opposite circulation and a
repeated ring junction. These are engineering counterexamples, not blind holdouts.
A route ending/starting inside a roundabout is rejected rather than assigned a
made-up exit count. Multi-carriageway/lane grouping is not implemented.

## Reproduce and evidence

Fixture/oracle freeze:6761d694d9eeabd1e3df648f77f9c6c5012b1a12.

- Map SHA256:`8b9d409865dd0b272456c2b99575c8dd29d3459602db7016377889b9b00ab465`.
- Oracle SHA256:`dd8e3c879b81c5199edf6ff95289638da19e535112b3694851b289ac27752f53`.
- Initial actual five-reference run:[38853990046](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38853990046), source`90f51f43c90d59b260fc88a873843ff4deb7c478`;397 tests. All five heavyweight reference builds executed sequentially.
- Targeted Valhalla/BRouter confirmation:[38854474267](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38854474267), source`2996b127760764131530596e156c5a3e58ea0930`;405 tests. DMN5/5 rerun with all nine additional safety controls. No algorithm change between runs; capture now retains returned points and accurately labels the DMN component.
- [Baseline capability](../references/junction001-before-20261016.json), [initial execution/raw maneuvers](../references/junction001-executed-20261016.json), [confirmation/raw coordinates](../references/junction001-retest-20261016.json). Each execution records job IDs, versions and map/oracle hashes. BRouter JAR, profile, lookups and prepared-segment hashes are included.

Configurations are in `.github/workflows/junction001-references.yml` at each
source SHA: OSRM5.27.1 car.lua/MLD with pinned image digest; Valhalla3.9.1 auto,
pinned digest, polyline6, no admin/timezone/elevation build; GraphHopper11.1
published-checksummed JAR, Java25, car/CH; ORS10.1.0 SHA256-verified official JAR,
Java25, driving-car/fastest, noCH/LM/core; BRouter1.7.10 SHA256-verified release,
Java17, car-vario defaults, timode3, actual map builder without elevation.
Tiny-network pruning is disabled. All directions requests enable instructions
and complete geometry. No hosted APIs, credentials or paid calls are used.
Geometry requires2m endpoints/on-path,5m length and0.5m forward-progress tolerance;
interior segment samples reject corner cutting. Missing maneuvers fail required
output; malformed/execution errors are UNRESOLVED and cannot receive a score.

Normal research CI now gates the DMN five-case batch, all405 unit tests and
existing GPS/routing/rerouting safety tests. Local compile, privacy guard and
diff whitespace checks pass. `scripts/unified_preflight.py` is absent/unavailable,
not counted as passed. The guidance code is an isolated research module and
requires trusted roundabout metadata supplied explicitly; no Android routing,
GPS progress, narration, voice scheduling or lane integration is established.

Next bounded stage: freeze arrival safeguards (exact destination versus passing
nearby, stale/weak/off-route fixes, overshoot and recovery), then offline
reliability/resources and integration. Do not rerun the unchanged heavy junction
cohort automatically. The UK40-case coverage remains17 correct/0 confident wrong/
23 withheld, with seven lost cases unresolved; **promotion remains blocked**.
