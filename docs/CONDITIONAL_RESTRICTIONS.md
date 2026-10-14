# Imported complex restrictions — verified local stage

DriveMate Navigation remains an independent navigation laboratory, separate from
the Android application. Base: public repository commit
05fc0a7f1f7f848b894a146c62835b871f6e09e2. No GitHub writes or builds.

## Implemented

- Single via-node and one/multiple via-way relations are resolved to actual directed
  road segments, including reversed via ways and split segments.
- Multi-road bans preserve inbound history. Mandatory turns also enforce the
  required continuation at earlier intermediate exits.
- Same-way U-turn bans distinguish reversal from continuing straight.
- Unknown road access remains routable and is reported as unverified. Explicit
  road prohibitions, one-way directions and turn restrictions remain enforced.
- Two explicit conditional paths are available. Both accept only a documented
  weekly schedule subset: optional weekday or wrapping weekday range, one minute-
  precision time span, including overnight spans. Conditions using holidays,
  weather, dates, dimensions, complex opening_hours grammar, and road-access or
  one-way conditional tags are unsupported and rejected.

### Turn-arrival evaluation

With no compiled window, the importer supports one weekly `no_*` conditional
clause and no static/conditional override combination. `prepare_navigation`
retains its condition; `route` needs an aware departure and the road's IANA time
zone (explicit or from a ZoneInfo departure). Arrival is converted through UTC,
including daylight-saving changes. The condition is evaluated at the start of
the restricted final manoeuvre, using estimated accumulated travel time.

The bounded search retains different elapsed-time labels for the same road state.
Discarding later labels is invalid when a ban ends later. It searches non-waiting
walks and may return legal circuits; it does not model deliberate waiting. The
100,000 default label/state budget can be overridden explicitly. Budget exhaustion
raises `IncompleteTimeSearch`, never `RouteNotFound`. Mode parameters are validated;
timed queries use time-expanded Dijkstra rather than heuristic performance modes.

This path runs in the research implementation. Portable execution rejects it
explicitly; dynamic native support remains pending. Traffic, stops and travel-time
errors can change actual junction arrival: this is estimated-clock simulation,
not a real-road legality guarantee. Timed journey integration is now implemented; see TIMED_JOURNEY_STAGE.md.
It requires an explicit road timezone and aware datetime observations.

### Compiled interval evaluation

For both research and portable routing, import with `window=(aware_start,
aware_end)` and `timezone_name`. The half-open interval is limited to seven days.
The evaluator considers every weekly-rule change within it and compiles the union
of applicable bans/mandatory continuations. A route requires an aware departure
inside that interval and its estimated completion must precede the interval end.
Static base rules apply when no conditional clause is active. Conflicting
simultaneous clause values are rejected rather than guessed.

This is conservative: a route legal at one exact arrival time may be excluded
because a restriction applies at another time in the interval. It is not an
exact time-dependent shortest route, and it must not be presented as one.

## Validation

151 local test methods passed (see full log), including the six inherited tests
whose time-aware implementation was missing at resume. Thirteen new complex-import
methods include 60 independently enumerated acyclic timed route comparisons.
Coverage includes later arrival labels, start/end boundaries, overnight rules,
DST repeated hours, required clocks, interval expiry, unsupported conditions,
wrong-way via paths, multi-segment history, early exits, and unknown access.
Portable host source rebuilt with warnings treated as errors. Source compilation
and explicit-source privacy scan passed. The Git-tracked privacy CLI is unavailable
in a non-Git snapshot; its inspection function was run on source files directly.
No Android, raw GPS, on-road or full navigation-app validation was performed.

Six fresh actual GraphHopper 11.1 comparisons used original synthetic OSM fixtures:
no/only multi-segment route, unrelated arrival, and early exit. Each compared both
DriveMate execution paths to independently authored expected road sequences.
All six tied correctness. GraphHopper's checksum, exact fixture hashes and raw
responses are retained in results/import_competitor. There is one observation per
case. Costs/profiles differ, so latency, route cost and scores are not ranked.
No conditional competitor comparison has been executed in this stage.

Initial setup failures are recorded: incomplete cached JAR (checksum rejection),
missing required ignored-highways configuration, and success-response `hints`
metadata having a dictionary shape. The complete pinned JAR was downloaded once;
configuration was corrected; adapter response handling gained regression tests.
No arbitrary retry loop or duplicated CI was used. The JAR and graph caches stay
outside the source deliverable; no reference-engine code was incorporated.

## Reproduction

From navigation_work:

```sh
bash navigation_core/native/build.sh
python3 -m compileall -q engine navigation_core map_data benchmarks tools tests
python3 -m unittest discover -s tests -v
python3 -m benchmarks.import_restriction_compare --jar /path/to/verified/graphhopper-web-11.1.jar
```

Reference semantics: https://wiki.openstreetmap.org/wiki/Relation:restriction
and https://wiki.openstreetmap.org/wiki/Conditional_restrictions . No OSM map data
or third-party source is embedded in the synthetic fixtures. Distribution licence
for the original project remains an explicit owner decision.

Next: clock-aware reroute integration and equivalent conditional-engine comparisons,
then evidence-backed roundabout exits. Lane and raw-GPS subsystems remain pending.
