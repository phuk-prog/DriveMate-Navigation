# Every test, results and recommended improvements (17 October 2026)

One line of results per test, then what to improve. Engines: DMN (ours) and six yardsticks
(OSRM, Valhalla, GraphHopper, openrouteservice, BRouter, OsmAnd). Real Greater Manchester
OpenStreetMap data; only GPS is simulated. "Right" means right by the map, not checked
against street signs. Recommendations already approved by the owner are marked (approved).

## 1 Map data and road network
**1a Car access per road (78 roads):** DMN 78/78, Valhalla 78/78.
**1b Wider six-region check (120 roads):** DMN sure on 79, held back on 41 unclear roads.
**1c Banned turns (142 junctions):** DMN 131, 0 banned turns; Valhalla 112 (9 banned), OSRM 111 (3), GraphHopper 66.
**1d Bollards and gates (61):** DMN 46 = OSRM 46, Valhalla 42, GraphHopper 9; nobody crossed a closed barrier.
Improve (approved): ask once about a gate/private road at your own start or finish and remember it;
time-limited rules by the clock; check the 5 no-route junctions on Mapillary; your own turn/gate corrections.

## 2 Road rules on whole routes
**2a No-car roads (44):** DMN 44, Valhalla 42, OSRM 41, GraphHopper 30, openrouteservice 30, OsmAnd 23, BRouter 20.
**2b One-way roads (48):** DMN 48, OSRM 47, Valhalla 47, GraphHopper 45, openrouteservice 43 (1 wrong way), OsmAnd 43, BRouter 37.
Improve (approved): any route using a no-car road or a one-way the wrong way is a FAIL, in tests and
in the app's check of received routes; time-limited gates/one-ways by the clock; say on screen when
the only route is through a bus gate; add "one way except cycles" roads to the test.

## 3 Knowing which road the car is on (24 normal drives, 4,474 GPS points)
Run C [39062533167](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39062533167), revision `3d93a47`: every engine rerun after the DMN change; same traces for all.
Right / wrong road (run 39062533167; the next piece of the same road counted apart, not as wrong):
OSRM 96% / 1.2%, Valhalla 85% / 1.0%, GraphHopper 81% / 1.0%, DMN before the fix 37% / 0.07%,
**DMN with the fix 78% / 0%** (0 wrong roads in 4,474 points).
Improve (approved): make the fix DMN's normal setting; keep the position moving when unsure;
never use OSRM for the live position; private replay of real drives.

## 4 After losing GPS (24 drives, 25 s blackout, a 60 m jump reading, a vague reading)
Right / wrong in the first 30 s: OSRM 91% / 5.8%, Valhalla 44% / 14%, GraphHopper 39% / 2.1%
(matched nothing on 14 drives), DMN before 42% / 0.14%, **DMN with the fix 77% / 0.28%**.
DMN with the fix back in 3 s (worst 5 s; before: 4 s, worst 19 s); 46 of 48 bad readings ignored (before 47).
Improve: rerun with the fix; keep the car moving on the map and keep announcing during a blackout;
use the Pixel's motion sensors and Android Auto car speed; tighten the jump check (1 got through).

## 5 Giving a valid route (57 short junction routes)
All seven engines 57/57.
Improve: none needed here; long trips are untested (see 6 and 7).

## 6 Route quality (24 journeys of 1–2 km)
Valid routes: DMN 24, Valhalla 24, OSRM 23, GraphHopper 14, openrouteservice 14, OsmAnd 11, BRouter 9.
Length against the shortest found: DMN 1.00, OsmAnd 1.00, GraphHopper 1.00, openrouteservice 1.03,
OSRM 1.05, Valhalla 1.05.
Improve: test long trips (motorway, 20–50 km); judge by time as well as distance; prefer main roads
over rat-runs where the time is equal; fix the test's reading of other engines' long routes.

## 7 Route calculation speed (18 journeys, one machine)
Over local HTTP: OSRM 1.2 ms, Valhalla 3.5, openrouteservice 9.3, GraphHopper 11.3, DMN 12.5, BRouter 27.1.
In-process: DMN 11.6 ms, OsmAnd 41.1. Map load: DMN 0.2 s, others 1.2–6.3 s.
Improve: fast enough for a phone now; time long trips and a whole-region map; if slow, add a
quicker search (precomputed shortcuts) without changing which route is legal.

## 8 Junction turn instructions (36)
DMN 36, OSRM 36, openrouteservice 36, BRouter 36, OsmAnd 36, Valhalla 35, GraphHopper 31.
Improve: add "bear left/right" and staggered-junction cases; check the spoken wording follows UK Highway Code terms.

