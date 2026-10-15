# DMN network connectivity and route-alternative recheck — 15 October 2026

This is an **opt-in, research-only** pinned Greater Manchester experiment. It repeats the historical public-road cohort with the improved branch/rejoin route-pair scanner and new graph-connectivity diagnostics (without modifying the sample, source date or route algorithms).

## Pre-existing control

Prior experiment [38782273948](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38782273948) checked 96 mapped routes and found zero distinct candidates. Graph was 2,023 declared vertices, 1,202 directed edges and zero imported prohibited-turn pairs. The result was INSUFFICIENT, not a validation of driver preferences.

## Recheck acceptance

Report active drivable nodes, weak components, largest weak component, branch nodes and physical cycle-rank upper bound. Report routable pairs, pairs with multiple paths, fastest-shortest disagreement and balanced distinction with explicit denominators. A successful CI run with zero divergence is still insufficient map coverage; never infer independently verified UK legality from OSM topology.

If scanner finds no useful alternatives, next isolate graph sparsity causes and expand the public area or extraction strategy under source/license/privacy, restriction completeness, import-size and execution limits; preserve this historical control. Compare against OSRM, Valhalla and GraphHopper only when on identical valid source cohorts. No personal routes, paid services, production DriveMate changes, or APK.

## Opt-in trigger diagnosis

CI run [38789145034](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38789145034) passed research unit checks but **SKIPPED** the UK smoke: on the `pull_request` event the workflow did not receive `github.event.head_commit.message`; the expensive opt-in is gated by the **pull-request title**. The draft PR title is temporarily marked `[uk-road-smoke]` for ONE controlled synchronization run, then will be unmarked. Do not mistake the skipped run for new UK route evidence.


## Executed pinned road-network diagnosis (verified)

[Actions run 38789281863](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38789281863) completed successfully with **266/266 Python unit tests**. Its public Geofabrik 2026-09-01 partial Greater Manchester map imported **2,023 graph vertices and 1,202 directed edges**, but only **49 active permitted-driving vertices** and **96 allowed directed edges**. The usable undirected network has **one weak component, 49 vertices and zero physical cycles**, despite 47 possible branch vertices (principally reverse directions); there are **zero imported turn prohibition pairs**. An improved branch/rejoin scanner still found **0/96 pairs with multiple routes**, **0/96 shortest/fastest divergences**, and **0/96 balanced-distinct paths**.

**Interpretation:** this is a *map coverage / conservative access-network limitation*, not an optimization tie, proof of road legality, nor evidence that route modes are equivalent. Many declared nodes and directed edges cannot be used as permitted vehicle navigation. Do not reclassify unknown or prohibited edges as allowed just to fabricate route alternatives. The latest code now separately reports allowed, unknown and prohibited directed edge counts.

## Next opted-in data investigation

An isolated workflow marker `[uk-network-coverage-smoke]` can run `benchmarks.public_network_sweep` on independently chosen bounded South Manchester, Wigan, and central Manchester public-map areas, reusing one pinned Geofabrik source. Each area will either yield a comparable topology report or be marked **UNSUPPORTED** due to importer limits/complex relations (never a fictitious pass). The runner securely removes temporary XML/PBF map inputs and saves only aggregate diagnostics. Keep the original 96 pairs as the historical control. Require at least one connected, loop-bearing allowed graph with meaningful candidate differences before external route-preference rankings. Even then, corroborated legal restrictions and same-route external-engine tests remain separate work.
