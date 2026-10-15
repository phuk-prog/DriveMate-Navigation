# DMN first modular test batch — measured evidence, 15 October 2026

**GitHub Actions:** [run 38726726953](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38726726953) — **success**, head commit `a4c5e59522449ef1370f7bb81653886d38e77ad1`. [Artifact](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38726726953) `first-dmn-road-smoke` stores the JSON output for 30 days. This page preserves its important numbers beyond artifact expiry.

## What actually ran

| Test evidence | Confirmed result | Interpretation |
|---|---|---|
| Python unit tests | **95 passed / 95 run**, 0 reported failures | Existing routing/import/adapter checks plus four modular inventory tests; does **not** mean 95/236 navigation behaviours passed |
| Granular matrix validation | **14 summary groups, 59 separate proposed modules, 236 defined checks** | Schema/coverage contract, **not** actual functional passes |
| Public UK map smoke | **8 of 8 routable scenarios** had agreement between **DMN Dijkstra and DMN A\*** on estimated route cost | Two algorithms operating on the same bounded DMN graph, **not independent road legality** or an external-engine comparison |
| Map source | historical Geofabrik `geofabrik-260901` Greater Manchester public OSM subset, SHA-256 `b3a883ae9b7c85072d24afeee7a1079aea00c22264516a0e1e71d49221ad27d5` | Partial road sample, **not** automatically representative of complicated UK junctions |
| Import graph size | **2,023 vertices; 1,202 directed edges** | A bounded sample, not a full navigation map |
| Supported imported prohibited-turn pairs | **0** | **No exercised evidence** that a turn-restriction scenario passes |
| A* geographic heuristic used | **8/8** sample scenarios | Internal implementation detail, not accuracy ground truth |
| Measured DMN Dijkstra warm median | **0.02543 ms** | 8 tiny same-run route cases; do not extrapolate to Android |
| Measured DMN prepared A* warm median | **0.03053 ms** | 8 tiny same-run route cases, not evidence of broad superiority |
| Unprepared A* median | **2.45286 ms** | Preparation work is significant in this prototype |
| One-time A* preparation | **2.55752 ms** | Must be included separately for cold-start cost |
| External reference engines executed in smoke | **0** | No fresh 12-engine or ten-engine results produced in this run |
| Verified safe for live navigation | **false** | Do not treat this smoke as acceptance |

Unit tests and smoke were executed in the same workflow job. The 8/8 success is **algorithm agreement**, *not 8 separately independently verified legal driving journeys*. It does not establish route-length superiority, actual speed-limit accuracy, map-match correctness or safety.

## Module-level scoring after this batch

All **14 navigation quality category scores remain UNRANKED**. The new 236 atomic check definitions default to **NOT_RUN** until linked to an actual independently judged scenario/evidence row. Tests for bounded prototype source parsing and route choice ran, but this by itself does not provide a numeric user-facing category score.

In particular, this run did **not** independently judge **GPS position error, heading, sensor fusion, drift, roadside matching, actual vehicle speed, posted or variable speed limits, speeding alerts, difficult junction turn restrictions, lane data, exit numbering, reroute controller recovery, guidance speech, correct-side/entrance arrival, Android offline end-to-end performance, memory or battery**. Some capabilities already have historical evidence and implementations in *other research branches*, which must be linked and revalidated against the module catalogue before giving credit; do not conflate different snapshots and cohorts.

## Next meaningful test batch

1. **Evidence reconciliation:** link pre-existing `navigation_core`, GPS, lane, roundabout, guidance and journey test cases from `tests/real-road-legality-20261015` and related historical branches to the 59 modules; preserve original case IDs, counts and caveats. Do **not** copy entire branch trees or rewrite results automatically.
2. **Real difficult UK roads:** independently collect challenge cases with proven *actual turn-restriction relations*, multilane/spiral roundabouts, slip roads, parallel carriageways and level changes; use pinned public map data and independent legal evidence wherever feasible. Retain simple controls, no hard numeric minimum.
3. **Full positioning and speed:** on the same pinned public roads replay simulated public/non-personal GPS plus time, speed, heading, accuracy radius, sustained bad fixes, tunnel loss, car park startups and wrong-turn events. Separately judge map matching, speed measurements, posted speed limits and server/algorithm response time. Injected GPS cannot establish real sensor accuracy.
4. **End-to-end controller:** run departure-to-arrival sequences, roundabouts, lanes, speech timing, reroutes, correct entrance/side and offline region seams, marking unsupported capabilities UNKNOWN or NOT_RUN, then follow with selected GitHub Android emulator journeys.
5. **Reference ranking:** compare at least ten suitable reference families *when executable and genuinely comparable*; retain observational external systems in an unranked tier. Publish a per-category out-of-ten descending score **only when an explicit scoring formula and adequate comparable independently judged coverage exist**.

### Ownership and release
This test changed only the research **review branch** and temporarily downloaded public OSM data into CI. Existing research results were preserved. **No production Android branch or APK was modified, and no physical phone installation was required.**
