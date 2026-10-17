# ACCESS-001 — no-car roads, route-level, four engines (Category 2)

> **Latest:** seven-engine results (adds openrouteservice, BRouter, OsmAnd) are in
> [SEVEN_ENGINE_SCOREBOARD.md](SEVEN_ENGINE_SCOREBOARD.md); DMN scores unchanged. The tables
> below are the earlier four-engine runs.

**DMN: 44/44 judged closed-road cases legal, 0 routes along a road closed to cars.**
Map-derived (OpenStreetMap tags in a hashed snapshot), not independent UK road law.

## Runs and frozen inputs

- Result of record: [run 39039633092](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39039633092),
  revision `2d9c3f9` (after the owner-approved DMN fix below), all four engines freshly rerun.
- Before the fix: [run 39039003647](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39039003647),
  revision `ceb3c76`. Scores: [before](../references/category2-runA-before-fix-20261017.json),
  [after](../references/category2-runA-after-fix-20261017.json).
- Source: pinned Greater Manchester OSM snapshot `2a8ef8e1…` (data/turn001-snapshot).
- Cohort `config/access001-cohort.json`: 139 road ways cars may not use, 15–400 m, both
  ends on a car road, drawn per kind in sha256 order before any engine ran.
  `config/access001-prepared.json`: 3 km clip per case (roads, restrictions, barriers),
  clip SHA-256 frozen; no-route retried on a 7.5 km clip; at most 12 testable per kind.
- Test: car route from the car road before the way to the car road after it. Every
  route is also audited against one-way, turn restriction, closed barrier and other
  closed-road rules. DMN control (tested road opened to cars) marks discriminating cases.
- Contract history (all before any reported result): v1 0.94 km clips → v1.1 5 km
  clips (owner: several miles wide) → v1.2 3 km clips, 12 per kind (owner: catch every
  issue without long runs).

## Ranking — closed roads (44 judged cases, same cases for every engine)

| Rank | Engine | Legal pass | Drove a closed road | Other rule breaks | Off target | No route |
|---:|---|---:|---:|---:|---:|---:|
| 1 | DMN | **44** | 0 | 0 | 0 | 0 |
| 2 | Valhalla 3.9.1 | 42 | 0 | 0 | 2 | 0 |
| 3 | OSRM 5.27.1 | 41 | 0 | 0 | 3 | 0 |
| 4 | GraphHopper 11.1 | 27 | 0 | 0 | 17 | 0 |

By kind (legal pass / 12, busway / 8): DMN bus gate 12, busway 8, no cars 12,
pedestrian 12. Valhalla 11, 8, 11, 12. OSRM 11, 8, 10, 12. GraphHopper 8, 5, 9, 5.
Discriminating cases (the unblocked route uses the road): 20 closed + 7 restricted.

## Reported, not judged — private / access-only roads (21 cases)

| Engine | Used road | Avoided | Other |
|---|---:|---:|---|
| DMN | 4 | 15 | 2 endpoint withheld by policy |
| OSRM | 5 | 15 | 1 off target |
| Valhalla | 3 | 16 | 2 off target |
| GraphHopper | 7 | 3 | 9 off target, 2 no route |

Whether through traffic may use a private or access-only road depends on who is
driving; OSM alone cannot say, so these are not scored.

## Category 5 (separate): route returned on the exact test segments

DMN 63/65 (2 withheld by policy), OSRM 61/65, Valhalla 61/65, GraphHopper 37/65.

## Timing (not a ranking)

Medians: OSRM 0.7 ms, Valhalla 16.5 ms, GraphHopper 85 ms (warm query); DMN 594 ms
includes importing the whole clip each time, so it is not comparable (Category 7).

## Issue register

| Case(s) | Engine | Issue | Status |
|---|---|---|---|
| 765322434, 868019400, 7993379 (7.5 km retry) | DMN | One via-way turn rule with members not joined end to end made DMN reject the whole clip | **Fixed** (owner-approved, `2d9c3f9`): blocked per relation (`disconnected_via_way_blocked`), never permits a banned move |
| 1135461207, 559432689 | DMN | Start/finish on a road DMN marks closed: withheld by policy | By design (restricted kinds only) |
| 17 closed cases | GraphHopper | Route did not start/finish on the exact segments | Harness/adapter snapping; not a rule break |

## Follow-up

Both proposals below were approved and done in `436d548` (unknown rule values and
multi from/to rules now fail closed per relation). Fresh four-engine rerun
[39041918552](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39041918552):
scores unchanged (DMN 44/44, ONEWAY-002 48/48, no rule breaks).

## Proposed DMN improvements (as originally proposed)

1. Other importer checks still reject a whole map for one bad relation ("unsupported
   turn restriction" value; `only_` with several from/to ways). Handle them per
   relation like the fix above.
2. DMN timing includes the clip import; measure warm route time separately before any
   speed comparison (Category 7, run D).
