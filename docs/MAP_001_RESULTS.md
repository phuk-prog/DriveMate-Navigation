# MAP-001 — Category 1 map data and directed road graph: executed result

**Date:** 16 October 2026. **State:** COMPLETED / PROVISIONAL / STOP FOR OWNER REVIEW.
Source revision `8880b6109cf3886dbe9e81ca54c38b57e0d4aff4`; [GitHub Actions execution](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38936452842) concluded **SUCCESS**, with [the full 120 individual case verdicts and frozen source SHA-256 manifest](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38936452842/artifacts/12060209997). This was an owner-authorized run for **Category 1 only**; it did not exercise other navigation categories or the Android app.

## Actual scope of first execution

Downloaded six **bounded live public OpenStreetMap API extracts**, with twenty distinct motorcar-source OSM ways selected in each area; froze source byte hashes and case IDs **before** judging against the DMN research importer. Original raw downloads were not uploaded. Outputs and sample road positions have **provisional source-data truth only**—not independent road-law, sign, GPS, or surveying verification.

**Important coverage qualification:** This run's executable per-way oracle tests **directed edge IDs, one-way/two-way direction, graph endpoint orientation, and positive segment length**. It does **not yet measure complete motorcar access status, turn-restriction relation legality, grade-separated connectivity, every roundabout, conditional road rules, lane/speed attributes, source age accuracy or whole-region graph representation**. Each source way was extracted into a single-way graph for this specific assay. A green case therefore cannot certify all Category 1 requirements.

## Actual DMN ★ source-geometry scorecard

| Area | Judged source-match pass | Detected mismatch | Not judged | Selected cases |
|---|---:|---:|---:|---:|
| Manchester | 14 | 0 | 6 | 20 |
| Birmingham (West Midlands) | 15 | 0 | 5 | 20 |
| Carlisle (Cumbria) | 18 | 0 | 2 | 20 |
| Cardiff (Wales) | 20 | 0 | 0 | 20 |
| Glasgow (Scotland) | 16 | 0 | 4 | 20 |
| Belfast (Northern Ireland) | 13 | 0 | 7 | 20 |
| **Total** | **96** | **0** | **24** | **120** |

The 96 evaluated directed-geometry cases all agreed with the **same OpenStreetMap source** used to generate their expectations; there were no recorded wrong orientations/edges **within those evaluated conditions**. This is **96/96 judged**, **not 120/120** and **not 96/120 verified road/legal accuracy**.

### Exact unresolved case cause counts (from artifact)

- **18 of 24** — `attached_turn_relation_omitted_from_isolated_case`. The source road participates in a mapped turn restriction relation, but the present single-way graph probe cannot retain enough surrounding roads/via context to judge it. **TEST-HARNESS ISSUE**. Do not interpret an isolated-way pass as correct turn legality.
- **6 of 24** — `conservative_source_rejection` with the message **conditional tags are unsupported** (one Glasgow, five Belfast samples). **DMN FEATURE/COVERAGE GAP**, also requires a time/vehicle-conditioned independent reference. These six were **safely withheld**, not silently accepted.

No confirmed false direction or incorrect endpoints were found among tested eligible ways. No unsafe real-world routes were executed or independently adjudicated.

## Competing navigation engine applicability — NO head-to-head graph ranking yet

**DMN ★:** actually executed this 120-case graph assay.

**OSRM, Valhalla, GraphHopper, openrouteservice, BRouter, Itinero, Routino, OsmAnd and Organic Maps:** none has yet provided a configured **equivalent internal per-way directed graph-fact inspection adapter** for these six source extracts. Route calculation or snapping output is not equivalent graph import truth. They are **NOT_RUN / INTERFACE_NOT_COMPARABLE for MAP-001**, not failures or zeroes.

**HERE, Mapbox, TomTom, Google Maps and Waze:** no authorized/available comparable internal graph fact API. **NOT_RUN / NO_AUTHORIZED_GRAPH_INSPECTION_INTERFACE**. No paid provider calls made. The earlier ROUTE-004 mapped one-way routing ranking is a different category and has not been reused or presented as a Category 1 result.

**Main comparable engine ranking: NOT AVAILABLE** (one eligible executed engine only). Do not show DMN as rank #1 solely because opponents were not executed. No cross-engine graph processing speed comparison is available.

## Issues found — deliberately separated

| Priority | Issue type | Exact observation | Proposed action (not performed) |
|---|---|---|---|
| 1 | **Test harness** | 18/120 way probes lack associated turn-restriction relations and adjacent roads; cannot judge turn graph correctness | Freeze full relation+referenced-way+node neighbourhoods and independently examine via-node and via-way restrictions; reject unknowns conservatively |
| 1 | **Comparator harness** | No equivalent public external directed graph inspection across the requested engines | Investigate graph inspection adapters for legally accessible open-source engines; run a new shared case contract only where identical graph facts can be exposed |
| 1 | **DMN functionality / coverage** | 6/120 conditional restriction-tagged ways fail closed | Design actual vehicle/time/date-conditioned access evaluation, with dated reference evidence; never simply remove tags or treat them as open |
| 2 | **Test harness** | No selected roundabout samples and no source-backed overpass, road-level or motorway-link graph audit, despite broader design targets | Create explicit quotas backed by the actual source inventory and separate coverage labels; don't silently substitute ordinary roads |
| 2 | **Test harness** | Source access classifications and full turn restrictions were not independently asserted in successful orientation cases | Add explicit access per-directed-edge expected/actual comparisons and complete-movement graph checks |
| 2 | **Test coverage** | Six small city-centre sample footprints do not establish full England/Scotland/Wales/Northern Ireland map completeness or current road truth | Scale geographic and rule diversity with bounded published source extraction, independent verification and source dates |
| 3 | **Methodology** | Prototype importer has a 6 MB per-extract input limit | Use bounded provenance-tracked regional tiles without silently dropping dependent restriction data, or design a verified streaming import contract |

## Next action / strict owner gate

**STOP after Category 1.** Show this report and let the owner approve either (a) a **Category 1 test-harness correction and new equivalent competitor graph adapters** followed by fresh comparable tests, or (b) proceeding to a separate Category 2 review. No Category 2 execution is authorized. Do not modify DMN routing/GPS/default rules, remove any option, merge into production or release an APK.
