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
