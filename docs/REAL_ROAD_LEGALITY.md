# DMN real-road routing legality stage

Scope: compare navigation components, not whole competitor apps. Research branch `tests/real-road-legality-20261015` derives from `93a5964ca4b21d0ccedde66a83eced6ddc02804a`. Existing Android integration branch and production remain unchanged. No APK publication.

## Protocol

- Preserve the original 100 Wigan endpoints and 13 October 2026 public OSM snapshot, checked against XML SHA-256 `65f4326133144ea3fcac75cb4d670a0f23fb3a21792d1eca954bc8c286093a52`.
- Run one request per endpoint pair through actual DMN C++, GraphHopper 11.1, OSRM 5.27.1 MLD, OSRM 5.27.1 CH and Valhalla 3.9.1. Five configurations, four engine families. Different car costing remains disclosed; there is no speed or preferred-route-cost ranking.
- An independently authored raw XML judge checks provider geometry without DMN importer, search, matcher or route-repair helpers. Geometry must map uniquely to consecutive OSM nodes/segments within 1.5 m. Ambiguous, simplified, partial, offset or absent attribution stays unresolved; no shortest path is inserted to explain a provider response.
- Categories: route response, connectivity, one-way direction, access, supported node-via turn restrictions, roundabout direction and independent UK legal truth. Conditional/via-way/dimension/permission constraints stay unresolved when not supported. Missing turn/roundabout exposure is unresolved, not a pass.
- Preserve all 500 engine/case rows and 3,500 planned category cells. For every category show correct/judged, failed, unresolved/planned. Category rankings use only the intersection of cases judged for every engine. Overall navigation ranking remains unresolved.
- The judge tests dated OSM semantics. It does not establish current legal permissions from independent signs, traffic orders or first-hand observations. All 500 independent UK-legality cells remain unresolved unless separately evidenced.
- Authored small XML fault controls are unit regressions only, excluded from real-road scores.

## Efficient execution and evidence

One serialized, no-release GitHub job performs source/privacy/native/full-regression checks before provisioning reference engines. No Android rebuild is needed for this host component stage. No optional unavailable engine is silently omitted. Doc-only result commits do not retrigger the workflow.

Outputs: `results/legality/comparison.json`, `rows.json`, `COMPARISON.md`; per-method regression evidence and map checksum retained in the Actions artifact. Exact source SHA/run IDs and permanent reduced snapshots must supplement expiring artifacts.

## Permanent prioritised remaining-work register

| Priority | Work | State |
|---|---|---|
| Critical | DMN-01 conditional/complex restrictions and rejected map areas | Open; conservative judge does not implement DMN support |
| Critical | DMN-02 independently verified UK legal movements | Open; raw OSM-rule comparison is only one supporting check |
| High | DMN-03/04 matching ambiguity and four research arrival failures | Open; heldout-044, 050, 052, 073 preserved in app register |
| High | DMN-05/06 equivalent GPS comparisons and signed junction/roundabout/lane truth | Open |
| High | DMN-07/08 wrong turns, history-safe reroutes, recovery, offline/mobile resource proof | Open |
| Medium | DMN-09/10/11 audio, licensing/distribution and full app session integration | Open |
| Historical | DMN-12 same-map 100-route host benchmark | Complete; prior evidence unchanged |

Before execution: 500 engine-route attempts and 3,500 category cells pending for this new stage. Prior Android stage: 48/48 shared component passes each, 8/8 candidate-only host parity; 176 broader app checks unresolved. Historical research journeys: 16 passed, 4 failed, 80 unresolved; 11 workstreams open. These are different units and must not be added together or overwritten by new host results.

Local preflight: focused RED controls proved missing judge, duplicate-cohort denominator and uncertainty-classification defects before their fixes; focused GREEN suite and full regression result must be checked before upload. Local Docker/OSM service and actual reference-engine execution are unavailable; exact GitHub run is mandatory. Review is limited to this protocol and source change; no ownership/licensing clearance is implied.

Pre-upload verification at base `93a5964ca4b21d0ccedde66a83eced6ddc02804a`: 25/25 new judge/scorecard controls and 6/6 existing response-adapter checks passed. Full suite: 522 recorded methods, zero failures/errors, one existing external-reference skip. Native core was built with warnings as errors; Python compilation, workflow YAML/Bash syntax, staged diff checks and tracked-file privacy guard passed. Independent code review findings were reproduced and corrected before upload. Local reference service runtime is unavailable; no real-road outcome is claimed before Actions.

## First actual comparison and attribution follow-up

Run [38713339259](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38713339259), source `f3f43c1904719086b37e6ba2832dc82f533bcac0`, completed successfully: 500/500 route attempts, zero detected rule violations, 1,796 passing category cells and 1,704 unresolved of 3,500 planned. Full permanent rows: `legality-run-38713339259.json`.

All five configurations returned 100/100 valid responses. DMN, OSRM MLD/CH and Valhalla each passed connectivity/direction/access 100/100 and roundabout direction 12/12 (88 unexercised). GraphHopper had only 16/100 uniquely attributable routes, with 84 unresolved, not failed. Shared judged comparison tied all five at 100/100 responses and 16/16 connectivity/direction/access. No common judged roundabout cohort, no tested turn-restriction cases, no independent UK legal truth; those receive no rank.

Investigation: the GraphHopper adapter retained ordinary import/response geometry simplification. Its documented `routing.way_point_max_distance` and request `way_point_max_distance` settings can disable simplification. Legality mode now requests zero for both, with two new configuration/request regressions. Default speed/comparison behavior stays unchanged. Reference source: https://github.com/graphhopper/graphhopper/blob/11.0/core/src/main/java/com/graphhopper/GraphHopper.java and https://github.com/graphhopper/graphhopper/blob/11.0/web-bundle/src/main/java/com/graphhopper/resources/RouteResource.java. The pinned runtime remains 11.1; only fresh execution can establish the effect. This is a benchmark compatibility correction, not a navigation product fix.

Remaining after first run: 1,704 unresolved cells in this host stage, including all 500 turn-restriction and all 500 independent UK-law cells. Prior 176 broader Android checks, 11 research workstreams, four failed/80 unresolved historical journeys remain unchanged. Next mandatory gap is a genuine real-road turn-restriction cohort with independent truth, not synthetic controls substituted into this scorecard.

Retest preflight at parent `f3f43c1904719086b37e6ba2832dc82f533bcac0`: 27/27 new legality controls and 6/6 adapter controls passed; full suite 524 methods, zero failures/errors, one unchanged skip. Python/YAML/Bash, full staged privacy scan, scope/diff checks passed. Reference engines remain unavailable locally; next exact-SHA GitHub run required.
