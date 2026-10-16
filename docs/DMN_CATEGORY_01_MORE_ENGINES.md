# MAP-001 additional unchanged reference engines — binary access trial

Scope: Category 1, frozen Manchester OSM XML SHA-256
`34438baa7a28c55958cd5ba7ac3909a551c51197911963364d27a26eefe8973a`.
The workflow starts from the same archived v3 artifact and builds isolated
real-OSM-way graphs sequentially; no synthetic roads are entered into scoring.
Reference implementations stay unmodified and local. All input conversions,
build versions, source SHA and HTTP result hashes are retained. No user GPS.

- Valhalla 3.9.1: original 32 profile checks and full native graph audit remain.
- OSRM MLD 5.27.1: unchanged pinned BSD-2-Clause reference build,
  default upstream car.lua, no access/oneway/restriction bypass.
- GraphHopper 11.1: unchanged Apache-2.0 community Java jar with the same
  car-profile config used in existing repo test workflows, network-minimum
  zero only to permit a small isolated graph, not to override motorcar policy.
- DMN: same importer/source access controls, no new navigation behaviour changes.

Only four source ways (155729945, 115559329, 548694371,
35277147) have eight testable forward/reverse ordinary-car controls.
The contextual or permission-specific profiles remain unsupported in the
OSRM/GraphHopper request API, not assumed closed or scored as pass.
Native graph/directed-turn comparison remains only for Valhalla; the
additional adapters observe local route responses, which are a different
scope. No full Category 1 ranking or real-UK-road-law certification.

A nonzero returned route must correlate with the **actual two source
endpoints** or it is NOT_JUDGED. NoSegment/unmatched snap, invalid JSON, API
failure and missing geometry cannot be converted into NO_ROUTE. GraphHopper's
specific "Connection not found" with HTTP 400 and OSRM NoRoute with HTTP 200
are the only accepted engine-denial signatures. Failures and unjudged results
are retained; partial rankings require the same cases in all four engines.
Do not rank computation speed: local HTTP requests, import and routing
and external engine startup have different measurement boundaries.

The engine support is a benchmark adapter, not incorporation of a third-party
engine into the independently controlled DMN runtime. OSM attribution:
OpenStreetMap contributors (ODbL). No third-party source copied, no paid
provider, and no commercial reference without permission.

The frozen input, artifact and case register are retained. If setup fails,
label the event SETUP_FAILURE; repair setup without silently changing car
policy or deleting historical results. No Category 2/app/APK/merge work.

## Preserved first setup failure

Initial batch commit 9145f1f on CI runs 38968182356 and 38968182544 failed
**before engine execution**: category_test_runner rejected an unregistered
new test file. Corrective commit registers it to map_data without changing
test expectations, frozen data, engine configuration or DMN runtime.
Fresh complete execution is required; the failed CI evidence remains on GitHub.

## First actual run and corrective classification

Full workflow https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38968306967
PASS with fresh local execution of all four engines. Its original strict
route-error classifier judged 5/8 common binary cases (four engines 5/5 on
that shared subset), with three reverse-denial cases unjudged for both OSRM
and GraphHopper. The 12-way native directed access comparison remained
12/12 and 108 segment checks for DMN and Valhalla. Valhalla's original
profile check was 10/10 comparable; DMN passed all 32 isolated-way profiles.

Investigation found a **harness classification gap**, not evidence that the
three reverse road movements are permitted. OSRM 5.x can return HTTP 400
with JSON code NoRoute; GraphHopper can return HTTP 400 with the exact
message "Connection between locations not found". The adapter previously
withheld those responses because it accepted only HTTP 200 OSRM NoRoute and
a different GraphHopper error string. It now recognises these exact error
signatures while preserving NOT_JUDGED for NoSegment, snap mismatches,
invalid options, missing geometry and other HTTP error responses.

External documentation supporting the correction:
- https://github.com/Project-OSRM/osrm-backend/blob/master/docs/http.md
- https://github.com/Project-OSRM/osrm-backend/issues/1968
- https://github.com/graphhopper/graphhopper/issues/2826

Fresh four-engine execution on the original unchanged frozen inputs is
required. Do not promote the original 5/5 to 8/8 by reclassifying historical
observations. Preserve that first execution as separate evidence.
