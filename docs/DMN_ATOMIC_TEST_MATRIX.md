# DMN — atomic navigation testing matrix (15 October 2026)

**12 functional groups × 6 categories × 3 atomic checks = 72 categories and 216 check definitions.** Each check is currently **NOT RUN under this new framework**. This file defines what must be tested; it does not claim those navigation engines or sensors have been exercised. Full raw checks in [`config/dmn-atomic-test-matrix.json`](../config/dmn-atomic-test-matrix.json), verified by [`tools/dmn_atomic_coverage.py`](../tools/dmn_atomic_coverage.py).

Each `NAV-xxx` category maps to a proposed logical responsibility and one or more concrete test fixtures. Create narrow input/output contracts for the real implementation; `proposed/` is a logical boundary, **not a claim that these source directories already exist**. Reuse real UK public road geometry and independently verified legality, and use reproducible GPS/sensor faults on that geometry; don't call a synthetic sensor reading a field measurement.

**Results discipline:** pass, fail, unknown evidence, unsupported, not run and incomparable are distinct. Missing lane or legal data is **unknown**, not a failure or success. Show user one highest-first `/10` scoreboard **only after** the scoring methodology, independent truth and matched test cohorts are established; retain detailed per-check evidence. Do not rank against unavailable Google/Waze observations. Keep past research measurements separate and intact. Physical-device sensor truth is deferred; emulators cannot establish absolute GNSS/IMU field accuracy.

## Atomic check catalogue

### Road data and graph
_Logical module: `proposed/road-data`._

**NAV-001 — OSM provenance and freshness**: NAV-001-A: Reject missing map version or checksum; NAV-001-B: Compare dated public extracts reproducibly; NAV-001-C: Flag stale or conflicting road evidence.

**NAV-002 — Road geometry continuity**: NAV-002-A: Detect broken public-road segments; NAV-002-B: Detect spur and disconnected network errors; NAV-002-C: Check segment lengths against source geometry.

**NAV-003 — Junction graph topology**: NAV-003-A: Preserve every mapped road junction link; NAV-003-B: Detect false joins at crossing roads; NAV-003-C: Preserve correct incoming and outgoing connections.

**NAV-004 — Carriageway representation**: NAV-004-A: Distinguish two directions on dual roads; NAV-004-B: Preserve separate parallel carriageways; NAV-004-C: Reject virtual crossing between physically separate roads.

**NAV-005 — Motorcar access permissions**: NAV-005-A: Apply explicit motorcar access tags; NAV-005-B: Reject unverified private restricted links; NAV-005-C: Differentiate destination-permitted and through access.

**NAV-006 — Physical barriers**: NAV-006-A: Block confirmed bollards and bus traps; NAV-006-B: Mark unknown gates as uncertain; NAV-006-C: Retain a valid detour around confirmed barriers.

### Legal movements and restrictions
_Logical module: `proposed/legality`._

**NAV-007 — One-way direction**: NAV-007-A: Reject the wrong way on one-way streets; NAV-007-B: Handle reversed one-way ways; NAV-007-C: Check carriageway legality after a missed turn.

**NAV-008 — Node-based turn restrictions**: NAV-008-A: Reject confirmed no-left and no-right turns; NAV-008-B: Honor only-turn restrictions; NAV-008-C: Retain restrictions when route starts mid-junction.

**NAV-009 — Via-way and multi-link turns**: NAV-009-A: Check restrictions traversing multiple links; NAV-009-B: Avoid bypass through a split junction edge; NAV-009-C: Mark unsupported via-way rules unknown.

**NAV-010 — Legal U-turn decisions**: NAV-010-A: Allow independently confirmed lawful dead-end U-turn; NAV-010-B: Reject independently confirmed prohibited U-turn; NAV-010-C: Reroute without inventing permission when alternatives are absent.

**NAV-011 — Roundabout legal circulation**: NAV-011-A: Follow UK permitted direction; NAV-011-B: Reject prohibited entry and exit maneuvers; NAV-011-C: Check complex nested and spiral movement permissions.

