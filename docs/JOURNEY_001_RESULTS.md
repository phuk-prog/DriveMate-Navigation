# JOURNEY-001 (run B1) — real junctions and roundabouts, four engines

> **Latest:** seven-engine results (adds openrouteservice, BRouter, OsmAnd) are in
> [SEVEN_ENGINE_SCOREBOARD.md](SEVEN_ENGINE_SCOREBOARD.md); DMN scores unchanged. The tables
> below are the earlier four-engine runs.

Categories 5, 6, 8, 9 and 11 from one shared run, each ranked separately (no total).
Truth is map-derived (hashed OpenStreetMap snapshot), not independent UK road law.

**DMN: 57/57 valid routes, 36/36 junction instructions, 21/21 roundabout exits** (v1.1,
after the owner-approved changes below; v1 had 18/19 judged).

## Run and frozen inputs

- Result of record (v1.1): [run 39044116917](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39044116917),
  revision `4abf5bf`, all four engines freshly rerun after the DMN change;
  [scores](../references/journey001-runB1-v1.1-20261017.json). First run (v1):
  [39043457966](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39043457966),
  [scores](../references/journey001-runB1-20261017.json).
- Owner decision (v1.1): every road a car may leave by counts as a roundabout exit,
  service roads included.
- Source: pinned Greater Manchester OSM snapshot `2a8ef8e1…`. Cohort
  `config/journey001-cohort.json`, frozen before any engine ran: junction nodes joining
  3–4 arms of car roads (no service roads, living streets, motorways, roundabouts or
  restriction via nodes), first clean movement in sha256 order; single closed
  roundabout rings with 3+ spoke nodes, entry by sha256. 3 km clips (hashes frozen in
  `config/journey001-prepared.json`). Testable: 12 left, 12 right, 12 straight-on
  turns; roundabout exit 1: 8, exit 2: 6, exit 3: 7.
- Turn truth from the bearing change at the junction node: straight under 25°, left
  or right 60–120°. Exit truth: ring nodes after the entry where a car may leave.
  Instructions are judged only when the engine's route makes the intended movement.

## Category 5 — valid route (legal, on the exact test segments)

| Rank | Engine | Valid |
|---:|---|---:|
| 1= | DMN | 57/57 |
| 1= | OSRM 5.27.1 | 57/57 |
| 1= | Valhalla 3.9.1 | 57/57 |
| 4 | GraphHopper 11.1 | 46/57 (11 off target) |

## Category 6 — route quality

All valid routes of every engine had the shortest length found for their case
(median 1.0×, none over 1.2×). These short junction movements barely test route
quality; longer journeys are needed before ranking it (run C routes).

## Category 8 — junction turn instruction

| Rank | Engine | Correct / judged | Wrong |
|---:|---|---:|---|
| 1= | DMN | **36/36** | — |
| 1= | OSRM | **36/36** | — |
| 3 | Valhalla | 35/36 | 1 straight-on movement announced as "exit right" (turn-7839680152) |
| 4 | GraphHopper | 26/30 | 4 turns of 60–120° announced as "continue" (6 not judged: route differs) |

## Category 9 — roundabout exit number (v1.1: every exit a car may leave by counts)

| Rank | Engine | Correct / judged | Wrong | Not judged (route differs) |
|---:|---|---:|---|---:|
| 1 | DMN | **21/21** | — | 0 |
| 2 | Valhalla | 20/20 | — | 1 |
| 3 | GraphHopper | 15/15 | — | 6 |
| 4 | OSRM | 17/20 | 3: counted without service-road exits | 1 |

Ranked by correct answers on the cases each engine was judged on; engines with
fewer judged cases rank below those with more at the same accuracy.

## Category 11 — route line on the road

| Engine | Median worst point off the road | Cases with a point over 5 m off |
|---|---:|---:|
| OSRM | 0.04 m | 0 |
| Valhalla | 0.04 m | 0 |
| GraphHopper | 0.05 m | 11 (its off-target cases) |
| DMN | not applicable: draws the OSM road points themselves | — |

## Timing (not ranked)

Medians: OSRM 1.1 ms, Valhalla 19 ms, GraphHopper 92 ms (warm query); DMN 205 ms
includes the clip import (Category 7, run D).

## Issue register

| Case | Engine | Issue | Status |
|---|---|---|---|
| roundabout-127572573-exit2 | DMN | Refused the instruction because the exit road had uncertain access | **Fixed** (`4abf5bf`, owner-approved): instructs on uncertain-access roads the route uses |
| roundabout-3994228-exit3, roundabout-58425651-exit2 | DMN | Did not count service-road exits | **Fixed** (`4abf5bf`): owner chose to count every exit |
| same three cases | OSRM | Counts exits without service roads | Competitor, recorded |
| 4 turn cases | GraphHopper | Real 60–120° turns announced as "continue" | Competitor, recorded |
| turn-7839680152 | Valhalla | Straight-on movement announced as "exit right" | Competitor, recorded |

## Proposed DMN improvements

None outstanding for categories 5, 8, 9 and 11 on this cohort. Category 6 needs longer
journeys (run C).
