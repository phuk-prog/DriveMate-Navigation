# DMN — owner-controlled, one-category-at-a-time comparison programme

**Status: ALL CATEGORY EXECUTIONS PAUSED / NOT STARTED under this protocol.** This is a *prospective test-design improvement*, not a new execution result. Existing historic run artifacts remain historic evidence and are not re-labelled. Scope: DMN navigation engine only; never run the Android app, emulator, UI, audio, APK or private `phuk-prog/DriveMate`.

## Required sequence and hard approval gates

1. **Review only:** Show the owner the next category's specific behaviours, real-UK-road cases, how each case can be independently judged, eligible competitor engines, exact measures, reasonable budgets and rankings, safety counterexamples, missing methods and constraints. **Do not launch any CI, test, benchmark, engine process, map download or source-changing implementation during this step.**
2. **Owner starts:** Run **only** if the owner explicitly says **"Start category N"** or unambiguously approves starting the currently reviewed named category. "Next", "continue", or approval to improve the test plan alone **does not authorize execution**. Do not begin the next category after finishing a previous one. Ask a brief clarification if category number is ambiguous.
3. **Freeze before execution:** Pin map archive/hash, bounded geographical case manifest, independently corroborated truth versus provisional OSM truth, engine version/profile, source licensing, common applicable case IDs, scoring definitions, pass/fail/unknown rules and budgets. Save hashes and exact provenance. Real roads in scored main UK cases; synthetic controls may run as a separately labelled safety suite, never replace real-road tests.
4. **Run once and separately:** Check existing active/queued jobs first, cancel/avoid overlaps only when authorized, reuse cached source assets, and use bounded CI workers. Attempt DMN ★ plus each *actually available and applicable* licensed reference on identical complete frozen inputs and equivalent interfaces. Mark inaccessible/unsupported engines **NOT_RUN / UNSUPPORTED** with reasons, not failures or passes. Never spend money or accept new licence conditions without owner authorization.
5. **Report category results only:** Full common cohort vs independently labelled partial cohorts, highest-to-lowest ranking by the category-specific primary valid metric, per-engine passed/failed/withheld counts, exact failures and cases, times in comparable ms only, setup/data costs separated, evidence-level badge **VERIFIED / PROVISIONAL / UNKNOWN**, and remaining category gaps. Original unit contracts alone do not count as a competitor score.
6. **Recommendations last, STOP:** Investigate failures and propose possible DMN improvements ranked by evidence and safety impact. **Do not implement behavioural fixes, turn on an optional GPS rule, merge, retest competitors, or move to the next category without a separate owner approval.** After an approved fix, rerun all relevant frozen common-case DMN and actually applicable competitors, preserving old measurements and owner gates.

## Ordered category queue — exactly the current 21 engine categories

Every category below is **AWAITING OWNER START** for a new head-to-head test, even if historical unit tests or older narrow comparisons exist.

