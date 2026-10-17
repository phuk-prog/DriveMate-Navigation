# Category 1 of 21 — Map data and directed road graph (review only)

**Status: READY FOR OWNER REVIEW; NOT EXECUTED.** Category ID `map_data`. This is the **first** item in the current engine-only register. The current Python unit tests under this category are not a head-to-head engine comparison. Do not run them, download map extracts, dispatch workflows or edit the engine until the owner explicitly says **"Start category 1."**

## Question to answer

Given the **same permitted, version-pinned public UK road dataset**, how accurately and completely can DMN ★ and each accessible competitor engine *ingest and represent a legal motor-vehicle road graph*, with uncertainty retained? This tests graph construction and preservation of source facts **only**. Actual route choice/fastest time belongs to later routing categories; GPS, lane advice, manoeuvre guidance and Android are separate categories.

## Improved prospective cases — not executed

Propose an initial **120-case common, frozen case inventory**, subject to importer limits, accessibility and owner review before starting. Target **six bounded UK source areas** with roughly 20 disjoint, inspectable source road elements each: Greater Manchester (complex urban), West Midlands (urban/junctions), Cumbria (rural), Cardiff (Wales), Glasgow (Scotland) and Belfast (Northern Ireland). These are *prospective footprints only*: no verified individual road layouts, selections, current restrictions or exact archive availability are asserted now.

Proposed checks, recorded separately even if they share case data:

| Check | What must be judged | Required counterexamples |
|---|---|---|
| Road graph fidelity | Imported edge/node topology follows pinned source way geometry, shared vertices and travel orientation | Disconnected segments, wrong carriageway, zero-length edges |
| One-way and access tags | Preserve source-way direction and legal/unknown access classification | Reverse one-way, private/bus-only roads, contradictory/missing vehicle tags |
| Turn restrictions | Preserve explicit restriction relations without inventing legal turns | No-U-turn, prohibited left/right, via-way restrictions, unsupported conditional/time rules |
| Junction and roundabout topology | Graph contains source arcs/connectors rather than simplifying unsafe shortcuts | Roundabout exits, multi-arm junction, incorrect connector across divided road |
| Bridge/tunnel separation | Preserve grade and nonconnecting crossings unless actually joined by a source node | Overpass, underpass, side-by-side segments |
| Vehicle-road classifications | Preserve relevant road class, links, slip/service roles and direction | Slip road/Main road mistaken for one edge; motorway/service road split |
| Source attributes and unknowns | Preserve/source-report lane-turn/speed/entrance attributes where applicable, without asserting absent information | Missing speed/lanes, signed exceptions, conditional restrictions, unknown access |
| Consistency and robustness | Same fixed input -> reproducible graph; reject corrupt/partial data rather than silently guess | Dangling source IDs, duplicate/malformed OSM tags, truncated extract; separately labelled defensive controls |

The **source agreement** verdict is only **PROVISIONAL**, even if all 120 source-derived cases succeed. Independent current lawful road truth, construction updates and signs should be separately corroborated where feasible and are otherwise **UNKNOWN**, not passed. Test cases dependent on unsupported conditional-access/turn semantics may be **NOT_JUDGED** until the full condition is represented; never strip restrictions to award passes.

## Fair engine applicability — determine before starting

Potential executable candidates: **DMN ★, OSRM, Valhalla, GraphHopper, openrouteservice, BRouter, Itinero and Routino**. Other requested families such as OsmAnd, Organic Maps, HERE, Mapbox, TomTom, Google Maps and Waze need category-specific, permitted graph-inspection interfaces; many APIs expose final routes but not a comparable internal directed road graph. **No one is treated as tested or scored yet.** Existing older engine runs are *context*, not this proposed full common category.

For each candidate, record engine version, motorcar profile, snapshot/maps source, licence/cost, output/inspection route, access to directed graph facts, supported restrictions and any normalization losses. **Do not infer graph-import compliance from a successful shortest-path request** or a different-map proprietary service. If no equivalent graph inspection exists, label unsupported rather than score zero. For different maps, separate a data-source quality study from the same-input engine importer cohort.

## Proposed scorecard and priorities (frozen before a run)

Main ranking **highest to lowest**: correctly represented judged source facts / identical eligible common-case count, with safety-critical wrong-direction/illegal-turn representations reported first in a separate fail register. Equal counts share rank. Show **correct / wrong / withheld / unsupported** for each subcheck and overall only when all engines share the same eligible cases; preserve the full and partial cohorts separately.

Separate informational measurements: graph build seconds and peak resident memory (same CI worker/profiles/snapshot), graph/map bytes and source freshness. Do **not** combine resource use with correctness or compare different-worker/hardware times as a speed ranking. The actual route-computation milliseconds will be tested in **Category 7**, not here.

For each failing DMN fact, record exact OSM way/relation/segment IDs, original source tags, import output, competing engine outputs if equivalent, whether current legal truth is independently confirmed, cause hypothesis and priority.

## One category, one review gate

On an explicit owner **"Start category 1"**: (a) freeze exact eligible inputs, ground-truth labels and budgets; (b) audit and execute the available compatible engines sequentially; (c) produce one full/partial categorized ranking with exact failures and measured resource costs; (d) list DMN improvements **last**; (e) STOP and ask the owner before fixing anything or looking at Category 2.

**Current state: PROPOSED, 0 of the new 120 candidate cases selected/run/scored; no workflows triggered by this review.**
