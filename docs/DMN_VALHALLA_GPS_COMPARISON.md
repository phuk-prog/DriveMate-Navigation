# Second actual external GPS reference: Valhalla trace attributes

This adapter implements Valhalla's documented `POST /trace_attributes` with `shape_match:map_snap` and `costing:auto`, on a version-pinned, localhost-only Valhalla container. It reuses the **identical deterministic public UK OSM four-fix scenarios** as the OSRM Match and DMN exercise. Each run reports valid matched points, unmatched points, and snapped points within 20 meters of generated input; DMN's road-edge IDs are tracked **separately** because they are not equivalent to proximity.

An independently surveyed vehicle location/lane and legally signed correct road are still unavailable; all observations are synthetic and map-derived. Map profiles, engine graph generation, OSRM/Valhalla snap semantics and HTTP overhead differ, so **do not compute overall navigation winner or out-of-ten score**. Unit tests use injected fake responses and MUST set `external_reference_families_executed:0`. Only a successful opt-in GitHub Actions live-container run can set it to 1.

Prior baseline: [OSRM live comparison 38752861279](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38752861279), 12 OSRM Match responses / 48 generated points (40 snapped within 20m, 8 unmatched); on the same 12 scenarios DMN single 6 correct edge, DMN temporal 8, 0 confidently wrong. Those are not equal accuracy measures.

Valhalla and OSRM are distinct **families**, while CH/MLD OSRM are variants of the same family. No personal traces, paid provider API or APK involved.