**NAV-012 — Conditional vehicle and time rules**: NAV-012-A: Evaluate bus gates and school-street schedules; NAV-012-B: Check time-bound turns and closures; NAV-012-C: Flag uncertain vehicle, holiday or time exceptions.

### Route search and preferences
_Logical module: `proposed/routing`._

**NAV-013 — Shortest legal path**: NAV-013-A: Measure distance against independently shortest legal route; NAV-013-B: Exclude illegal shortcuts from shortest path; NAV-013-C: Test ties and disconnected destination.

**NAV-014 — Fastest legal path**: NAV-014-A: Compare estimated travel time against legal alternatives; NAV-014-B: Handle different road classes and speed assumptions; NAV-014-C: Never optimize time through illegal movements.

**NAV-015 — Preference and avoidance routing**: NAV-015-A: Check avoid-motorway option; NAV-015-B: Check toll, charge and restricted-zone avoidance; NAV-015-C: Explain and report when requested avoidance is impossible.

**NAV-016 — Alternative route generation**: NAV-016-A: Return materially distinct legal alternatives; NAV-016-B: Avoid duplicate geometry disguised as alternatives; NAV-016-C: Report no alternative when none exists.

**NAV-017 — Dynamic route costs and traffic**: NAV-017-A: Update costs without changing legal access; NAV-017-B: Compare fresh vs stale traffic decisions; NAV-017-C: Keep useful route when traffic information is offline.

**NAV-018 — Multi-stop routing and profiles**: NAV-018-A: Preserve waypoint order and arrival behavior; NAV-018-B: Check passenger-car restrictions and controls; NAV-018-C: Reroute while retaining remaining stops.

### Route geometry and progress
_Logical module: `proposed/geometry`._

**NAV-019 — Route line road adherence**: NAV-019-A: Keep route polyline on verified road centerline; NAV-019-B: Check route drift at complex roundabouts; NAV-019-C: Reject off-network turn-point coordinates.

**NAV-020 — Curved and spiral connectors**: NAV-020-A: Follow mapped roundabout arcs; NAV-020-B: Preserve curved slip-road alignments; NAV-020-C: Avoid cutting corners between legal road links.

**NAV-021 — Grade-separated road geometry**: NAV-021-A: Separate bridges from underpasses; NAV-021-B: Reject shortcuts across different levels; NAV-021-C: Keep approach and exit line on correct level.

**NAV-022 — Junction transition geometry**: NAV-022-A: Place turn anchors at actual connection; NAV-022-B: Do not create nonexistent lane connectors; NAV-022-C: Maintain path continuity through junction.

**NAV-023 — Progress along route**: NAV-023-A: Track distance remaining monotonically when on course; NAV-023-B: Avoid progress jumping to adjacent parallel road; NAV-023-C: Recalculate distance after permitted detour.

**NAV-024 — Route versus displayed map version**: NAV-024-A: Detect routing-versus-renderer map mismatch; NAV-024-B: Keep instructions aligned with route geometry; NAV-024-C: Fail visibly when map lacks required geometry.

### GPS signals and sensors
_Logical module: `proposed/positioning`._

**NAV-025 — Raw GNSS validity**: NAV-025-A: Reject invalid latitude, longitude and fix values; NAV-025-B: Record GNSS quality and location uncertainty; NAV-025-C: Handle intermittent satellite visibility.

**NAV-026 — Heading and orientation**: NAV-026-A: Compare motion heading with road travel direction; NAV-026-B: Handle compass reversal and magnetic interference; NAV-026-C: Avoid unstable headings while stopped.

**NAV-027 — Movement speed measurement**: NAV-027-A: Check GNSS speed against replay truth; NAV-027-B: Reject extreme speed spikes; NAV-027-C: Handle near-zero and stop-start speeds.

**NAV-028 — IMU dead reckoning**: NAV-028-A: Propagate position during short GNSS loss; NAV-028-B: Bound drift without map evidence; NAV-028-C: Reject false motion from sensor noise.

