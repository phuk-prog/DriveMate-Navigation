# JOURNEY-001 (run B1) — real junctions and roundabouts, four engines

Categories 5, 6, 8, 9 and 11 from one shared run, each ranked separately (no total).
Truth is map-derived (hashed OpenStreetMap snapshot), not independent UK road law.

**DMN: 57/57 valid routes, 36/36 junction instructions, 18/19 judged roundabout exits.**

## Run and frozen inputs

- [Run 39043457966](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39043457966),
  revision `17e84a4`, ~5 minutes; scores in [references](../references/journey001-runB1-20261017.json).
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

## Category 9 — roundabout exit number

| Engine | Correct / judged | Unclear (service-road exit) | Wrong / refused | Not judged |
|---|---:|---:|---|---:|
| Valhalla | 20/20 | 0 | — | 1 |
| GraphHopper | 15/15 | 0 | — | 6 |
| DMN | 18/19 | 2 | 1 refused (roundabout-127572573-exit2) | 0 |
| OSRM | 17/18 | 2 | 1 wrong (same case: said exit 1) | 1 |

Not ranked: the engines were judged on different numbers of cases and two cases
depend on whether service-road exits count, which is a convention (see below).

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

| Case | Engine | Issue |
|---|---|---|
| roundabout-127572573-exit2 | DMN | Planned the route but refused the instruction: the exit road is an unnamed service road with uncertain access, and the maneuver builder refuses non-allowed edges |
| roundabout-127572573-exit2 | OSRM | Said exit 1 for exit 2 (an unnamed service-road exit comes first) |
| roundabout-3994228-exit3, roundabout-58425651-exit2 | DMN, OSRM | Counted exits without service roads (Oldmoor Road; an unnamed one-way service road); Valhalla counted them |
| 4 turn cases | GraphHopper | Real 60–120° turns announced as "continue" |
| turn-7839680152 | Valhalla | Straight-on movement announced as "exit right" |

## Proposed DMN improvements (owner approval needed)

1. Give the roundabout instruction even when the exit road has uncertain access, as
   long as the route already uses it (today the maneuver builder refuses).
2. Owner choice: should a service-road exit count when numbering roundabout exits?
   DMN skips them. Suggestion: count named service roads (for example Oldmoor Road)
   and skip unnamed ones (car parks, private accesses).
