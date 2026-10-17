# RESOURCE-001: bounded resource characterization and A* work reduction

All nine frozen analytical grid cases pass under three DMN configurations in
both timing/memory phases. CI executes324 actual searches in18 sequential fresh
workers; all429 tests and existing safety batches pass. The new per-request A*
cache reduces real distance-function calls from223 to64 on the8×8 diagonal
control without changing route acceptance. It increases Python query allocation
peaks; it does not establish universal speed superiority.

The cases use invented8/16/32-square grids with112m edges at40km/h. Manhattan
edge count, length and time are hand-declared in the frozen oracle; every path
is checked for continuity/access and agreement with those analytical quantities.
No competitor or DMN route defines expected correctness. This is not independent
road/GNSS truth, Android performance, battery life or country-scale routing.

## Actual CI resource values

Representative32×32 cases below use1024 vertices and3968 directed edges. The
three configurations are **one DMN family**, not three navigation engines.

| Configuration | Graph build ms | Separate preparation ms | Diagonal median/p95 ms | Reverse median/p95 ms | Row median/p95 ms |
|---|---:|---:|---:|---:|---:|
|Dijkstra|5.544|0|8.748/11.724|8.752/8.870|6.392/6.688|
|A* raw coordinates|5.605|0|13.648/16.654|14.030/23.321|3.125/3.155|
|A* prepared|5.715|2.949|11.053/13.834|10.684/11.957|0.183/0.192|

Prepared A* is much faster for the row case but remains slower than Dijkstra for
the two diagonals. Its one-time validation/preparation cost is shown explicitly;
raw A* validates geometry on each query. The default router remains Dijkstra.
No evidence here justifies switching every query to A*.

| Separate memory worker | Setup Python peak bytes | Diagonal query Python peak bytes | Reverse query Python peak bytes | Row query Python peak bytes | Whole-worker peak RSS KiB |
|---|---:|---:|---:|---:|---:|
|Dijkstra|1563204|786912|722440|631148|27352|
|A* raw|1563204|868712|789064|20672|27752|
|A* prepared|1563204|868408|789040|20648|27412|

Python traced allocation peaks and process RSS measure different things. RSS is
Linux worker-lifetime high water including the interpreter, setup, protocol/hash
bookkeeping and all requests; it is not request-only memory. Setup peak includes
graph construction and preparation. Query allocation peaks are separately traced
increments; graph allocations predate that trace. Memory workers are separate
from timing workers, so tracemalloc does not distort the timing samples.

Each case has one warmup plus ten untraced timed calls. Raw nanosecond samples
are retained; p95 uses nearest rank and, with ten samples, equals the observed
maximum. It is not a population tail-latency guarantee. Configuration order
rotates by graph size; every worker runs sequentially. Runtime/hardware variation
limits cross-run claims. Python/kernel/architecture/CPU-count/clock metadata are
recorded, but there is no calibrated phone or identical-native-runtime test.
The worker40s and total180s limits bound this experiment.

## Reproduced inefficiency, change and retest

The old A* implementation computes a geographic heuristic for every improved
incoming-edge state. Multiple such states share a vertex/destination, so the
same real geodesic calculation repeats. A delegating test spy measured223 calls
on64 vertices; the new bound-control failed with223>64. The spy performs the
real distance calculation and the router returns a real path; it does not mock
an engine/reference response. Old engine source remains available at the frozen
base SHA, and the original measured run/hash/counter is preserved.

A local dictionary now caches each vertex's value within one request. It does
not live in prepared map state, leak between destinations, weaken admissibility,
change turn/access rules or alter acceptance. The same control now measures64
calls. A changed-destination test, the full429 tests and all frozen resource
paths pass. Existing invalid-geometry fallback and map-bound preparation tests
remain in the full suite.

On the same local workspace, the32×32 prepared diagonal medians changed from
14.742/13.864ms to10.913/10.387ms. Its diagonal Python allocation peaks rose from
817840/738576bytes to868232/788992bytes, about50KB additional memory. The unchanged
Dijkstra control also sped up from8.885/8.788ms to7.810/7.969ms, showing ambient
variation. Therefore the entire latency difference is **not attributed to the
cache**. The deterministic work-count reduction is established; timings are
informational observations with an explicit memory tradeoff. No arbitrary
performance threshold or overall resource score was invented.