**NAV-029 — Sensor fusion and source selection**: NAV-029-A: Compare GNSS-only versus valid fused output; NAV-029-B: Handle disagreement between GNSS and IMU; NAV-029-C: Switch sensor sources without location jumps.

**NAV-030 — Fix timestamps and ordering**: NAV-030-A: Drop stale and out-of-order fixes; NAV-030-B: Handle duplicate timestamps; NAV-030-C: Recover cleanly after a sudden time discontinuity.

### Road matching and position confidence
_Logical module: `proposed/matching`._

**NAV-031 — Parallel road selection**: NAV-031-A: Distinguish frontage road from main road; NAV-031-B: Remain on correct close parallel road; NAV-031-C: Express unknown rather than confidently choosing wrong link.

**NAV-032 — Dual carriageway side**: NAV-032-A: Choose correct side of divided road; NAV-032-B: Stay on side through bends; NAV-032-C: Reject across-median snap without legal connection.

**NAV-033 — Slip road and service road matching**: NAV-033-A: Switch correctly onto true slip road; NAV-033-B: Do not snap service road traffic to motorway; NAV-033-C: Keep vehicle on correct merge path.

**NAV-034 — Bridges and stacked roads**: NAV-034-A: Disambiguate bridge versus road underneath; NAV-034-B: Use trajectory to retain level context; NAV-034-C: Avoid false motorway position beneath flyover.

**NAV-035 — Roundabout position matching**: NAV-035-A: Track actual circular path without shortcut; NAV-035-B: Resolve close entry and exit links; NAV-035-C: Retain exit count while GPS jitters.

**NAV-036 — Stationary urban and indoor starts**: NAV-036-A: Stay fixed at traffic lights during GPS scatter; NAV-036-B: Handle urban canyon multipath; NAV-036-C: Initialize from car park or indoor weak fix conservatively.

### Rerouting and signal recovery
_Logical module: `proposed/recovery`._

**NAV-037 — Off-route detection**: NAV-037-A: Detect genuine missed turns; NAV-037-B: Ignore single noisy false deviations; NAV-037-C: Time off-route detection separately from computation.

**NAV-038 — Single wrong-turn recovery**: NAV-038-A: Generate new legal route after wrong exit; NAV-038-B: Avoid old instruction replay; NAV-038-C: Check reroute from true current incoming road.

**NAV-039 — Repeated missed turns**: NAV-039-A: Reroute after rapid successive wrong turns; NAV-039-B: Cancel obsolete queued reroutes; NAV-039-C: Maintain legal state and arrival target.

**NAV-040 — Tunnel and long GPS outages**: NAV-040-A: Continue conservatively in tunnel; NAV-040-B: Stop certainty from increasing during long loss; NAV-040-C: Reacquire correct road after signal returns.

**NAV-041 — Rejoining an existing route**: NAV-041-A: Rejoin when legal and genuinely beneficial; NAV-041-B: Avoid oscillating between alternative paths; NAV-041-C: Do not recommend impossible backtracking.

**NAV-042 — No-route and blocked-road fallback**: NAV-042-A: Report truly unreachable destination; NAV-042-B: Avoid illegal detour when blocked; NAV-042-C: Recover once road graph or evidence returns.

### Speed limits, traffic and ETA
_Logical module: `proposed/speed`._

**NAV-043 — Signed speed limit by section**: NAV-043-A: Compare limit per verified road section; NAV-043-B: Distinguish posted limit from routing speed estimate; NAV-043-C: Mark missing or contradictory limit unknown.

**NAV-044 — Variable speed and conditional limits**: NAV-044-A: Handle motorway variable limit inputs; NAV-044-B: Handle temporary limits only when supported; NAV-044-C: Do not invent a limit from average speed.

**NAV-045 — Live driving speed display**: NAV-045-A: Update speed at realistic cadence; NAV-045-B: Filter sudden noisy speed spikes; NAV-045-C: Keep units consistent in mph and km/h.

**NAV-046 — Overspeed warning behavior**: NAV-046-A: Warn only against supported applicable limit; NAV-046-B: Apply tested hysteresis around threshold; NAV-046-C: Suppress warning with unknown legal limit.

