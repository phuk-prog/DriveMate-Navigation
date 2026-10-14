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
