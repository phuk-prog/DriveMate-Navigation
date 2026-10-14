# Real English road speed category

This benchmark replaces *synthetic road performance comparisons* with real public
road-network geometry from Greater Manchester, England. Existing fabricated
road fixtures remain regression/mutation controls and are never evidence of
actual English-road navigation performance.

Dataset: Geofabrik historic `greater-manchester-261013.osm.pbf`, based on
OpenStreetMap; ODbL 1.0; attribution © OpenStreetMap contributors.
Fixed 2026-10-13 source snapshot. Road-subset bbox (W,S,E,N):
-2.252,53.477,-2.234,53.488 (central Manchester).

Only public road topology is used. All test endpoint pairs are deterministically
derived from public roads, not driver records or personal journeys. The full PBF
and XML are ignored under `results/`; CI artifacts exclude the map.
The historic PBF checksum is verified against its dated Geofabrik checksum and
the observed SHA-256 is recorded with the run.

The first cohort is DriveMate's Python research service, GraphHopper 11.1,
OSRM 5.27.1 MLD and OSRM 5.27.1 CH, executed as actual configured HTTP
services on one GitHub-hosted runner. MLD and CH are two configurations of
OSRM, not independent navigation products.

Warm-up 3 times, repeat 20 times each public-road scenario. Time includes the
HTTP response and JSON handling; report each request, median, p95, p99, max
and correct endpoint/route-response coverage. Invalid and unresolved responses
do not earn a speed rank. No cross-product routing-accuracy claim follows from
endpoint success alone; independent road/turn legality, lane geometry, real
GPS drives, Android battery, and UK traffic remain unverified.

If the importer rejects a genuine road or legal restriction, STOP: document
the gap and improve the importer; never remove restrictions or replace roads
with synthetic ones to manufacture passing results.

The source snapshot is not itself verified against current physical signage.
Real-world legality requires a separate independently established reference.


## Real-road import preparation

The first run found that unfiltered Greater Manchester urban XML exceeds the
prototype's 6 MB input cap. The preparation now uses Osmium's standard tag
filter with *automatic referenced-object inclusion*: every highway way,
barrier node, turn-restriction relation and lane-connectivity relation is
retained with its referenced nodes and ways. Unrelated buildings and shops
are excluded. This is extraction for a motorcar graph, not fabricated map data.
The filter intentionally preserves restrictions even when they cause the
prototype importer to reject the dataset. Failure is labelled an importer
coverage blocker, never an engine route-speed failure.

See https://docs.osmcode.org/osmium/latest/osmium-tags-filter.html.


## Conditional node metadata safety gate

The Manchester preflight found a conditional tag on a public map node. The
prototype importer previously rejected *every* node `:conditional` tag,
even those unrelated to motorcar routing. It now distinguishes generic,
unmodelled bicycle/parking node metadata from conditional motorcar access,
barriers, speed and other road-safety keys. Safety-relevant unsupported
conditions remain hard import failures; irrelevant conditions are counted
in importer metadata and are never used to infer legal permission.
Regression tests exercise both acceptance and fail-closed cases.


## Fixed-area coverage gate (do not cherry-pick failures)

The central Manchester tile has an actual unsupported `motor_vehicle:conditional`
tag on a node, which **must not be silently dropped**. We therefore retain an
explicit `UNSUPPORTED` area-preflight result and independently try four other
predeclared public English-road tiles: Stockport, Wigan, Rochdale and
Ashton-under-Lyne. Only the first successfully imported region enters the
limited warm HTTP speed benchmark. The rejected-area records are retained in
`area-preflight.log`; no inference of UK-wide speed, route correctness or legal
coverage is permitted from a selected region. Extending DriveMate's conditional
motor-vehicle access model remains an independent correctness task.


## Additional independent speed references

Add Valhalla 3.9.1 (`auto` costing) and openrouteservice 9.7.1
(`driving-car`) as genuine engine services loading the **same Wigan
OSM PBF extract** on the **same runner**. Each gets the same case IDs,
cold graph preparation is outside the timed warm HTTP window, and response
endpoints are validated before a valid response is counted.

If a reference service fails its startup/readiness gate, its outcome is
`not_tested`, with the actual Docker log retained; it is **never**
awarded a zero time, a passing route, or a failed navigation correctness mark.
Invalid route responses are distinct from setup failures and cannot earn
complete-cohort speed ranks.

BRouter needs its **own original .rd5 data built from this pinned map**.
Public weekly BRouter tile downloads are NOT a same-map comparison.
RoutingKit CH and pgRouting are algorithm-only adapters currently fed by
DriveMate-imported transitions. They are not ranked against independent
HTTP road importers, and no fake service result is inserted.

This remains a **warm HTTP response latency** comparison for a small
real-road extract, not an Android navigation quality, full-English-network
routing, or verified legal-road-performance ranking. Preserve total and
per-case timing records, all unresolved cases and source provenance.


## openrouteservice startup diagnosis

The first ORS 9.7.1 setup downloaded its official image but did not
reach /health and was excluded, not scored as a routing failure.
Because it previously launched with Docker --rm, its failure
logs were lost on exit. The next run retains stopped containers until
the final cleanup, prints the bounded startup log on failure, and
assigns ephemeral writable directories to image UID 1000 before launch.
A response-time result is accepted only if an ORS service genuinely
starts and passes all per-route response checks.


## Corrected ORS profile configuration

The retained container log identified the exact startup failure:
`Expected single profile in config`. We had created an unintended custom
`car` profile while the image already enabled the normal
`driving-car` profile. The test workflow now sets
`ors.engine.profiles.driving-car.enabled=true` (documented default
profile name). This changes only the isolated reference engine
configuration; it does not alter DriveMate routing or road permissions.


## Compiled DriveMate build is now the primary benchmark candidate

The previous speed category mistakenly ranked a Python research service as
"DriveMate". This was not the compiled routing build. The real-road benchmark
now calls the **compiled C++ navigation_core/native/router** through a
single persistent `--stream` session with the map prepared once.
Every result is independently checked against the navigation-core route
validator (legal transitions, path continuity and integer route cost).
The wrapper must mark results `implementation=compiled-cpp`; an impostor,
missing/malformed or non-native response never earns a speed measurement.

The C++ binary retains its original bounded batch-mode protocol unchanged
for existing regression tests. `--stream` adds an optional benchmark-only
read-query/write-response loop, using exactly the existing C++ routing search
functions; it never falls back to Python shortest-path search.

Two distinct timing measurements are preserved: (1) native C++ internal
calculation nanoseconds, excluding request marshalling, and (2) end-to-end
warm local HTTP response milliseconds, including the Python HTTP wrapper,
cross-process communication and validation. The latter can be compared
methodologically against other local HTTP services, subject to different
costings and interfaces. Do not claim these are on-device Android/APK figures.

Python remains an oracle/reference for preflight and independent correctness;
it is no longer the primary scored DriveMate candidate in the engine rankings.
