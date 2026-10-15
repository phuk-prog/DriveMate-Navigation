# Second actual external GPS reference: Valhalla trace attributes

This adapter implements Valhalla's documented `POST /trace_attributes` with `shape_match:map_snap` and `costing:auto`, on a version-pinned, localhost-only Valhalla container. It reuses the **identical deterministic public UK OSM four-fix scenarios** as the OSRM Match and DMN exercise. Each run reports valid matched points, unmatched points, and snapped points within 20 meters of generated input; DMN's road-edge IDs are tracked **separately** because they are not equivalent to proximity.

An independently surveyed vehicle location/lane and legally signed correct road are still unavailable; all observations are synthetic and map-derived. Map profiles, engine graph generation, OSRM/Valhalla snap semantics and HTTP overhead differ, so **do not compute overall navigation winner or out-of-ten score**. Unit tests use injected fake responses and MUST set `external_reference_families_executed:0`. Only a successful opt-in GitHub Actions live-container run can set it to 1.

Prior baseline: [OSRM live comparison 38752861279](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38752861279), 12 OSRM Match responses / 48 generated points (40 snapped within 20m, 8 unmatched); on the same 12 scenarios DMN single 6 correct edge, DMN temporal 8, 0 confidently wrong. Those are not equal accuracy measures.

Valhalla and OSRM are distinct **families**, while CH/MLD OSRM are variants of the same family. No personal traces, paid provider API or APK involved.

## Execution gate

The Valhalla trace_attributes request/schema unit suite has now passed in [GitHub Actions 38753413439](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38753413439). The first **live** Valhalla comparison is deliberately opt-in on a separate CI commit and remains unverified until its own real container and response artifact complete. The prior local OSRM Match reference has already executed independently on [run 38752861279](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38752861279). Do not treat the unit response mocks as a second live provider.

## Verified live Valhalla GPS results

[Actual Valhalla trace_attributes run 38753612912](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38753612912) **succeeded with 198 Python unit/contract checks** and 12/12 real UK **public map-derived artificial four-fix GPS sequences** served by local pinned Valhalla 3.9.1. From 48 returned tracepoints, **43 snapped within 20 m**, **1 snapped farther than 20 m**, **4 unmatched**; all 12 traces had a response. This shares input source and GPS generated traces with OSRM/DMN but does **not** establish correct road ID, travel direction, legal turn, lane selection or comparable confidence: read [two-family results and limitations](DMN_EXTERNAL_GPS_FIRST_TWO.md). Preserve the artifact `dmn-vs-valhalla-map-match-uk` and no overall ranking.
