# DMN — confirmed-progress GPS research results across UK regions

**Executed 16 October 2026 | Engine research only | STOP before default promotion.**

This is an actual source-code, frozen public-map replay, NOT an Android application and NOT an independent real-world positioning or lawful-road validation. Both GPS methods remain present. The original conservative DMN matcher is the sole authoritative output; the **opt-in** adjacent-fragment experiment now also has a bounded directed-progress check and remains research-only.

- [Full pinned GPS-003/UK40 and three-region execution](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38924328629) **SUCCESS**; [download per-event, per-case JSON evidence](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38924328629/artifacts/12055029313).
- [GPS-004 frozen ten-case progress safety workflow](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38924328663) **SUCCESS**. Original frozen oracle, including the historical default reversed-fragment coverage failure, preserved. These ten cases are analytical/synthetic controls, not real roads.
- [All 21 navigation-engine category checks](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38924328641) **SUCCESS**, **527/527** units passed, including **69/69 GPS matching units**. [Per-category JSON audit](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38924328641/artifacts/12055983482).
- Source revision evaluated: `0a60d9f92617806d4196c8da414d4f8f65e150cd`, research branch `codex/dmn-gps001-ranked-trial-20261015`.

## A. Fixed original UK benchmark — before, intermediate and latest

| Independently labelled experiment | Original DMN ★ | Earlier opt-in matcher | Latest opt-in directed-progress matcher |
|---|---:|---:|---:|
| GPS-003 source-generated complete streams passed | **8/24** | **24/24** | **24/24** |
| UK40 source-generated directed road fragments correct | **17/40** | **22/40** | **30/40** |
| UK40 safely withheld / unresolved | **23/40** | **18/40** | **10/40** |
| Confident wrong-generating-fragment claims | 0 observed | 0 observed | 0 observed |

**Eight** of the previously retained 18 unresolved UK40 cases are resolved in the latest opt-in replay; the **ten still withheld** remain explicit failures of required matching coverage or unknown/abstained observations, not passes. Original GPS results were recomputed on the same historical frozen inputs; no old score or oracle was overwritten. Historical documents 8/24, 17/40, 22/40 and previous 18 remain archived.

The new rule considers only an immediately forward directed successor to a recent trusted segment on the same numbered OSM way and in the same travel direction. It requires: a mapped allowed turn, exactly two time-reachable candidates (old segment and direct successor), clearly better lateral/heading residual on the successor, movement beyond reported positional uncertainty, reliable moving fix and an observation sufficiently past the road-fragment boundary. Ambiguous junctions, unrelated nearby roadways, backwards travel, implausible GPS, prohibited turns and unknown road truth remain fail-closed. The existing default matcher does not use this rule.

## B. NEW regional real UK-road geometry — independent geographic subsets

All roads in these tests are actual directed road segments from the **pinned 2026-09-01 Greater Manchester OpenStreetMap archive**; they are not invented/synthetic road networks. Each region's twelve cases were chosen from distinct incoming OSM way IDs and evaluated separately on the same observation generator and road graph for both DMN options.

| Area | Coverage | Original DMN correct | Opt-in research correct | Still withheld by research | Reverse-motion checks | Confident wrong source-edge |
|---|---|---:|---:|---:|---:|---:|
| Salford | 12 distinct OSM-way cases | 6/12 | **11/12** | 1/12 | 6/6 | 0 observed |
| Stockport | 12 distinct OSM-way cases | 5/12 | **9/12** | 3/12 | 6/6 | 0 observed |
| Oldham | 12 distinct OSM-way cases | 2/12 | **7/12** | 5/12 | 6/6 | 0 observed |
| **Total** | **36 map-derived cases** | **13/36** | **27/36** | **9/36** | **18/18 tested** | **0 observed** |

These are geographical diversification results: 36 total selected OSM-derived trajectory cases, not 36 verified independent driven trips. In these same scenarios the research matcher recovered **14 more correct source-fragment matches** while introducing no confidently wrong generating-source-edge match. Its remaining nine withheld cases are not labelled correct. Each reverse-motion control also reported no confident claim on the same edge when position moved backwards in the generated scenario; this is not proof against all illegal U-turns or real GNSS disturbances.

**Important conservative source exclusions:** The bounded OSM importer cannot safely evaluate conditional/time-dependent access restrictions, some complex turn relations or unrelated building/POI objects in larger extracts. The regional research runner therefore constructed a **separately hashed drivable-road-only scored subset**, excluding entire uncertain/conditional road ways and restriction-linked manoeuvres, not stripping individual restriction tags to make them appear unconditionally legal. The original archive and raw three-area extracts were left unchanged. Counts of excluded objects, raw/subset SHA-256 and per-case road IDs are recorded separately for each area in the linked artifact. The excluded roads are **NOT_JUDGED / UNKNOWN**, not silently counted as passing or legally permitted. Other DMN legality and map-data categories remain enabled and separately tested.

## C. Failure register and work still required

| Priority | Remaining problem | Evidence / next action |
|---|---|---|
| 1 | UK40 still **10/40 withheld** | Inspect which remaining candidate geometry is truly unresolved and avoid claiming a road on ambiguous trajectories |
| 1 | Three additional regions still **9/36 withheld** | Compare each actual alternative and source-map restrictions; record independent GNSS and dated roadway truth where possible |
| 1 | Real-world wrong-road safety unproven | Preserve side-by-side, slip-road, opposite carriageway, bend, tunnel/drop-out and prohibition adversarial tests; no promotion without independent evidence |
| 2 | Complex time-dependent turns were intentionally unjudged in regional GPS category | Build a verified date/time/vehicle-conditioned legal-map evaluator before treating those ways as safe/scoreable |
| 2 | No equivalent cross-engine GPS streaming cohort | Establish and run eligible GPS-matching competitors against one explicit comparable contract, not their routing accuracy |
| 3 | GPS computation and memory overhead unranked | Perform equivalent worker/interface/profiles/case-boundary runs only when a valid shared benchmark exists |

**No new baseline matcher, turn legality or confidence threshold change was enabled.** Both GPS algorithms remain available, all 21 DMN engine categories retained. There was no Android application edit, APK, release or merge. The research PR remains open; further default behavior changes require the owner's review and fresh full comparable retesting of applicable engines.

**STOP for safety review.**