**NAV-047 — ETA and distance-to-arrival**: NAV-047-A: Compare ETA with replay arrival time; NAV-047-B: Recompute ETA after wrong turn and traffic; NAV-047-C: Keep ETA stable when stopped.

**NAV-048 — Traffic and delay quality**: NAV-048-A: Check time-dependent travel cost input; NAV-048-B: Separate offline baseline from live traffic; NAV-048-C: Avoid false congestion changes from GPS noise.

### Turn, roundabout and voice guidance
_Logical module: `proposed/guidance`._

**NAV-049 — Turn direction and maneuver labeling**: NAV-049-A: Identify left right straight and keep maneuvers; NAV-049-B: Detect complex staggered junction wording; NAV-049-C: Avoid suggesting nonexistent maneuver.

**NAV-050 — Advance instruction timing**: NAV-050-A: Check warnings at varied driving speeds; NAV-050-B: Do not warn after passing a turn; NAV-050-C: Scale approach notice to complex junctions.

**NAV-051 — At-turn and post-turn instructions**: NAV-051-A: Confirm instruction at actual maneuver; NAV-051-B: Clear stale prompt immediately after turn; NAV-051-C: Prepare next instruction without repetition.

**NAV-052 — Roundabout exits and wording**: NAV-052-A: Count traversed usable roundabout exits correctly; NAV-052-B: Check mini and spiral roundabout wording; NAV-052-C: Avoid nonexistent exit number.

**NAV-053 — Uncertainty-aware instructions**: NAV-053-A: Withhold unsupported exit and lane precision; NAV-053-B: Issue simpler supported direction instead; NAV-053-C: Never present low-confidence guidance as fact.

**NAV-054 — Voice and Bluetooth audio**: NAV-054-A: Duck music rather than cut it off; NAV-054-B: Restore music without overlapping prompts; NAV-054-C: Prevent duplicate or truncated spoken prompts.

### Lane-level guidance
_Logical module: `proposed/lanes`._

**NAV-055 — Lane count detection**: NAV-055-A: Match mapped count against independent lane evidence; NAV-055-B: Handle lane changes across a junction; NAV-055-C: Report unknown when lane-count evidence absent.

**NAV-056 — Lane arrows and turn legality**: NAV-056-A: Check straight left and right arrow meaning; NAV-056-B: Do not recommend lane with illegal movement; NAV-056-C: Support lane-specific permitted exits.

**NAV-057 — Combined and shared lanes**: NAV-057-A: Represent lanes that go straight and turn; NAV-057-B: Avoid reducing combined arrow to one direction; NAV-057-C: Check shared turns across multiple lanes.

**NAV-058 — Recommended lane choice**: NAV-058-A: Choose lane appropriate for upcoming maneuver; NAV-058-B: Handle approach lane changes at correct distance; NAV-058-C: Avoid unnecessary weaving before exits.

**NAV-059 — Special and restricted lanes**: NAV-059-A: Exclude bus-only lane when not permitted; NAV-059-B: Respect conditional lane restrictions; NAV-059-C: Distinguish hard shoulder from running lane.

**NAV-060 — Lane evidence gaps**: NAV-060-A: Classify missing lane tags as unknown not failure; NAV-060-B: Fail verifiably incorrect lane instruction; NAV-060-C: Use direction-only guidance when precise lane unknown.

### Destination search and arrival
_Logical module: `proposed/arrival`._

**NAV-061 — Address and destination resolution**: NAV-061-A: Select intended property not neighboring postcode center; NAV-061-B: Handle multiple buildings sharing address; NAV-061-C: Flag uncertain search match before navigation.

**NAV-062 — Vehicle-accessible entrance**: NAV-062-A: Target drivable entrance not rear pedestrian door; NAV-062-B: Reject unreachable private path; NAV-062-C: Mark absent vehicle entrance evidence unknown.

**NAV-063 — Correct side and approach**: NAV-063-A: Approach destination from legal carriageway side; NAV-063-B: Avoid wrong-side dual carriageway arrival; NAV-063-C: Check permitted final turn into approach.