[Before local run](../references/resource001-before-local-20261016.json) and
[after local retest](../references/resource001-after-local-20261016.json) retain
all nine cases/three configurations, raw timing samples, separate memory workers,
source/oracle/graph hashes and the work-control result. They explicitly identify
local working-tree execution; neither is falsely labelled a CI run. Both use
the same measurement harness. CI's committed-source run is separate evidence.

## Reference coverage and ranking limits

The [CI report](../references/resource001-ci-20261016.json) retains all12 external
families plus DMN and all nine per-case reasons. All external resource cohorts
remain NOT_RUN/unranked. Five existing OSM directions adapters do not accept the
identical arbitrary112m/40km/h RoadGraph. Their previous OSM/HTTP query measurements
are different cost models, transports and workloads and are not substituted.
OsmAnd/Organic Maps lack executable native/app resource harnesses. HERE/Mapbox/
TomTom/Google lack configured permitted same-workload access; no paid calls are
authorized. Waze lacks an established permitted automated replay interface.
These are work/access gaps, not evidence that those engines are slow or unsafe.

Last actually executed static reference versions remain OSRM5.27.1 car.lua/MLD,
Valhalla3.9.1 auto, GraphHopper11.1 car/CH, ORS10.1.0 driving-car/fastest and
BRouter1.7.10 car-vario, with their earlier exact configurations/hashes and CI
links. None is claimed executed in RESOURCE-001. A common native resource adapter
and broader comparisons remain future work. This trial has no performance
quality threshold, so no out-of-ten resource-quality score or cross-family rank
is assigned. Earlier scoped GPS/routing/junction rankings remain intact.

## Exact provenance and remaining work

- Inspected base:`b71b125d9cec45c3bb6430947c88299dc45f70ee`.
- Freeze:`9dd63134411b9562519d7bd6cf5abfe1a4b19ea6`, before resource tuning.
- Executed implementation:`83f3830ee346ba428e4d78ad09e528f40e28ba95`.
- CI:[38861398588](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38861398588), job116844266276;429 tests,324 actual searches, all54 size/configuration/phase case rows pass (nine distinct cases).
- Oracle SHA256:`53146d2087ed204f01d870291df17898b1f5e27ff69039b01e02a642126a6dd5`.
- Every worker records the complete canonical graph digest; the report binds the
  grid generator, harness and both algorithm source hashes, phases/configuration,
  actual run SHA and environment. No external engine or Android test was run.

Run`python -m benchmarks.resource_trial --output results/resource001-DMN.json`.
Normal CI now gates the resource correctness cohort and retains measured values.
Compile/privacy/whitespace and full local checks pass. Canonical
`scripts/unified_preflight.py` remains unavailable, never counted passed. Rollback
removes the per-request cache and new resource gate/harness; no production app,
release, APK, signing or paid infrastructure changed.

The owner authorized the remaining programme, but its earlier one-bounded-stage
per-invocation requirement is retained. Next bounded stage is research integration:
connect map snapshot/context, matching/progress, rerouting, guidance and arrival
and replay failures together before any readiness claim. The separate longer
phone/lifecycle/battery trials and native offline route proof remain UNAVAILABLE:
this workspace has no adb, emulator or research Android project; no device run
or APK was produced. Independent labelled road/legal/GNSS truth has not been
obtained; generated-map agreement and competitor consensus cannot replace it.
These availability findings are not claims that all harness-development work is
blocked or complete. Broader permitted competitor adapters remain work.

The seven UK backward-adjacent coverage cases remain unresolved; no new truth
supports forcing them. The17 correct/0 confident wrong/23 withheld result and
promotion block are unchanged. Preserve all failures and proceed through the
remaining authorized stages, with physical/independent checks explicitly unverified
until actual evidence exists. Do not merge or promote on synthetic resource wins.
