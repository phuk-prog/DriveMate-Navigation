# DMN network connectivity and route-alternative recheck — 15 October 2026

This is an **opt-in, research-only** pinned Greater Manchester experiment. It repeats the historical public-road cohort with the improved branch/rejoin route-pair scanner and new graph-connectivity diagnostics (without modifying the sample, source date or route algorithms).

## Pre-existing control

Prior experiment [38782273948](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38782273948) checked 96 mapped routes and found zero distinct candidates. Graph was 2,023 declared vertices, 1,202 directed edges and zero imported prohibited-turn pairs. The result was INSUFFICIENT, not a validation of driver preferences.

## Recheck acceptance

Report active drivable nodes, weak components, largest weak component, branch nodes and physical cycle-rank upper bound. Report routable pairs, pairs with multiple paths, fastest-shortest disagreement and balanced distinction with explicit denominators. A successful CI run with zero divergence is still insufficient map coverage; never infer independently verified UK legality from OSM topology.

If scanner finds no useful alternatives, next isolate graph sparsity causes and expand the public area or extraction strategy under source/license/privacy, restriction completeness, import-size and execution limits; preserve this historical control. Compare against OSRM, Valhalla and GraphHopper only when on identical valid source cohorts. No personal routes, paid services, production DriveMate changes, or APK.
