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

### Explicit multi-region validation invocation
The temporary draft-PR marker is enabled for one synchronization run to measure the candidate regions with the 2026-09-01 pinned public extract. A green CI status alone is not a successful route-comparison verdict; inspect the JSON `result` and per-area supported/unsupported counters, then remove the title marker.


## Second experiment — useful alternative-route topology found

**[GitHub Actions run 38789915043](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38789915043) SUCCESS**, 270/270 Python unit and contract tests. Opt-in UK coverage step actually executed; reusable aggregate evidence artifact: `dmn-public-uk-network-coverage` (artifact 11998804996). The trigger was removed from the draft PR immediately after completion.

The **South Manchester** public, pinned (`geofabrik-260901`) sample imported successfully: source SHA256 `bd91e62db908ceaad39438b0122b04c6efcaa73383bc6de85824dc5b05b30329`; 17,518 declared vertices, **944 permitted-road active vertices**, 1,749 allowed directed edges, 1,100 uncertain directed edges and 238 prohibited directed edges. Seven weak permitted-road components (largest 775 vertices), a physical-cycle-rank upper bound of 19, and 699 branching vertices. **71/96** map-derived origin/destination pairs had multiple paths; **10/96** used different Fastest vs Shortest mapped routes; **0/96** had Balanced distinct from both. Eight initial A*/Dijkstra public-map scenarios completed; no imported prohibited turn pairs.

**Wigan and central Manchester**: both marked `UNSUPPORTED` by the conservative importer, *not* 0/96 performance and not navigation failures. Unsupported reason classes should be diagnosed safely (bounds/object count, missing complete relation, conditional/via-way tags, etc.) without relaxing the closure/turn safety guard.

**What this proves:** a more representative bounded public road network can exercise genuinely different route preferences in the research engine. **What this does not prove:** correct real-world UK turn legality, driver journey quality, lane advice, current traffic or superiority over OSRM/Valhalla/GraphHopper. All 10 divergent cases need independent legal/geometry checks and matched-source competitor execution before any scored ranking.

**Next priorities:** classify the two importer rejections; preserve and export sanitized, reproducible source/map-scoped 10-case route test identifiers; add independently verified turn/access truth; compare the exact same public road graph cases to locally executed accessible external engines, with transparent non-comparable/missing judgments; rerun after improvements. Do not lift uncertain edge restrictions to artificially improve coverage.

## Measured diagnosis and deliberate next comparison

[Actual 38789281863](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38789281863) SUCCESS: **266 Python tests**, source graph 2,023 declared vertices, 1,202 directed edges, but only **96 mapped usable directed edges across 49 active nodes**. These form ONE weak component and have **physical cycle rank zero**, so the 96 extracted travel pairs necessarily have no alternate physical corridor. Graph branch counts from bidirectional links are not proof of alternative routes. Source classification breakdown is to be measured explicitly in the next run; it is incorrect to assume all 1,106 remaining directed edges are closed or illegal without inspecting their source access tags.

Next controlled opt-in `[uk-route-diversity-smoke]` keeps the first pinned historical cohort as an unchanged control and runs TWO separately preselected small public Greater Manchester/Stockport road areas through the existing strict importer, no user locations or new app code. The machine report includes source road-access counts by OSM highway class, active connectivity, physical cycle rank, distinct route-choice counts, and rejects unknown/unsupported motorcar legality rather than discarding rules. Both fixed extracts and downloaded public PBF are deleted; only aggregate JSON evidence retained in the job artifact. If source import is unsupported or the test still has zero useful cycles, report **INSUFFICIENT** and improve the bounded completeness-preserving importer next. Neither source timestamp nor an OSM graph cycle proves independently legal UK driving maneuvers.

### Controlled area-study execution

The research unit gate [38790336431](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38790336431) passed **273/273 Python checks**, including temporary-directory setup repair. A single `[uk-route-diversity-smoke]` draft-PR opt-in is requested here to run the additional TWO independent public road-area extracts on the same pinned public Greater Manchester OSM snapshot. Record all status counts, true route-path diversity, any import failures and source highway-class access summaries; upload **only aggregate JSON** and delete source files. Remove the PR opt-in title as soon as results are captured. Green execution alone is NOT road truth.

## Connected real-road restricted-turn preference comparison

The two simpler bounded city-area extractions were measured in [Actions 38790505083](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38790505083) (**273/273 Python tests, experiment completed**), but **0/2 road areas were safely importable**: Manchester centre had a mapped restriction referencing a missing/non-drivable maneuver; Stockport contained a conditional road rule the prototype does not support. Consequently **ZERO real-route mode comparisons were added**, even though CI was green. Both must remain unsupported; do not delete their conditional rule or pretend an incomplete road graph is legally navigable. The opt-in PR title was cleared.

To obtain real connected road choice *without weakening the strict importer*, the established `benchmarks.uk_neighborhood_detours` buffered, source-complete restriction cases now also execute the actual **Fastest, Shortest and Balanced** candidate generator, preserving the incoming road edge. Each generated route must respect mapped access and turn rules, align with existing independent shortest-time Dijkstra and stay explicitly UNVERIFIED until a separate legal/road-data oracle confirms it. The report distinguishes independently chosen mapped cases, multiple candidate paths, fastest/shortest divergences and unsupported neighborhoods; its pre-existing 3/4 historically runnable examples are NOT assumed to yield preference diversity without a new measured run.

### One-time bounded real-road preference run

After unit/contract CI for the revised preference probe completed green, request exactly one `[neighborhood-detour-smoke]` public Geofabrik 2026-09-01 test of the existing four mapped-turn-rule neighborhoods. Retain incomplete/conditional areas as unsupported, enforce incoming-edge turn legality for every candidate, and report both ordinary found detours and preference diversity as separate denominators. Once finished clear the PR opt-in marker; do not repeat heavy downloads or claim traffic-law certification.

### Measured restricted-turn alternatives and expanded internal pairing

[Real UK Actions 38791026944](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38791026944) GREEN, **273/273 Python checks**: 4 public UK restriction neighborhoods prepared, 3 with complete imported mapped rules, **3/3 graph-permitted detours found**, **3/3 profile-tested restricted turns with multiple candidate paths**, **0/3 fastest vs shortest mode-optimum divergences**, **7/7 candidate paths explicitly unverified for real UK law**, and 1 incomplete neighbor restriction left unsupported. The bounded results are NOT independent real road law, not whole-UK legal routing proof or competitor scores. This is improved connected-route coverage, but only three very close junction journeys.

The next experiment explores up to **48 additional mapped-graph journey pairs per safely supported neighborhood** (same actual public UK roads, same snapshot and mapped restrictions) and records observed physical cycle availability, alternate candidates, Fastest/Shortest divergence and whether Balanced is distinct. Previously measured single restricted-turn cases are retained unchanged. New OSM-only alternatives remain NOT independently verified UK legal routes. No competitor access or Android APK in this experiment.
