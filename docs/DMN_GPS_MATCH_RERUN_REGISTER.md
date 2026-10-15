# DMN post-improvement comparison execution

This is a staged research-only assessment, not a twelve-engine accuracy ranking.

## Current safety intervention
- The new common last-fix source-geometry proxy and the DMN temporal matcher speed-consistency gate were successfully verified by [GitHub Actions 38765188399](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38765188399): **221/221 Python tests green**.
- Before any claimed increase in navigation quality, rerun each available external map matcher with the exact same snapshot/fixes and aggregate the common source-geometry proximity proxy. Evaluate the existing DMN temporal algorithm with the new speed consistency rule.
- **Critical:** a snapped point near the OSM generating edge is not independently verified right road, correct direction, legal maneuver or lane. Scores/rank remain unavailable until true, common road/direction truth exists.

## Opt-in execution
1. OSRM 5.27.1 local Match using pinned UK map subset.
2. Valhalla 3.9.1 local trace_attributes on the same subset.
3. GraphHopper 11.1 local /match on the same subset.

Run these sequentially to limit CI usage; preserve their historical baseline artifacts and reports. Do not report a new execution until a matching CI action succeeds. The evidence should separately show DMN single-fix, DMN temporal, each external engine, confident wrong-edge results, ambiguous/unmatched, geometry proxy, and unverified independent field truth. No production app or APK changes.

## OSRM geometry proxy after DMN speed gate

[Actual post-improvement run 38765331956](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38765331956) passed all 221 Python tests and completed the external OSRM local map matching on pinned Geofabrik UK map. The **same 12 final GPS observations** gave DMN single-fix **6/12 within 5 m, 6 withheld**, DMN temporal **8/12 within 5 m, 4 withheld**, OSRM Match **12/12 within 5 m, 0 withheld**, with **all near cases** having another mapped allowed directed road within 10 m (often simply the reverse edge on the same two-way geometry). No road-direction truth or independent surveyed position. This test is only a geometry-proximity comparison; **do not rank providers** from it. Valhalla comparison is the next single opt-in.

## Valhalla geometry proxy after DMN speed gate

[Actual post-improvement run 38765532707](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38765532707) GREEN, **221/221 Python tests** and real local Valhalla trace matching on the same pinned UK map. Common last-fix geometry proxy on identical 12 cases: DMN single 6/12 near, 6 withheld; DMN temporal 8/12 near, 4 withheld; Valhalla 9/12 within 5 m of the generating OSM link, 1/12 farther than 5 m, and 2/12 withheld. All nine near Valhalla cases had another plausible directed OSM link within 10 m, so this still **cannot verify road/direction**, lane or safe real GPS. GraphHopper is next sequential opt-in.

## GraphHopper geometry proxy after DMN speed gate

[Actual GitHub Actions run 38765714206](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38765714206) completed **SUCCESS**, **221/221 Python tests**, genuine local GraphHopper 11.1 `/match` requests on identical OSM map input and the same twelve generated UK-road 4-fix traces. Shared last-fix geometry proxy: DMN single **6/12** near within 5 m of generating road (6 withheld), DMN temporal **8/12** (4 withheld), GraphHopper **3/12** (9 not safely alignable/withheld). GraphHopper's 3 near outcomes all had other allowed directed road links within 10 m. It is **not** measured correct directional road identity, GPS field accuracy or independently corroborated traffic legality. This completes three sequential opt-in post-improvement external matching runs, without overlapping large CI jobs or app builds.

## Verified post-improvement cross-engine *same metric* (still non-independent)

| GPS last-fix output from identical twelve source-generated UK scenarios | Near generating OSM road within 5 m | Farther than 5 m | Unmatched, unalignable or withheld | Nearby alternative directed OSM edges for near results |
|---|---:|---:|---:|---:|
| **DMN one-fix candidate** | **6/12** | 0 | 6 | 6/6 |
| **DMN existing temporal** | **8/12** | 0 | 4 | 8/8 |
| **OSRM Match 5.27.1** | **12/12** | 0 | 0 | 12/12 |
| **Valhalla trace_attributes 3.9.1** | **9/12** | 1 | 2 | 9/9 |
| **GraphHopper 11.1 /match** | **3/12** | 0 | 9 | 3/3 |

Every near output has at least one other *directed edge* within 10 m, commonly a reverse edge of the same physical two-way road. Thus **even the OSRM 12/12 outcome does NOT prove the right road or carriageway or driving direction**. No out-of-ten category scores or ordinal ranking are justified. Each provider uses its own compiled graph, profiles and matching interfaces; all injected GPS positions originate from the same public map geometry used as the proximity oracle. The conservative speed-inconsistency safeguard is covered by new regression tests; **no real driving scenario yet independently proves that the change reduces actual wrong-road matches**. Preserve the previously observed 8/12 DMN temporal correctness counts as the limited map-generating-edge proxy, not independent traffic truth.

### Next discriminating checks

1. Build a **source OSM way ID / directed movement / position crosswalk** and distinguish two directed edges on one two-way physical road from genuinely different parallel carriageways (service roads/slips). Investigate alternative road count rather than assuming every reverse edge means wrong physical road.
2. Introduce independently grounded UK movement/road truth (official restrictions, traffic orders, public surveyed map or manually corroborated signs when available). Test wrong-direction, dual carriageways, slip-road merges, stacked roads, sharp turns and time-constrained transitions separately.
3. Expand held-out public UK situations and GPS noise severity, then retest all three external engines with identical observed dimensions and verified legal matching interfaces. Adding more names from the twelve-engine portfolio is not a substitute for comparable correctness evidence.
4. Only improve DMN matches where real evidence supports a safer unique result. Do **not** remove abstention merely to equal 12/12 close-by outputs; continue regression safety guards and rerun full checks after each change.
