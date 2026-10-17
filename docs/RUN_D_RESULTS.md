# Run D: quick targeted checks (categories 7, 14, 17, 18, 21)

One shared run, five separately scored categories (no combined score):
[39055768229](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39055768229),
revision `0d56359`, finished 17 Oct 2026 19:33 UK time. Harness `benchmarks/run_d.py`;
cases frozen in `config/rund-prepared.json` before any engine ran. Every clip is a
hash-checked JOURNEY-001 clip of the pinned OSM snapshot. Truth is map-derived, not road law.
Engines: DMN, OSRM 5.27.1, Valhalla 3.9.1, GraphHopper 11.1, openrouteservice 10.1.0,
BRouter 1.7.10, OsmAnd (nightly; build hash in the run). All jobs passed.

## Category 7: route calculation speed (18 journeys of 1–2 km)

Each journey: 1 warm-up and 10 timed identical queries. All engines ran on ONE machine
(AMD EPYC 7763, 4 cores), case by case, with the engine order rotated. Figures are the
median and p95 of each engine's per-journey medians, on the 7 journeys every engine
answered validly. Map import/build is setup and is not ranked.

| Rank | Scope A: localhost HTTP round trip | median ms | p95 ms |
|---:|---|---:|---:|
| 1 | OSRM | 1.17 | 1.40 |
| 2 | Valhalla | 3.54 | 5.28 |
| 3 | openrouteservice | 9.31 | 13.92 |
| 4 | GraphHopper | 11.34 | 12.53 |
| 5 | DMN (behind a small local server) | 12.54 | 43.53 |
| 6 | BRouter | 27.05 | 41.97 |

| Rank | Scope B: in-process call, map loaded | median ms | p95 ms |
|---:|---|---:|---:|
| 1 | DMN | 11.62 | 43.31 |
| 2 | OsmAnd | 41.08 | 60.11 |

OsmAnd has no server, so it is only in scope B. On all 18 journeys (every answer, valid or
not) the order is the same; DMN median 17.1 ms. Setup (not ranked), median: DMN import
0.23 s, Valhalla 1.2 s, OSRM 1.4 s, BRouter 1.4 s, GraphHopper 3.6 s, OsmAnd 5.2 s,
openrouteservice 6.3 s.

## Category 14: road closures (24 journeys)

The road carrying the middle of the map's shortest path is closed (`access=no` written
into the clip every engine gets). Without the closure, DMN's own route used that road in
16 of 24 journeys, so the test bites.

| Rank | Engine | Valid detour | Drove the closed road | Missed a detour | Detour vs shortest (median) |
|---:|---|---:|---:|---:|---:|
| =1 | DMN | **24/24** | 0 | 0 | 1.00 (1 over 1.2x) |
| =1 | Valhalla | 24/24 | 0 | 0 | 1.055 (5 over 1.2x) |
| 3 | OSRM | 23/24 | 0 | 0 | 1.02 |
| =4 | GraphHopper | 14/24 | 0 | 0 | 1.00 |
| =4 | openrouteservice | 14/24 | 0 | 0 | 1.04 |
| 6 | OsmAnd | 11/24 | 0 | 0 | 1.09 |
| 7 | BRouter | 7/24 | 0 | 0 | 1.00 |

Every non-valid answer is OFF_TARGET (did not end, or start, on the asked road piece in
the asked direction). For GraphHopper, openrouteservice, OsmAnd and BRouter about half of
these come with a drawn line the harness could not fully read back as OSM roads (see
category 21), so **"drove the closed road = 0" is proven for DMN, Valhalla and OSRM only**;
for the other four it holds for the part of the line that was read. DMN's live-closure
input (`blocked_edges` on the open map) gave the same route as the map closure in 24/24.

## Category 17: damaged map files (3 clips × truncated, corrupted, no roads, then good map)

