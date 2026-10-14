# Larger-map comparison protocol

The shared research OSM map now also contains four 16-by-16 directed grids with
diagonal alternatives, plus fixed-turn corridors with physical alternatives.
The 64 additional cases comprise 24 distance-choice requests, 16 stateless
missed-turn restart requests, eight reverse no-route requests and 16 fixed
90-degree turn-family checks. Half are on held-out coordinate layouts. Topology
is similar across layouts; these remain authored synthetic roads, not real cities.

The independent fixture imports no engine code. A separate shortest-path oracle
uses authored way lengths and connectivity. Grid/corridor components have no turn
restrictions, and all roads declare the same residential class and speed.
Existing difficult turn-restriction fixtures remain in the same map and are
rerun separately. A result can be legal while longer than the independently
shortest distance. The reported 1% distance criterion does not assert identical
vendor costing, ETA accuracy, or an optimal real-world driving route.

Each available engine actually runs the same requests and map. Native OSM
importers remain separate from RoutingKit and pgRouting, whose transitions are
supplied by the research importer. Endpoint snaps beyond 2m remain unresolved.
Raw competitor route responses are preserved. Fixed-turn checks compare ordered
left/right families, excluding departure/arrival and straight prompts. They do
not compare speech timing or fabricate lane occupancy.

DriveMate and GraphHopper additionally receive three warmup rounds and ten
measured rounds of eight larger-map requests, alternating order on one host.
Both use local HTTP, but DriveMate invokes its subprocess-backed ALT router and
returns a compact path, while GraphHopper uses a persistent JVM with CH/LM
disabled and its fuller response. Costing, response size and wrappers differ.
The p95 order describes these configured services on this workload only. It
does not rank native kernels, Android performance, cold start or all seven
engines. Timings from separate CI jobs are retained but not globally ranked.

Revision, map hash, exact coverage, distance truth and instruction-pass claims
are validated before scorecard generation. Corrupt path controls must detect a
missing road, reversed sequence and false no-route response. Focused regressions
also reject invented distance scores and turn passes. Legal/critical failures
remain more important than distance or speed; no combined app winner is asserted.

Output: `quality.json` per engine, paired `quality_speed.json`, and consolidated
`ROUTE_QUALITY_SCORECARD.md` / `route_quality_results.json` in the category artifact.

Valhalla turn-family constants are verified against the pinned
[3.9.1 direction descriptor](https://github.com/valhalla/valhalla/blob/3.9.1/proto/descriptors/directions.proto).
Production DriveMate and its APK are outside this work.
