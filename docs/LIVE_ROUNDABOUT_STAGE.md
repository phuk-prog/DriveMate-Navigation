# Roundabout journey integration and unknown-data policy

DriveMate Navigation remains independent navigation research. No GitHub, Android
app, APK, real-drive or raw-GPS work was performed in this stage.

## Behaviour

`journey.roundabouts()` now reports guidance for the current accepted snapshot.
An entry observed before entering a ring is retained through partial-road progress.
A third exit remains the third exit after passing earlier opportunities. Leaving a
ring clears its context; a later roundabout gets its own entry and ledger.

Future manoeuvre clocks use the exact remaining integer-partitioned cost of the
current road, and the destination fraction. A full-road timing estimate is not
substituted for a partial-road origin. The actual current road is treated as
observed history, while every proposed future access/turn is still validated.
An already traversed illegal turn never becomes permission for another turn.

Past exit opportunities are recorded when their node is crossed, using observed
history and crossing time. They are not retroactively evaluated against the
current clock. A trusted observation at the next road's zero fraction supplies
an exact crossing event. At a positive fraction, crossing time lies between the
previous and current observations; if weekly availability changes within that
interval, the exit number is withheld with `uncertain_crossing_time`. The route
remains available. Explicit timed history without crossing timestamps likewise
does not fabricate those times.

Stopping at the end of a road does not repeatedly count its pending exit. A missed
exit triggers the existing rerouting controller; if the new plan requires more
than one lap relative to the original entry, it yields `repeated_circulation`
rather than a misleading ordinal. Inside starts without entry context, complex
rings, ambiguous groups and unknown relevant access retain the prior fallbacks.
Accepted data remains immutable; invalid/stale/disconnected observations do not
advance the roundabout context. Arrived, no-route, incomplete or expired snapshots
show no stale roundabout guidance.

The ledger is bounded to one ring's road count. Guidance results are cached for
an identical immutable snapshot. Existing prepared graph/catalogue and bounded
restriction indexes are reused; guidance itself does not launch another native
route process. Static same-road progress still avoids recalculating the route.

## User's confirmed unknown-data rule

Missing or unconfirmed access/lane information does not prohibit a road or turn.
Unknown-access roads remain routable and are labelled unverified. No lane advice
is invented from missing annotations. Confirmed access bans, directed one-way
roads and no/only turn restrictions remain enforced.

Importer review found that optional `turn:lanes:*:conditional` and supported
lane-destination annotation keys could cause an entire import to fail despite
not establishing a road prohibition. These optional hints now remain unverified,
with aggregate `unverified_lane_ways` metadata. They cannot grant permission or
hide a confirmed ban. Tests prove that a service road with unknown access and an
unparsed lane hint remains routable in its known one-way direction, while the
reverse direction and an explicit motorcar ban remain prohibited in both backends.

This is not a blanket waiver of source validation: missing roads, malformed data
and known conditional travel rules the importer cannot evaluate remain explicitly
unsupported. Such an import error is not a claim that a particular road is banned.
Lane-access/time-direction semantics and lane connectivity need their own verified
implementation before those features can be used in guidance.

## Executed evidence

**212 local test methods passed**, including **20 new integration/policy methods**.
The focused tests cover retained numbering, missed exits, partial timing, historical
versus current rule clocks, uncertain crossing intervals, end-of-road waits,
unknown entry/ring data, invalid observation atomicity, separate successive rings,
inside starts, explicit inbound history, arrival, one-way/access bans, optional lane
hint handling, and absence of extra route jobs during repeated guidance requests.

**Four complete trusted-road roundabout replays passed 80 numerical progress checks**,
then cleared guidance after exiting and reported arrival. The fixture checksum was
verified against the preceding stage's original synthetic GraphHopper fixture.
These replays reuse preserved actual GraphHopper original-entry instruction values
1, 2, 3 and 4. They do not execute GraphHopper again or compare its live journey
controller. No new competitor winner, speed score or complete-app claim is made.

Source compilation, source privacy inspection and archive integrity verification
passed. Exact source hashes, per-test register, red/green logs and replay observations
are retained in results/. No lane, voice, GPS, Android or real-road acceptance has
been established by these trusted-road controller tests.

## Reproduce

```sh
python3 -m compileall -q engine navigation_core map_data benchmarks tools tests
python3 -m unittest discover -s tests -p test_live_roundabouts.py -v
python3 -m unittest discover -s tests -v
python3 -m benchmarks.roundabout_progress_replay
```

Limits: trusted contiguous road observations; no automatic GPS matching; estimated
future travel time; limited weekly grammar; more than seven days between uncertain
timed crossings conservatively removes numbering; and no guidance refresh without
an accepted observation. Restricted-exit numbering still needs real signed evidence
and broader comparisons. The separate reference cache can support later appropriate
experiments without incorporating third-party engine code into DriveMate.

Next: evidence-based lane/junction guidance with useful fallbacks where lane data
is missing, while preserving confirmed routing legality and all existing regressions.
