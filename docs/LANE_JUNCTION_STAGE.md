# Static lane evidence and junction guidance — verified local stage

Original DriveMate Navigation software, separate from the Android application.
No GitHub write, APK build or real-road test was performed.

## Implemented contract

- `PreparedNavigation.junctions(route, ...)` describes route transitions using
  supplied geographic endpoints, validates road/turn legality and can return
  explicit lane indications or declared direct lane connections.
- `journey.junctions()` integrates partial-road origin/destination costs and the
  current accepted snapshot. It clears passed guidance, reuses immutable results
  for repeated requests and does not launch additional route jobs. Roundabout
  context and junction guidance share the same legality/clock path preparation.
- Static `turn:lanes` values are parsed left-to-right, with `|` between lanes and
  `;` between indications. Supported tokens cover through, ordinary/slight/sharp
  left/right, reverse and merge markings. Explicit direction suffixes determine
  forward/backward data without mirroring lane order or guessing a two-way split.
- A declared lane count must agree with its indication vector. Counts are capped
  at 32 and hint/connection strings at 2,048 characters. Blank, unknown, inconsistent
  or unsupported values degrade optional guidance rather than road availability.
- Lane data is parsed once per way/direction. Indications are usable only at the
  direction's way endpoint; interior segments retain counts but not a guessed
  end-of-way turn marking. This conservative prototype may omit valid intermediate
  markings; explicit connectivity can supply them where justified.
- Reverse one-way generic indication order is conservatively unverified unless an
  explicit backward indication key exists. Unsupported vehicle-specific,
  conditional or lane-change annotations are not treated as known vehicle lanes.
- Simple single-via-node connectivity relations are resolved to unique directed
  roads, with validated declared directional lane bounds. Parenthesised targets
  retain their lane-change-required meaning. Only direct connections become lane
  candidates; no lane change is invented. Duplicate/conflicting/out-of-bounds or
  ambiguous/unsupported relations retain route-level guidance without lane advice.
- Explicit connectivity overrides broad painted-direction matching. Without it,
  an indicated lane is a candidate only for a geometrically unambiguous physical
  branch family. A closed/prohibited parallel branch is still part of the physical
  ambiguity: excluding it legally does not prove where a painted arrow connects.
  Missing branch geometry, roundabout tangent geometry or unknown relevant access
  cannot create a verified lane assignment.
- A compulsory bend can be labelled follow-road; straight transitions and ordinary
  left/right/slight/sharp/reverse geometry are available as route-level descriptions.
  Geometry creates no painted arrow. Same-way shape transitions are suppressed
  when there is no actual branching or explicit connectivity evidence.

Lane candidates are advisory evidence about usable lanes for the planned road.
They are not a command to change lanes immediately, a current-lane estimate,
proof of a safe gap, or an independently surveyed real-road permission.

## Unknown-data policy and remaining limits

Missing lane evidence never closes a road/turn. Arrow absence is not a turn ban.
Confirmed one-way, road-access and no/only turn restrictions remain enforced;
connectivity cannot override them. Optional invalid data does not grant permission.

This is an initial bounded static component. It does not evaluate lane-specific
vehicle access, time-dependent lane rules, both-ways lanes, via-way connectivity,
placement inference, safe lane-change manoeuvres, multi-junction lane reachability,
spiral/turbo roundabout lanes, current-lane positioning, voice timing or Android
rendering. Vehicle-specific lane information suppresses advice until those
semantics are implemented; this stage is not lane-aware legal route acceptance.
Directions use immediate endpoint geometry, so motorway-fork-specific instruction
quality and longer geometry lookahead remain pending. These limits do not imply
that a road is closed.

## Executed evidence

**238 local test methods passed**, including **26 new lane/junction methods** and
**1,197 exhaustively enumerated lane-indication combinations** checked against an
independent membership oracle on an original synthetic crossroads. Tests also
cover directional import, missing/invalid/vehicle lane data, ambiguous and missing
geometry, physical branches that are legally closed, count mismatch, explicit
connection priority, lane-change-only links, connectivity bounds/duplicates,
interior segments, live progression, no extra route jobs and confirmed bans.

The four existing roundabout journeys were rerun: all **80 numbering checks**,
exit clearing and arrival checks passed after the shared path refactor. Source
compilation and explicit source privacy inspection passed. Exact source hashes
and per-test records are included in results/.

One fresh actual GraphHopper 11.1 process served three original crossroads queries.
DriveMate Navigation and GraphHopper matched left, straight and right route
instructions and selected roads: all three tied directional correctness. The
GraphHopper instructions returned no lane fields. Lane comparison is therefore
not applicable in this adapter, not a claim of DriveMate lane superiority or of
GraphHopper's global capabilities. Raw responses, checksum, fixture and observations
are retained. Current DriveMate results were rechecked against those unchanged
responses after the final physical-branch correction. No latency or score ranking.

The separate verified reference cache was reused; no Maven download, new CI or
Android build was needed. Reference engine code was not incorporated into DriveMate.

## Reproduce

```sh
python3 -m compileall -q engine navigation_core map_data benchmarks tools tests
python3 -m unittest discover -s tests -p test_lane_guidance.py -v
python3 -m unittest discover -s tests -v
python3 -m benchmarks.roundabout_progress_replay
python3 -m benchmarks.junction_reference --jar /path/to/verified/GraphHopper_11.1_Benchmark_Cache.jar
```

Primary format definitions reviewed:
https://wiki.openstreetmap.org/wiki/Key:turn:lanes
https://wiki.openstreetmap.org/wiki/Relation:connectivity
https://wiki.openstreetmap.org/wiki/Lanes
No third-party source or real map data was copied into the synthetic fixtures.

Next: GPS road matching, while retaining the outstanding advanced-lane,
conditional-reference, portable-timed-routing and real-road/device validation gaps.
