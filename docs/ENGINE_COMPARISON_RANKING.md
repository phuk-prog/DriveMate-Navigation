# Routing engine expansion and safety-first benchmark ranking

## Seven runnable configurations

1. DriveMate independent routing candidate.
2. GraphHopper 11.1, pinned Java JAR.
3. OSRM MLD 5.27.1 pinned container.
4. OSRM CH 5.27.1 pinned container (same OSRM engine, distinct algorithm).
5. Valhalla 3.9.1 pinned container.
6. RoutingKit C++ CH pinned Git commit 54d49bb0cdea56dde182357522e4e86a03c57852 (BSD-2-Clause).
7. pgRouting 3.7.3 PostgreSQL/Boost Dijkstra with recorded image digest.

**Five distinct routing software families, seven configurations.** None of the open-source dependencies are integrated or copied into DriveMate's production Android code. They are disposable benchmark runtimes.

## Ranking contract

A leaderboard is generated only from matching authenticated fresh evidence: nine identical scenario IDs, exactly matching dataset SHA-256 and expected paths. Ranking order: confirmed forbidden-route errors first (worst), then most correct, fewest incorrect, fewest unresolved cases. Ties remain ties; candidate-only GPS and UI results cannot create a synthetic superiority claim.

Files in each successful workflow artifact: `RANKING.md` (clear placement/failures); `ranking.json` (machine-readable); `HEAD_TO_HEAD.md` (per-case pass/fail/unknown); `SCORECARD.md` (ranking plus category comparisons).

Each engine's failed or unresolved case is highlighted with scenario identity. Environmental setup errors remain unavailable, not route failures. A deviation from a specially authored shortest route needs legal verification before being labelled an unlawful manoeuvre.

## Technical parity boundaries

RoutingKit and pgRouting use their **actual independent CH/Dijkstra search implementations** but are fed an explicit edge-state graph that carries the same imported access and turn constraints. This verifies search under matching route inputs, **not** native OSM import, independent turn-restriction parsing, numbered roundabout directions, map-matching or real-time rerouting. CH/MLD and different cost models must not be counted as distinct consumer apps.

All seven can be ranked on the nine shared route cases. Only DriveMate, GraphHopper, OSRM MLD/CH and Valhalla have corresponding roundabout-exit guidance evidence on four synthetic rings. Only the first five support the four clean observed-position path comparisons. GPS failure recovery, lanes, instruction audio, offline battery and real-UK roads remain unranked between competitors.

## Defect history

RoutingKit first reported eight passes, one failed "reverse_one_way_no_route" case: the benchmark adapter mistaken an unreachable empty arc path for an actual empty route. Fixed and rerun: nine passes, no failures.

pgRouting first could not initialise its extension, then yielded nine unknowns when psql command tag lines were interpreted as edge IDs. Both were benchmark-harness issues; the corrected engine run passed nine out of nine.

Never delete failed logs or overwrite their evidence; report passing latest results and the previous failure history separately.