| Rank | Engine | Passed / judged | Notes |
|---:|---|---:|---|
| =1 | OSRM, openrouteservice, BRouter | 12/12 | refused all 9 damaged files with an error; good map routes again |
| =1 | OsmAnd | 12/12 | refused truncated/corrupted; empty map built with no route (no crash) |
| 5 | DMN | 16/18 | refused all 9 damaged packages, old map kept routing the same, recovery 3/3, map update 3/3; **refused 2 of 3 good real maps** |
| =6 | GraphHopper, Valhalla | 3/12 | never started on any damaged file (waited 90 s / 240 s); good map routes again |

No engine served a route from a damaged file. GraphHopper and Valhalla are marked down
for giving no clear answer within the wait, but the harness does not watch their own
process, so a quick error from them inside the wait is **UNVERIFIED**, not ruled out.

DMN fault (verified): its offline package store rejects any map containing a time-based
rule (`*:conditional` tag), and 2 of the 3 real clips have one. The damage checks then
ran on a labelled copy with those tags removed. The research importer handles such tags
per road; only the offline package contract refuses them.

## Category 18: bad requests (3 clips; 4 bad requests + "still alive")

| Rank | Engine | Passed / judged | Failures |
|---:|---|---:|---|
| =1 | DMN | **12/12** | none (outside-map not applicable: DMN takes road pieces, not coordinates) |
| =1 | GraphHopper | 14/14 | none |
| =1 | openrouteservice | 14/14 | none |
| 4 | OsmAnd | 12/14 | unreachable destination: routed to a different road 278 m and 589 m away |
| 5 | BRouter | 12/15 | destination about 31 km outside the map: routed to the nearest road (3/3) |
| 6 | Valhalla | 9/14 | outside the map (3/3) and unreachable (2) routed elsewhere |
| 7 | OSRM | 9/15 | outside the map (3/3, about 31 km away) and unreachable (3/3) routed elsewhere |

All engines answered the same start and finish sensibly, refused the impossible
latitude, and gave the same answer afterwards (no crash, no hang).
Scoring note, made after this run and before any engine change: in one clip the
"unreachable" street can be reached along unmarked `highway=track` roads (no access tags,
so car legality is unknown). Answers that reached it (GraphHopper, Valhalla,
openrouteservice, OsmAnd: one each) are UNRESOLVED and left out of "judged" above;
`summary.json` still counts them as not passed.

## Category 21: comparison integrity (harness checks per engine, 18 journeys × 3)

Repeat answers identical, start/finish at the asked points, drawn line readable as OSM
roads (all within 5 m), DMN's server answer equal to its direct call.

| Rank | Engine | Passed | Failed check |
|---:|---|---:|---|
| =1 | DMN | 54/54 | none |
| =1 | Valhalla | 54/54 | none |
| 3 | OSRM | 53/54 | 1 finish point off the asked point |
| =4 | GraphHopper, openrouteservice, OsmAnd | 48/54 | line not readable in 6 journeys |
| 7 | BRouter | 45/54 | line not readable in 9 journeys |

This ranks the test set-up, not the engines. Every engine gave identical repeat answers.
The line reader, which was fine on the short run B routes, loses some 1–2 km lines.

## Issue register (exact cases in `summary.json` of the run)

1. DMN (verified): offline packages refuse real maps with time-based rules (2/3 clips).
2. DMN: detour 1.2x+ longer than the shortest found by any engine in `turn-307444490`
   (map-derived; DMN routes by time, others' shortest may differ in time).
3. Harness: line reading on 1–2 km routes (category 21), so the off-target counts of
   GraphHopper, openrouteservice, OsmAnd and BRouter in categories 7 and 14 are partly
   UNRESOLVED.
4. Harness: GraphHopper/Valhalla start failures are only seen as time-outs.
5. Harness: one "unreachable" destination is reachable by unmarked tracks.

## Proposed improvements (each needs the owner's approval; none made)

- DMN: let offline packages accept maps with time-based rules, handled per road as the
  research importer already does; then rerun category 17 for every engine.
- Harness: keep each engine's raw line and improve reading of longer lines; watch
  engine processes so a quick start failure is seen; then rerun categories 7, 14 and 21.
