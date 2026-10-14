# Time-aware journey rerouting — local verified stage

Current source is navigation_work/, based on the reconciled navigation laboratory.
No Android application or GitHub repository was modified, and no APK was built.

## Behaviour

- Timed journeys accept timezone-aware datetime observations and an explicit road
  IANA timezone. Snapshot timestamps are UTC epoch seconds; ordering is checked in
  UTC, including repeated local times when daylight saving ends.
- Road observations remain trusted, directed, contiguous road progression. They
  are not GPS fixes. Stale/out-of-order times, backwards progress and skipped roads
  are rejected without changing the accepted snapshot.
- Dynamic weekly bans are evaluated at estimated manoeuvre arrival, including
  partial origin/destination roads. Multi-road restriction history survives wrong
  turns. An already traversed turn is actual history, not new legal permission.
- Same-road observations recalculate timed plans: a stationary delay can activate
  a ban, and a later observation can recover a route when a ban ends. Static
  journeys retain their efficient same-road cost update without another search.
- One endpoint graph/router overlay is cached for identical position/history.
  Clock-dependent route results are never cached. Timed actions are indexed by
  their final road to avoid scanning unrelated restrictions for each road choice.
- Search-budget exhaustion yields status `incomplete`, with no guidance and no
  estimated remaining cost. It is never reported as `no_route`. Compiled-window
  expiry or insufficient remaining interval yields `restriction_window_expired`,
  also clearing the planned route.
- Compiled conservative windows use the portable host backend; exact timed search
  uses the research backend. Exact portable time-dependent execution is pending.
- A wrong-turn flag requires deviation from a known navigating plan. Missing or
  incomplete guidance does not establish that a driver made a wrong turn.
- Arrival on the actual accessible destination road is a terminal physical
  observation. It does not assert that previously traversed turns were legal.

## Executed evidence

The complete local suite passed **169 test methods**. Eighteen new timed-journey
methods include **60 independent partial-road/delay oracle comparisons**, in
addition to the preceding stage's 60 node-route oracle comparisons. Scenarios
include estimated-time boundary crossings, bans ending during progress,
wrong-turn history, restricted partial destinations, unknown-access flags,
stale/disconnected/backward observations, incomplete search, compiled expiry,
no-route recovery, stationary overlay reuse, repeated DST hours and arrival.

The initial ten tests failed because timed journey creation was unavailable.
Review tests then reproduced a misleading wrong-turn flag during an incomplete
plan. Both failures were corrected, and focused then full regressions passed.
Source compilation and an explicit local source privacy inspection also passed.
Per-test records and exact source hashes are in results/timed_journey_register.csv
and results/timed_source_manifest.json. These are executable synthetic tests,
not on-road, Android, GPS, battery or full-app validation.

No fresh external engine was executed this stage. The restored GraphHopper JAR
is truncated: 11,206,144 bytes, while the previously validated executable was
47,331,301 bytes, and its checksum no longer matches. OSRM, Valhalla and Docker
executables are absent. Prior six actual GraphHopper static restriction comparisons
remain historical evidence, not newly executed timed-journey comparisons.

GraphHopper 11.1's official RestrictionTagParser source explicitly filters conditional
turn keys out of the parsed restrictions:
https://github.com/graphhopper/graphhopper/blob/11.1/core/src/main/java/com/graphhopper/reader/osm/RestrictionTagParser.java
Reviewed source blob: 05ac5c49075dec72ae38cef9be313d1129f7ec61.
This is a source-reviewed capability limit, not a benchmark or score. No third-party
source was incorporated. Valhalla or an appropriately configured OSRM setup remains
needed for applicable time-aware engine comparisons. No winner is assigned here.

## Reproduce

```sh
python3 -m compileall -q engine navigation_core map_data benchmarks tools tests
python3 -m unittest discover -s tests -p test_timed_journey.py -v
python3 -m unittest discover -s tests -v
```

Remaining limits: bounded/non-waiting time-label search; limited weekly grammar;
estimated travel time rather than observed future arrival; no GPS/map matching;
no Android execution; endpoint overlay rebuilds when position/history changes;
no event scheduler between observations. Callers must provide a fresh valid
observation before treating a timed snapshot as current. Traffic, long stops and
clock correction need integration before real-road navigation. Actual device clock
jumps are not distinguished from elapsed waiting by this simulator.

Next component: evidence-backed roundabout exit identification, while keeping the
conditional competitor gap and portable timed-search gap in the test register.
