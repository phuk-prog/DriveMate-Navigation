# TURN-001 results — turn restrictions on real Greater Manchester junctions

17 October 2026. Research engine test only (no Android app).

**What is tested.** 142 real junctions where OpenStreetMap (OSM) bans a turn
("no right turn", "only straight on" and so on). Each engine gets the same small
map clip and the same start and finish, chosen so the quickest route *without*
the ban would make the banned move. The route is then checked:

- did it make the banned move? (**fail**)
- did it start and finish on the exact road segments asked for? (if not: **off-target**)
- does the whole route obey every other one-way and turn ban on the clip? (**full rule check**)
- if there is no route, it is asked again on a map 3 times wider.

"Pass" below means: right start and finish, no banned move, and the whole route
passes the full rule check. OSM is the reference, not independent proof of the
law on the street.

Frozen inputs (same in every run): OSM source `2a8ef8e1…22acba`, cohort
`f2949a8a…c391c`, prepared clips `8500d8f3…07bf3`
(branch `data/turn001-snapshot`). 169 frozen relations, 142 testable,
129 "discriminating" (the route without the ban really does use the banned move).

## Current result — TURN-001 v1.3 after the DMN fix (fresh run of all engines)

Run [39019749346](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39019749346),
commit `0668fce`, all five jobs passed. Harness self-check (OSRM with the tested
ban removed): 121 of 129 discriminating cases then make the banned move, so the
test does catch violations.

| Engine | Pass | Pass but route breaks another rule | Fail (banned move) | No route | Off-target | Start/finish road closed to cars |
|---|---|---|---|---|---|---|
| DMN | **131** | 0 | **0** | 5 | 0 | 6 |
| Valhalla 3.9.1 | 112 | 3 | 9 | 0 | 18 | — |
| OSRM 5.27.1 | 111 | 2 | 3 | 13 | 13 | — |
| GraphHopper 11.1 | 66 | 1 | 0 | 7 | 68 | — |

Each row adds up to 142. Only cases with the same start, finish and map are
compared, so this is a like-for-like ranking for this test only: DMN, then
Valhalla, OSRM, GraphHopper.

### Reasons for failures, case by case

**DMN.** No banned moves and no rule breaks.
- *6 start/finish roads closed to cars* (4853640, 8798974, 13119340, 13119370,
  20158895, 21197635): OSM itself marks the start or finish road as closed to cars.
  Refusing is correct.
- *5 no route* (also none on the 3x wider map). No other engine found a route
  that passes the full rule check at any of them:
  - 10558420 (no straight on): OSRM and Valhalla only got through by going straight on
    (the banned move); GraphHopper found nothing.
  - 13613008 (only U-turn): Valhalla made the banned move; OSRM finished 23 m away on
    another road; GraphHopper found nothing.
  - 16644804 (only left turn): OSRM found nothing; GraphHopper and Valhalla finished on
    the wrong road.
  - 4853555 (no straight on): OSRM and Valhalla finished 13 m away on another road;
    GraphHopper found nothing.
  - 7615778 (no straight on): all three stopped 53 m short, still on the start road.
  Whether a legal way through truly exists at these five is not proven either way.

**Valhalla.** 9 banned moves: 10558420, 7968303, 19797631 (no straight on), 12722170
(no entry), 13442755 and 13613008 (only U-turn), 14241462 (no U-turn), and 13119284,
13119287 (time-limited bans; the frozen rules count them at all times). Pass routes that
break another rule: 14262912 (wrong way along one-way 512386300 and against
"only straight on" 14262910), 15774822 (wrong way along one-way 246370185),
7301773 (uses time-limited ban 13119284, legal only at some times). 18 off-target:
start or finish snapped to a different road segment.

**OSRM.** 3 banned moves: 10558420, and 13119284, 13119287 (time-limited bans).
Pass routes that break another rule: 14262912 (as Valhalla), 7301773 (time-limited).
13 no route; at 12 of them DMN found a route that passes the full rule check
(10182417, 11902362, 11902363, 11902364, 12722170, 17548962, 19755564, 19797631,
20032015, 20066776, 6316748, 7968303). 13 off-target.

**GraphHopper.** No banned moves. 68 off-target: GraphHopper often attaches the start
or finish to a different segment, so most of its routes cannot be judged. Pass route
breaking another rule: 14262912 (as above). 7 no route; at 4 of them another engine
had a passing route (12420333, 13166535, 13442755, 14285234).