## 9 Roundabout exits (judged)
DMN 21/21; Valhalla, GraphHopper, BRouter, OsmAnd 20/20; openrouteservice 17/17; OSRM 17/20.
Improve: add big multi-lane and mini roundabouts, and exits that are service roads.

## 10 Lanes (36 junctions)
DMN 35/35; OsmAnd 25/34 (9 no answer); OSRM 22/36 (2 wrong, 12 no answer); others give no lanes.
Improve: the app should use our lane data, not OSRM's; add lane tests where OSM has no lane data
(Mapillary arrows); show "no lane data" rather than guess (data-only rule already agreed).

## 11 Route line on the road
DMN draws along map points (not applicable); others 0 over 5 m on short routes; on 1–2 km routes
the test could not read some lines (a test weakness).
Improve: fix the test's line reading on long routes.

## 12 Wrong turns and re-planning (24 drives)
Before the fix: 23 of 24 spotted (median 8 s, worst 15 s), 1 lost, 1 false re-plan after a blackout.
**With the fix: 24 of 24 spotted (median 3 s, worst 13 s), all new routes legal, all reached the
destination, 0 false re-plans.**
Re-planning from the wrong road: DMN 24 valid and shortest; Valhalla 24 (30% longer); OSRM 23 (16% longer);
GraphHopper 14; openrouteservice 14; OsmAnd 12; BRouter 4.
Improve: require fresh good readings after a blackout before re-planning; spot wrong turns faster at
speed (e.g. 5 s); a U-turn should only be offered where it is legal and safe.

## 13 Turn announcements (DMN only)
Before the fix: 308 on time, 7 late, 1 after the turn; 54 turns never announced in normal drives.
**With the fix: 451 on time, 12 late, 1 after the turn; 5 never announced.**
Improve: the fix; announce from the estimated position when briefly unsure; a second "now" announcement
close to the turn; time announcements by speed (motorways earlier).

## 14 Road closures (24)
DMN 24 = Valhalla 24, OSRM 23, GraphHopper 14, openrouteservice 14, OsmAnd 11, BRouter 7.
Nobody seen driving a closed road. DMN's live-closure input = map closure 24/24.
Improve: feed TomTom and National Highways closures into DMN's live-closure input; say "road closed
ahead, new route" on screen and by voice.

## 15 Speed limits (judged roads)
DMN 61/61, GraphHopper 68/68, OsmAnd 65/65; others give no limits.
Improve: add roads with different limits each way and time-limited 20 mph zones; show "limit unknown"
rather than guess.

## 16 Arrival (DMN only, 72 drives)
Before the fix: correct 9, never said "you have arrived" 62, 1 not reached.
**With the fix: correct 60 of 72, never said it 12, no early or wrong-place arrival.**
Improve: the fix; also arrive when stopped near the destination; say which side the destination is on.

## 17 Damaged maps and updates
OSRM, openrouteservice, BRouter, OsmAnd 12/12; DMN 16/18; GraphHopper, Valhalla 3/12 (never started).
DMN refused all 9 damaged files and kept the old map, but refused 2 of 3 good real maps (time-based rules).
Improve: let offline maps with time-based rules load (rules handled per road); show which map version is in use.

## 18 Bad requests
DMN 12/12, GraphHopper 14/14, openrouteservice 14/14, OsmAnd 12/14, BRouter 12/15, Valhalla 9/14, OSRM 9/15.
OSRM and Valhalla quietly route elsewhere (up to 31 km away) when a place is unreachable.
Improve: the app warns when a route from any service ends more than about 50 m from where you asked.

## 19 Memory and processor (DMN only)
About 18 ms of work per GPS point (same with the fix), about 1.2 MB memory (worst 3.3 MB). Battery and map size not measured.
Improve: measure battery and memory on the Pixel with a whole-region map.

## 20 Whole journey (DMN only, 72 drives)
Before the fix: 8 of 72 fully passed. **With the fix: 57 of 72** (12 no arrival, 2 had a wrong
position, 1 late announcement after a turn).
Improve: arrival when stopped near the destination (the 12 left); look at the 2 wrong positions;
then real recorded drives.

## 21 Test fairness
DMN 54/54, Valhalla 54/54, OSRM 53, GraphHopper 48, openrouteservice 48, OsmAnd 48, BRouter 45.
Improve: fix the test's long-route reading; watch engine start-up so a quick failure is seen.
