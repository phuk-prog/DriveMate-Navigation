# DMN navigation-engine test categories — what the actual engine needs

**Official 21 existing categories retained**, with the same IDs/order. Category 21 is **benchmark quality infrastructure** and must never be scored as driver navigation performance. No Android UI, Bluetooth, voice synthesis, APK or application visuals are part of this programme. Only one category starts at the owner's explicit command.

Every category's primary check uses identical *applicable* cases for DMN ★ and individually version-pinned reference engines, with provenance, independent lawful truth vs provisional OSM, frozen case IDs, actual passed/failed/withheld counts and safety-critical fail details. Never fill unsupported external engines with zeros.

| # | Category | What must actually be tested | Primary reported measurement |
|---:|---|---|---|
| 1 | **Map data and road graph** | Directed edges, one-ways, connectivity, barriers, car access, turn relation preservation, separate overpasses, roundabout/source topology, unknown/conditional tags | Source-correct / judged graph facts, omitted edges/turns, withheld sources |
| 2 | **Road legality and restrictions** | Actual permitted vehicle movements, no/only-turn, no-U-turn, conditional/time restrictions, closed/private roads, reversing across one-ways | Legal movements / independently adjudicated cases, illegal suggestions |
| 3 | **GPS positioning and road matching** | Same GNSS trace in main/service/slip roads, parallel carriageways, junction splits, roundabouts, low speed | Correct road/carriageway / independently referenced fixes; confident wrong vs withheld |
| 4 | **Bad GPS and recovery** | Underpasses, tunnels, urban multipath, indoor starts, signal dropout, stops and contradictory fixes | Incorrect snaps, safe withholding, verified recovery time/frames |
| 5 | **Route calculation and validity** | Start and destination, directed path continuity, alternatives, unavoidable gaps, correct access/restriction application | Legal reachable routes / judged queries, missing/unreachable false outputs |
| 6 | **Route quality and preferences** | Fastest, shortest legal, reliable, easy-turn, avoid options, unnecessary detours, local vs motorway | Travel-time/distance regret vs applicable verified baseline, mode-specific quality |
| 7 | **Route calculation speed** | Same case workload, cold/warm routing, valid responses, equivalent API boundary, same worker/machine | Valid route p50/p95 milliseconds and setup separately; no mixed-worker ranking |
| 8 | **Junction choices** | Correct turn, legal branches, T/crossroads, slip merges, immediate guidance after movement | Correct maneuvers / independent junction cases; illegal turns |
| 9 | **Roundabout navigation** | Exit count, path direction, multi-ring/spiral layouts, before/through/after guidance | Correct exits / adjudicated maneuvers, wrong/unsafe movements |
| 10 | **Lane decisions** | All lane arrows incl. combined through/turn, legal selected lane, best lane for following turn, changing lane safely | Correct lane advice / independently known lane diagrams |
| 11 | **Route-line adherence** | Every route and turn point on the intended mapped geometry, dual carriageway side, no corner cutting | Maximum / p95 lateral error in metres plus off-road decisions |
| 12 | **Rerouting** | Missed turns, road departures, legal reconnect, no repeated wrong-road loops, adaptive countdown | Correct reroutes / incident; detection and new-route milliseconds |
| 13 | **Instruction decision and timing** | Approaching, turn-now, post-turn, prompt duplication, speed-aware distance, uncertain GNSS | Correct prompt windows / events, late/wrong/duplicated cues |
| 14 | **Traffic and closures** | Map-matched incidents, dynamic avoid/replan, source age, unavailable/false traffic, verified closure | Valid replans / measured events, stale/unsafe closure responses |
| 15 | **Speed-limit intelligence** | Per-section direction, UK mph/kmh, variable/conditional limits, crossings and source updates | Accurate limits / independently evidenced road sections, false alerts |
| 16 | **Arrival correctness** | Vehicle-accessible destination point, road/entrance side, destination approach, no premature/false arrival | Correct vehicle arrival / independent destination cases |
| 17 | **Offline reliability** | Routing, guided progress, cached maps/updates, interrupted download/restart, provenance integrity with network unavailable | Successful offline journeys / cases, corrupt/absent data safety |
| 18 | **Reliability and safety failures** | No fabricated route, fail closed on unknown laws, stale/invalid updates, GPS race/conflicts, bad map source | Dangerous false positives, crash/hang/rejection counts |
| 19 | **Resource efficiency** | Import/build bytes and time, live navigation CPU/RAM, GPS processing overhead, battery proxy, map size | Median/p95 CPU time, peak RAM, data bytes; energy only where genuinely measured |
| 20 | **End-to-end engine journey** | Start navigation engine -> route -> GNSS -> junction/roundabout -> wrong turn/reroute -> arrival | Completed fully valid navigations / frozen real-road replays |
| 21 | **Reference adapter and comparison integrity** | Engine version/rights, identical input profiles, shared cases, valid timing and rank rules, missing interface detection | **Benchmark quality gate — NOT a navigation-performance rank** |

## Cross-category test rules

- Test on *proper UK roads* using the same verified source snapshot and identical start/stop points for all applicable engines, while maintaining independently corroborated legality, exact source date and confidence. Manchester and the owner's named difficult roads should be included when applicable, not substituted with fabricated real-world claims.
- Include realistic adverse GPS, junctions, rounds, turns and U-turns. Preserve separate analytical/synthetic adversarial safety suites but never report them as live UK observations.
- Every category has a single priority scorecard with exact `correct/total`, `wrong`, `withheld`, source-truth status, per-case failures, processor/setup timings and the eligible engine cohort. Only compare like-for-like outputs.
- **Safety results outrank completeness** when prioritising issues. Speed is never considered faster if the returned path is wrong/illegal. The safety failures and availability failures must be separate.
- Maintain DMN original and experimental GPS matchers side by side without disabling either. Do not turn on a variant automatically.
- Competitor engines are relevant if their functionality is truly accessible; OSRM, Valhalla, GraphHopper, openrouteservice, BRouter and other compatible open engines are candidates, not untested winners. Paid/API-restricted engines require authorised access and compatible sampling.
- After a completed category, show **(a) results and eligible high-to-low rankings, (b) distinct engine issues vs test issues, (c) proposed improvements last**. STOP for owner review before fixes or starting the next category.

## Current completed / waiting status

Category 1 MAP-001 v2 complete. See [executed MAP-001 v2 results](MAP_001_V2_RESULTS.md) and original [v1](MAP_001_RESULTS.md). Category 2 remains **NOT STARTED**.
