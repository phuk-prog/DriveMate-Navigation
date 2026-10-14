# Roundabout exit identification — verified local stage

This is an original navigation-software component, not a map/UI redesign. No
GitHub mutation, Android modification, APK build or on-road test was performed.

## Contract and implementation

The importer now preserves each directed road's actual `junction` tag. Ordinary
roundabouts are distinct from `junction=circular`. Mini-roundabout nodes do not
become invented circular roads. The source format's one-way directions remain
unchanged. Guidance is exposed through `PreparedNavigation.roundabouts(route,
...)` for whole-road route sequences, with optional inbound entry context.

Preparation indexes connected tagged roundabout components and their outgoing
roads once. A component receives numerical guidance only when its tagged topology
is a simple directed cycle of at least three nodes. Branching/multiple connected
rings, incomplete cycles and explicitly bidirectional circles do not get a number.
This does not prohibit routing through them; it withholds unsupported guidance.

Numbers count legal motorcar departure opportunities at successive encountered
ring nodes. Incoming-only roads do not count. Confirmed road prohibitions and
history-dependent no/only turn rules exclude unavailable departures. Weekly bans
are checked at the estimated arrival at each candidate turn; the caller must supply
an aware departure and road timezone for time-dependent graphs. Full-route
continuity/access/turn legality is validated before guidance is returned.

This legal-departure convention is explicitly the current model, not an assertion
that every real sign uses the same numbering. Comparisons involving restricted exits
and real signed numbering remain pending and may require a separate physical-exit
number. The four external comparisons below contain no disputed restrictions.

Known uncertainty is kept visible:

- Unknown access remains routable. An exit-count candidate is retained internally,
  but no verified `exit_number` is emitted if a relevant opportunity has unknown
  access. No permission is invented and no lane arrows are inferred.
- Several departing roads at one node need explicit independent physical-exit
  grouping. Adjacent splits with the same evidenced group count once. Missing or
  conflicting groups, or a reused group after intervening exits, withhold the number.
  The importer does not manufacture grouping from names or coordinates.
- Starting inside without entry context yields `started_inside`; a destination
  inside yields `destination_inside`. Circulating more than one full lap yields
  `repeated_circulation`. All keep the route/exit road evidence, but no absolute number.
- A bypass that does not enter tagged ring roads receives no roundabout instruction.

`numbered` means verified against this graph snapshot and its authored restrictions,
not independently surveyed real-road completeness or current legal signage.

## Executed evidence

**192 local test methods passed**, including 23 new roundabout methods. Two
independent enumerations cover **462 synthetic combinations**:

- 398 entry/exit combinations for three- to eight-node rings, every entry rotation,
  both circulation directions and returning to the entry arm after one lap.
- 64 combinations of road-access bans or prohibited exit turns, checked against
  independently calculated legal-opportunity counts.

Other cases include incoming-only arms, unknown access, explicit/split grouping,
illegal/disconnected routes, multi-road history, timed bans at arrival, inside
starts/destinations, incomplete/branching/bidirectional topology and bypasses.
Catalogue identity is reused, costs are prepared once and restriction history is
bounded to relevant prefixes. No new latency or battery benchmark is claimed.

A **fresh actual GraphHopper 11.1 execution** used an original eight-node circular
fixture with four exit arms. DriveMate Navigation and GraphHopper both produced
exit numbers 1, 2, 3 and 4; each selected the independently authored expected roads.
All four tied correctness. One observation per case; no scores, latency, lane,
Android, real-road or complete-app superiority ranking is established. Exact
fixture/checksum, raw instructions and per-test records are preserved in
results/roundabout_reference/. The reference executable was repaired from its
missing byte range and accepted only after matching the pinned SHA-512.

Source compilation and the explicit local-source privacy scan passed. Historic
GraphHopper restriction comparisons remain separately labelled in earlier reports.
The reference runtime is a separate reusable benchmark cache, not DriveMate code.

## Reproduce

```sh
python3 -m compileall -q engine navigation_core map_data benchmarks tools tests
python3 -m unittest discover -s tests -p test_roundabouts.py -v
python3 -m unittest discover -s tests -v
python3 -m benchmarks.roundabout_reference --jar /path/to/verified/GraphHopper_11.1_Benchmark_Cache.jar
```

Reference tagging definitions reviewed:
https://wiki.openstreetmap.org/wiki/Tag:junction%3Droundabout
https://wiki.openstreetmap.org/wiki/Tag:junction%3Dcircular
https://wiki.openstreetmap.org/wiki/Tag:highway%3Dmini_roundabout
No third-party source code or real mapping data was incorporated.

## Remaining work

This API consumes whole-road node routes. It does not yet carry a numbered
roundabout's original entry through partial-road journey observations, coordinate
snapping or a reroute from inside the ring. That lifecycle integration comes next;
calling whole-road guidance with a partial-road clock would be incorrect. Complex
spiral/turbo/signal-controlled junctions and mini-roundabout instructions require
separate evidence-aware handling. Lane advice, audio/timing, real junction ground
truth, device testing and comparisons with additional navigation systems remain
pending. The time-aware portable/reference-engine gaps remain in the project state.

The newer LIVE_ROUNDABOUT_STAGE.md documents completed partial-road journey integration.
