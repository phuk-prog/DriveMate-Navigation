# MAP-001 v2 — Category 1 improvement + fresh competitor routing proxy

**16 October 2026 · RESEARCH ENGINE ONLY · Complete / awaiting owner decision.**
Original [MAP-001 v1 results](MAP_001_RESULTS.md) are immutable.
Executed [MAP-001 v2](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38938343380) successfully with [all 120 source cases, SHA-256 manifest and individual verdicts](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38938343380/artifacts/12061463540). Separately, the [fresh six-engine ROUTE-004 source one-way functional proxy](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38938343146) finished **SUCCESS** for five executable references plus DMN ★. This is only a **narrow functional proxy**, not an equivalent competitor internal graph audit.

## What improved in the executable Category 1 harness

- Retains *connected from/via/to OSM ways and turn restriction relations* around the selected way, rather than stripping linked relations out of every case. Covers allowed one-way/two-way edges and source-derived explicit forbidden turn pairs for supported simple node-via restrictions.
- Independently derives motorcar access from source tags and endpoint barriers, and checks this status alongside directed geometry. Never assumes a conditional restriction is universally valid.
- Distinguishes source agreement from **SAFE_WITHHELD**, **NOT_JUDGED**, and **FAIL**; stores the exact per-way issue type and source hash. No source-map mismatch was silently removed.
- Does not modify the DMN road importer or its conservative rejection thresholds. No Android app code or navigation behaviour changed.

Important **before/after limitation:** v2 downloads the same six public UK *area boxes* via the OSM API, but at a **new time**, so v1 and v2 are not a same-input paired improvement in DMN quality. The improved test instrumentation is real; the 96 vs 107 change is not a proven 11-case navigation-engine upgrade.

## Full v2 source-graph source agreement

| UK sample area | Source agreement pass | Safe withheld | Not judged | Total |
|---|---:|---:|---:|---:|
| Manchester | 18 | 0 | 2 | 20 |
| Birmingham | 20 | 0 | 0 | 20 |
| Carlisle | 18 | 0 | 2 | 20 |
| Cardiff | 20 | 0 | 0 | 20 |
| Glasgow | 16 | 3 | 1 | 20 |
| Belfast | 15 | 5 | 0 | 20 |
| **TOTAL** | **107** | **8** | **5** | **120** |

**0 wrong source matches among 107 judged cases**. **11 passing cases retained mapped restriction relations; 10 contained at least one source-derived prohibited-turn pair.** This audit does not independently verify current UK road laws, driving directions, all lanes, all possible roundabouts or all graph edges; verdicts are **provisional OSM-source agreement only**.

## Actual separate six-engine comparison (source one-way *route output* only)

Shared frozen public Manchester map checksum starts `75701973da`, manifest starts `5987601174`. Each engine executed the same 12 route queries (six public one-way source ways, one permitted-direction and one reverse-direction query per way).

| Proxy rank | Actually executed engine | Passed / 12 | Failed | Unresolved |
|---:|---|---:|---:|---:|
| 1= | **DMN ★** | **12/12** | 0 | 0 |
| 1= | **OSRM** | **12/12** | 0 | 0 |
| 1= | **Valhalla** | **12/12** | 0 | 0 |
| 1= | **GraphHopper** | **12/12** | 0 | 0 |
| 1= | **openrouteservice** | **12/12** | 0 | 0 |
| 1= | **BRouter** | **12/12** | 0 | 0 |

Executed and artifact links:
[OSRM](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38938343146/artifacts/12061114480) ·
[Valhalla](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38938343146/artifacts/12062550197) ·
[GraphHopper](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38938343146/artifacts/12061997402) ·
[openrouteservice](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38938343146/artifacts/12061709780) ·
[BRouter](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38938343146/artifacts/12061224084).
Each artifact also carries a freshly run DMN baseline and common manifest.

**Absolutely no overall Category 1 ranking** is justified: route behaviour does not expose full engine road graphs, input map scope differs from MAP-001 v2's six regional extracts, and six source-derived one-ways do not adjudicate a nation's signs/current laws. Calculation time observations are stored but DMN's local in-process Python and external HTTP plus different GitHub workers are NOT_COMPARABLE as a speed leaderboard.

Itinero, Routino, OsmAnd, Organic Maps and commercial HERE/Mapbox/TomTom/Google Maps/Waze did **not** execute this proxy. Never assign unsupported engines zero or fill them with fabricated performance.

## Findings — separate DMN, test harness, source, and competitor issues

| Priority | Type | Evidence and relevant cases | Correct next action (NOT yet made) |
|---|---|---|---|
| High | **DMN capability / safe rejection** | Eight conditional cases: Glasgow (3) and Belfast (5). Importer rejects unsupported time/condition-dependent access. | Design a complete vehicle/date/time-zone-dependent evaluator with unknown fallback. Never assume an unsupported condition means unrestricted access; test independently before enabling. |
| High | **Test-source gap** | Three referenced relation member ways missing from bounding-box source: Carlisle `23467606`, `1101726808`; Glasgow `4627827`. | Freeze complete relation closure (all referenced ways, via nodes, turn context) without losing data provenance; rerun only eligible cases under a new version. |
| High | **Importer or test-context ambiguity** | Manchester `155729945` and `246124643`: mapped relation references a missing/non-drivable manoeuvre under prototype parser. No source traversal was confidently approved. | Inspect relation member tags/vehicle eligibility and importer assumptions; distinguish irrelevant modes, partial source, and actual missing legal movement before changing engine. |
| High | **Cross-engine harness limitation** | Other engines expose route outputs, while MAP-001 asks for equivalent internal directed edges/access/turn cost. | Build and audit graph-inspection adapters, starting with Valhalla `/locate` or graph tiles, OSRM vector graph tiles and GraphHopper core graph iterators; verify matching way ID, car access, turns, graph snapshots and licence before scoring. |
| Medium | **Coverage gap** | Few small source areas, no guaranteed quotas for grade-separated underpass topology, specific roundabout geometries, complex via-way restrictions, and lane/speed-source preservation. | Freeze targeted actual UK cases and dated independently corroborated reference records; preserve source-vs-real-road categories separately. |
| Medium | **Fairness limitation** | MAP-001 v1 vs v2 source snapshots are not identical and competitors not run on v2's own 120 inputs. | Reuse a single *frozen* input manifest/archived public source across every engine before treating results as head-to-head. |

**No confirmed dangerous incorrect road movement** surfaced in the judged source-fact or one-way proxy samples; this does not prove any engine is safe across UK roads.

## Status / next approval gate

**Category 1 research retest completed.** No DMN production code or default GPS/navigation decisions changed; no app, APK, merge or Category 2 execution. Await owner's decision before further MAP-001 importer changes or cross-engine graph adapter implementation; next navigation category has not started.