### Query times (milliseconds)

Measured on GitHub's shared runners. The scopes differ, so **speed is not ranked**.

| Engine | What is timed | Run 39019749346 median / p95 | Run 39018620731 median / p95 | Samples, errors |
|---|---|---|---|---|
| DMN | Read the clip, build the road graph and route, in-process Python (cold, per case) | 173.3 / 614.8 | 125.0 / 480.0 | 142, 0 |
| OSRM | One warm query to a local server (graph built beforehand, not timed) | 1.4 / 1.8 | 1.3 / 1.7 | 142, 0 |
| Valhalla | Same as OSRM | 18.8 / 20.6 | 14.5 / 15.8 | 142, 0 |
| GraphHopper | Same as OSRM | 71.7 / 86.1 | 84.1 / 97.9 | 142, 0 |

Base-clip queries only. Graph build time for OSRM, Valhalla and GraphHopper was
not measured. Run-to-run spread on shared runners is up to about 40 % for DMN.

## The fix made in this round

In the first v1.3 run, DMN had no route at 6 junctions. Only one of them,
**14285234**, had a route from another engine that passed the full rule check
(OSRM and Valhalla, identical routes).

*Why DMN missed it:* at this junction OSM says cars may **only turn right**, into an
18 m service road that dead-ends. The legal journey is: turn right into it, turn
round at the end, come back out. That service road has no access tags. DMN's safety
rule allows an untagged service road only at the very start or end of a journey,
never in the middle, so DMN refused it.

*Fix* (commit `0668fce`):
1. If an OSM "only this turn" ban, starting from a normal road open to cars, sends
   cars onto an untagged service road or track, DMN now treats that road as open to
   cars. The map is saying that is where cars go. Any access tag (private, no,
   destination, customers…), a time-limited rule, a barrier, or a "no turn" ban is
   still respected. Other untagged service roads are unchanged.
2. A related flaw found by the new tests: DMN let a car that was already on a normal
   road use untagged service roads as a short-cut, as if it were still starting out.
   Now the start allowance ends once the car is on a normal road, as the rule
   always intended.

Result: 14285234 now passes with the same route as OSRM and Valhalla. No other DMN
case changed (checked locally on all 142, then on GitHub). All 21 unit-test
categories pass (739/739).

## Earlier results — kept separate, not comparable with v1.3

The test rules changed between versions, so these numbers must not be added to,
or ranked against, the v1.3 table.

**v1.3, first run, before the fix** (run
[39018620731](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39018620731),
revision `3d81bf5`). Reference engines: same verdicts as the current table.
DMN: pass 130, fail 0, no route 6 (14285234 plus the 5 above), off-target 0, closed
start/finish 6.

**v1.2** (code `d4fa600`: adds the full rule check to every route). DMN: pass 108
(all 108 also pass the full rule check), fail 0, no route 7, off-target 0, start or
finish withheld 27 (17 untagged service roads under DMN's old policy, 10 closed to
cars in OSM).

**v1.1** (code `4f82085`: DMN learned via-way bans and to finish along the
destination road). DMN: pass 108, fail 0, no route 7, off-target 0, start or finish
withheld 27.

**v1** (code `3cd2d78`, DMN before the Category 1 fixes). DMN: pass 14, fail 7
(the harness added the final turn unchecked), no route 0, off-target 0, map
refused 117 (45 time-limited tags unsupported, 33 "only single via-node bans
supported", 30 "missing/non-drivable manoeuvre", 8 clip too large, 1 alternating
one-way unsupported), errors 4 (start/finish road not usable).

*Where these numbers come from:* the earlier sessions did not save the per-engine
result files. The DMN numbers above were regenerated on 17 Oct 2026 by running each
old version's own test code on the same frozen inputs (local machine). v1 matches
the record in commit `4f82085` (117 map refusals, 7 illegal final turns).
**OSRM, GraphHopper and Valhalla results for v1–v1.2: unavailable.** They were not
saved, and v1.3 found those versions could not see a banned move made on the first
or last part-segment of a route, so they would not be reliable anyway.

## Next test

**A route-level check of bollards and gates.** Same method as TURN-001: a frozen set
of real Greater Manchester barriers (bollards, blocks, gates, lift gates) on roads
where the quickest route without the barrier would pass through it. Every route from
all four engines is checked for driving through a barrier node, using the barrier's
own access tags. Gates with no access tags are reported separately, not as failures.
Not started.
