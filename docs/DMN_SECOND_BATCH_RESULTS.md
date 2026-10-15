# DMN second executable research batch — 15 October 2026

**Verified GitHub run:** [38734700233](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38734700233) (**success**) for the isolated DMN planning branch at commit `c4ebbf5eeee1880c629c46c994e463a268caa17e`; its artifact `dmn-uk-real-turn-rule-evidence` contains the ephemeral aggregate turn report (retained by GitHub for 30 days).

## Actual tests and non-results

| Evidence | Measured result | Strict interpretation |
|---|---:|---|
| Python unit/contract checks | **133 passed out of 133 run** | Unit tests for research functions, including new GPS input validation and public OSM turn-probe harness. Not 133 independent navigation feature passes |
| Public source | Geofabrik Greater Manchester OSM 2026-09-01 snapshot | Real publicly mapped UK restrictions, with contributor metadata stripped; NOT official/survey-confirmed law |
| Public restriction relations encountered | **20** | First 20 encountered until 12 judged rule cases reached |
| Eligible simple node-via relations in encountered cohort | **20** | Eligibility under test's subset limitations, not global coverage |
| Simple mapped turn-rule cases actually exercised | **12** | Mapped OSM restriction logic and DMN routing non-use; no independent legal or navigation oracle |
| Mapped forbidden incoming/outgoing turn pairs exercised | **12** | No forbidden pair traversed in the executed small subgraphs |
| Alternative legal paths found within local partial graph | **1** | Only an alternative in the restricted two-way subset; no real-world route-quality claim |
| No-route outcomes on partial graph | **11** | **UNKNOWN as full-network rerouting verdict**, not 11 complete real-world detours |
| Non-exercised/unsupported relations among considered candidates | **7** | Some local/way samples do not satisfy importer/coverage assumptions; record as gaps |
| Actual GPS/sensor observations, map matching or sensor fusion | **NOT TESTED** | New GPS-fix quality unit checks cover invalid/stale/noisy input rules only |
| Independently verified turn legality / lane correctness | **NOT TESTED** | OSM is not sufficient alone to judge what a driver may legally do at each real junction |
| External engines run in this batch | **0** | No ten-engine scoreboard or valid out-of-ten rank |
| Live Android emulator, full offline journeys, phone battery | **NOT TESTED** | Research host-only tests |

The report's source XML checksum is `b9b5ed253ef99d126b5e3f8d87074a945f3ce059fc213d5cb946158d1f0e2818`; source context `geofabrik-260901`. Individual turn IDs and road geometry were not uploaded as travel histories.

**Critical distinction:** The former 8-route [first batch](DMN_FIRST_BATCH_RESULTS.md) imported **zero** prohibited-turn pairs. The new restriction sample exercises 12 *mapped* prohibited-turn pairs. That closes only the narrow **absence-of-map-rule-test-data gap**—NOT the independent-legality, full-road-network, complex-junction/rerouting, GPS, lane guidance, actual speed limit, arrival or external-comparison gaps.

## Next action discovered from actual results

The turn probes build tiny input subgraphs containing the restriction's from/to roads and involved nodes; that is intentional for structural assertions. **11 no-route outcomes are inconclusive** about whether a proper alternate route exists outside this tiny subgraph.

The new `batch_from_real_turn_probe` converts that measured limitation into a stable proposed regression case under `NAV-042` (No-route and blocked-road fallback) without calling it a failure or pass. The follow-on executable regression must build a more complete real UK street network around selected difficult junctions, verify prohibitions independently, measure detour existence/quality, and run normal and wrong-turn replay. Include speed/position sensor faults and correct arrival when the required components exist. Add newly observed uncovered behaviors into the [adaptive programme](DMN_ADAPTIVE_TESTING.md), keep all evidence and rerun after improvements.

This batch did not touch DriveMate app production or release an APK. Current results remain **unranked**.