**NAV-064 — Arrival trigger confidence**: NAV-064-A: Do not finish on adjacent street; NAV-064-B: Require appropriate progress and distance; NAV-064-C: Avoid premature or repeated arrival alerts.

**NAV-065 — Overshoot and missed entrance**: NAV-065-A: Continue navigation after overshoot; NAV-065-B: Calculate legal return maneuver; NAV-065-C: Recognize corrected final arrival.

**NAV-066 — Stop and waypoint completion**: NAV-066-A: Complete stops in planned sequence; NAV-066-B: Do not skip stop due to GPS jitter; NAV-066-C: Resume final destination after intermediate stop.

### Offline operation, efficiency and resilience
_Logical module: `proposed/runtime`._

**NAV-067 — Fully disconnected navigation**: NAV-067-A: Compute valid offline route in airplane mode; NAV-067-B: Reroute offline during signal loss; NAV-067-C: Issue usable offline instructions to arrival.

**NAV-068 — Map download and update integrity**: NAV-068-A: Verify offline dataset checksum; NAV-068-B: Rollback incomplete map update; NAV-068-C: Reject graph/map snapshot mismatch.

**NAV-069 — Regional edges and missing data**: NAV-069-A: Route through downloaded region seams; NAV-069-B: Warn before offline map boundary; NAV-069-C: Do not invent roads outside loaded graph.

**NAV-070 — Startup and journey persistence**: NAV-070-A: Start navigation without network; NAV-070-B: Restore route after process restart; NAV-070-C: Recover state after app background and wake.

**NAV-071 — Performance, memory and battery**: NAV-071-A: Measure route compute warm and cold p50 p95; NAV-071-B: Measure reroute response and peak memory; NAV-071-C: Measure CPU and battery proxy on identical host.

**NAV-072 — Crashes, concurrency and rollback**: NAV-072-A: Handle corrupt map and malformed fixes without crash; NAV-072-B: Check overlapping route requests and cancellation; NAV-072-C: Keep baseline engine rollback available in isolated app integration.

## First executable stage

Run the new **catalogue contract tests** in normal low-cost GitHub unit CI; these validate completeness and falsification resistance only, not real vehicle behavior. In separate engine test workflows, attach actual public map hashes, engine builds, replay inputs, ground-truth sources, latencies, pass/fail/unknown and executable artifacts to these IDs. Start with routing and speed tests where code exists; do not manufacture GPS/voice/lane results where an implementation or oracle is absent. Expand to offline/emulator runs after isolated component measurements. No changes to DriveMate production and no APK release.

## Relationship to the existing modular inventory

The existing [59 proposed subsystem contracts and 236 granular check names](../config/dmn_navigation_modules.json) are a **separate implementation-oriented inventory**, summarized under 14 presentation groups. This **72-category/216-assertion matrix** adds a problem-focused classification for independently reproducing faults. These are overlapping descriptions of the same navigation work, **not 452 distinct executed or additional tests**, and the check counts must NOT be added or used in scoring. A follow-up evidence crosswalk must link overlapping check identifiers, remove duplicate execution, and ensure each distinct behavior has one canonical result before issuing numeric ranks. Neither inventory is proof that GPS, lanes, voice or physical sensors have passed.

## Adaptive growth rule (owner approval 15 October 2026)

**These 72 categories / 216 checks are the baseline, not a maximum.** Whenever real-UK route tests, GPS/speed/positioning replays, CI, engine comparisons or full journeys highlight a new behavior, uncovered failure, disagreement or evidence gap, follow the [adaptive study loop](DMN_ADAPTIVE_TESTING.md). Create a provenance-backed regression proposal; verify it, then implement and rerun it with neighboring, held-out and full-journey cases. If none of these 72 categories fits, add another category and isolated component contract; **never fabricate PASS/FAIL** for absent map, lane or legality evidence. Existing proposed checks overlap the 59-module/236-check inventory; do not sum these counts or create duplicate result IDs.
