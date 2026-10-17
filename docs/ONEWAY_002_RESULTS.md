# ONEWAY-002 — wrong-way requests on real one-way roads, four engines (Category 2)

**DMN: 48/48 legal, 0 routes driving a one-way road the wrong way.**
Map-derived (OpenStreetMap tags in a hashed snapshot), not independent UK road law.
Shares the ACCESS-001 run and harness; scored separately, no combined score.

## Runs and frozen inputs

- Result of record: [run 39039633092](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39039633092),
  revision `2d9c3f9`, all four engines freshly rerun after the owner-approved DMN fix.
- Before the fix: [run 39039003647](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39039003647).
  Scores: [before](../references/category2-runA-before-fix-20261017.json),
  [after](../references/category2-runA-after-fix-20261017.json).
- Source: pinned Greater Manchester OSM snapshot `2a8ef8e1…`.
- Cohort `config/oneway002-cohort.json`: 225 one-way car roads (roundabout, major,
  residential, service; no motorways, conditional or access-tagged ways), 15–400 m,
  both ends on another car road, sha256 order, drawn before any engine ran. The first
  draw of 75 left only 32 testable (one-way roads often have no legal road arriving at
  their exit end), so it was tripled before any engine ran; the first 75 are kept.
  3 km clips, 7.5 km retry, at most 12 testable per kind.
- Test: car route from the car road at the way's exit end to the car road at its entry
  end, so the direct route drives it the wrong way. Every route is audited against all
  mapped one-way, turn, barrier and closed-road rules. Control: the tested way made
  two-way; DMN control then used it in 40/48 (discriminating cases), and the OSRM
  harness check drove it in the wrong direction (31/48 in the before-fix run; the
  scoring job passes its check in both runs).

## Ranking (48 cases, same cases for every engine)

| Rank | Engine | Legal pass | Wrong way on tested road | Other rule breaks | Off target |
|---:|---|---:|---:|---:|---:|
| 1= | DMN | **48** | 0 | 0 | 0 |
| 1= | OSRM 5.27.1 | **48** | 0 | 0 | 0 |
| 3 | Valhalla 3.9.1 | 47 | 0 | 0 | 1 |
| 4 | GraphHopper 11.1 | 32 | 0 | 1 | 15 |

By kind (legal pass / 12): DMN 12 each; OSRM 12 each; Valhalla residential 11, others 12;
GraphHopper major 8, residential 10, roundabout 6, service 9.

## Category 5 (separate): route returned on the exact test segments

DMN 48/48, OSRM 48/48, Valhalla 47/48, GraphHopper 33/48.

## Timing (not a ranking)

Medians: OSRM 1.1 ms, Valhalla 11.7 ms, GraphHopper 89 ms (warm query); DMN 206 ms
includes importing the clip, so it is not comparable (Category 7).

## Issue register

| Case | Engine | Issue | Status |
|---|---|---|---|
| 1453114721, 63662324 | DMN | Whole clip rejected for one wrongly mapped via-way turn rule | **Fixed** (`2d9c3f9`); both now PASS |
| 940577703 | GraphHopper | Avoided the tested road but drove another one-way road (way 23344472) the wrong way | Competitor rule break, recorded |
| 15 cases | GraphHopper | Route did not start/finish on the exact segments | Snapping; not judged |

## Proposed DMN improvements

None needed for one-way legality on this cohort. See ACCESS-001 for the remaining
whole-map importer rejections and the timing note.