| Order | Category | Current next action |
|---:|---|---|
| 1 | Map data and road graph (`map_data`) | Review [Category 1 design](DMN_CATEGORY_01_MAP_GRAPH_TEST_DESIGN.md); WAIT FOR START |
| 2 | Road legality and restrictions (`legal_routing`) | Do not prepare/run its executable cohort until category-specific review |
| 3 | GPS positioning and road matching (`gps_matching`) | Do not prepare/run its executable cohort until category-specific review |
| 4 | GPS signal loss and recovery (`gps_loss_recovery`) | Do not prepare/run its executable cohort until category-specific review |
| 5 | Route computation and validity (`route_computation`) | Do not prepare/run its executable cohort until category-specific review |
| 6 | Route quality and preferences (`route_quality`) | Do not prepare/run its executable cohort until category-specific review |
| 7 | Route calculation speed (`route_calculation_speed`) | Do not prepare/run its executable cohort until category-specific review |
| 8 | Junction turns and maneuvers (`junctions`) | Do not prepare/run its executable cohort until category-specific review |
| 9 | Roundabout exits and paths (`roundabouts`) | Do not prepare/run its executable cohort until category-specific review |
| 10 | Lane counts and next-turn guidance (`lanes`) | Do not prepare/run its executable cohort until category-specific review |
| 11 | Route line and turn-point road adherence (`route_line_adherence`) | Do not prepare/run its executable cohort until category-specific review |
| 12 | Wrong turns and rerouting (`rerouting`) | Do not prepare/run its executable cohort until category-specific review |
| 13 | Navigation instructions and timing (`instruction_timing`) | Do not prepare/run its executable cohort until category-specific review |
| 14 | Traffic, closures and dynamic replanning (`live_traffic`) | Do not prepare/run its executable cohort until category-specific review |
| 15 | Road section speed limits and alerts (`speed_limits`) | Do not prepare/run its executable cohort until category-specific review |
| 16 | Correct arrival and approach side (`arrival`) | Do not prepare/run its executable cohort until category-specific review |
| 17 | Offline routing, maps and updates (`offline_reliability`) | Do not prepare/run its executable cohort until category-specific review |
| 18 | Failure handling, integrity and safety gates (`failure_handling`) | Do not prepare/run its executable cohort until category-specific review |
| 19 | Memory, CPU, energy and map size (`performance_resources`) | Do not prepare/run its executable cohort until category-specific review |
| 20 | Complete navigation-engine journey (`integrated_end_to_end`) | Do not prepare/run its executable cohort until category-specific review |
| 21 | Competitor adapters and comparison integrity (`reference_adapters`) | Do not prepare/run its executable cohort until category-specific review |

## Universal stronger test specification — distinct scorecards, not a global winner

- **Input matrix:** UK city/urban, rural, motorway, ring road, divided carriageway, service/slip roads, roundabouts, narrow/complex junctions, tunnels/bridges/grade separation, one-ways, prohibited manoeuvres, conditional restrictions, stationarity/bad GNSS and destination approaches **as applicable to this named category**. Include multiple geographically distinct UK places across England, Scotland, Wales and Northern Ireland where applicable; label independently verified evidence versus generated/source-map cases. Never assume all datasets/services cover the same four nations.
- **Case sheet:** ID, category, location/general area, input OSM snapshot, actual road evidence reference/date if available, exact input/expected output, validity and unknown conditions, route/profile, relevance to specific engine adapters, and safety-critical indicator. Do not score a provider against an interface it cannot lawfully provide.
- **Comparator audit:** DMN ★; candidate families OSRM, Valhalla, GraphHopper, openrouteservice, BRouter, Itinero, Routino, OsmAnd, Organic Maps, HERE, Mapbox, TomTom, Google Maps and Waze **only if** a permitted comparable engine/API exists, configured, available and applicable to this category. These are research targets, **not** assertions of working adapters. Do not collapse Google Maps and Waze or different engines into one score.
- **Metrics:** valid passes / complete common frozen judged cases, failed/unsafe cases, withheld/unknown, measured output error in domain units, missing evidence, per-case exceptions. Set ranking direction/ties in advance. For route calculation speed, median/p95 ms over valid routes on the **same worker, map/profile, case set and interface boundary**, noting sample size, cold/warm and setup. Never rank mixed in-process Python with external HTTP from different hosts by speed. For rerouting, correctness and route compute time are separate rankings.
- **Scoring restrictions:** no automatic 100% for unrun tests; 0-10 optional only if expressly described as derived from pass ratio; no weighted overall navigator winner. Full complete cohort separate from partial cohort, and preserve safety failures as failures. A map-derived generator edge is not independent proof of actual road law or GNSS accuracy.
- **Resource hygiene:** prepare the full shared manifest before a paid/heavy run; use small frozen road extracts sufficient for coverage, strict bounded retry/timeout, install once/use cache, run heavyweight references sequentially. Add targeted adversarial case types as evidence demands without silently changing a frozen benchmark after results.
- **Before/after:** maintain unmodified baseline and trial variants, including both DMN GPS matchers, with separate version/commit, dates and input hash. Changes to test criteria require a *new* test version, never retroactive pass changes.

## Current gate

**Review category 1 only.** No category is started and no new category ranking is available just because this design exists. See [Category 1 readiness and proposed checks](DMN_CATEGORY_01_MAP_GRAPH_TEST_DESIGN.md). The owner will decide whether/when to start it.
