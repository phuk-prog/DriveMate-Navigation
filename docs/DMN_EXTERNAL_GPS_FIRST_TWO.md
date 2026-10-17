# First 2 of 12 external GPS reference families — measured UK public-road study

**Pinned identical Geofabrik Greater Manchester snapshot:** `geofabrik-260901`, XML SHA-256 `b3a883ae9b7c85072d24afeee7a1079aea00c22264516a0e1e71d49221ad27d5`.

**Actual GitHub Actions execution:**
- [OSRM MLD 5.27.1 Match run 38752861279](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38752861279), **success**; artifact `dmn-vs-osrm-match-public-uk`; 193/193 Python unit/contract tests.
- [Valhalla 3.9.1 trace_attributes run 38753612912](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38753612912), **success**; artifact `dmn-vs-valhalla-map-match-uk`; 198/198 Python unit/contract tests.

Both containers actually served independent local HTTP matching requests, built from the **same original public OSM subset**, with 12 deterministic, two-contiguous-edge UK map-derived four-fix synthetic GPS traces. Tests use no personal GPS or device data, no licensed commercial API calls. OSRM CH/MLD are **one reference family**, not two.

| What was actually measured | DMN single-fix | DMN temporal (existing) | OSRM Match | Valhalla trace_attributes |
|---|---:|---:|---:|---:|
| Identical generated 4-fix road scenarios submitted | 12 | 12 | 12 | 12 |
| **Correct generating directed edge** on last fix | 6/12 | **8/12** | **NOT COMPARABLE** | **NOT COMPARABLE** |
| **Confidently wrong generating directed edge** | 0 | 0 | **UNKNOWN** | **UNKNOWN** |
| Last edge assignment withheld | 6/12 | 4/12 | Not comparable | Not comparable |
| External matching API returned a route/match result | — | — | **12/12** | **12/12** |
| Returned snapped points within 20 m of generated GPS input | Not assessed as equivalent | Not assessed as equivalent | **40/48** | **43/48** |
| Returned points unmatched | Not applicable | Not applicable | **8/48** | **4/48** |
| Returned snapped points greater than 20 m from generated input | Not assessed as equivalent | Not assessed as equivalent | **0/48** | **1/48** |

**IMPORTANT: DO NOT RANK WINNERS FROM THIS TABLE.** The two DMN figures measure *exact graph edge ID identification* against that same OSM-generated road; OSRM/Valhalla use independently built graphs/profiles and return snapped positions, which could be within 20 m on an **incorrect carriageway, one-way direction, forbidden exit or nearby slip road**. The source itself is not surveyed ground truth. OSRM/Valhalla matcher time scopes and road-profile restrictions also differ. These are **diagnostic different-metric results**, not equivalent correctness scores. A provider responding `Ok` does not prove correct road selection, legal manoeuvre or GPS reliability.

**Next test dependency:** build an independently validated **road/direction crosswalk** (e.g. mapping to source OSM way IDs, supported by authoritative signs/vehicle access and map geometry) and evaluate both the exact-road and proximity cohorts on each engine. Test difficult real UK junctions, dual carriageways, parallel roads, tunnels and slip roads, speed and heading variations, losses/reacquisitions, correct reroute and arrival. No out-of-ten scores before identical independently judged outcomes.

**Other external systems:** GraphHopper is next for actual lawful map-matching interface execution; the remaining **10 of 12** families have NOT been executed in this GPS comparison. The portfolio remains Valhalla, OSRM, GraphHopper, OsmAnd, Organic Maps, BRouter, HERE, Mapbox, TomTom, openrouteservice, Google Maps and Waze. Each must be labeled according to actual feature availability, provider terms and real evidence. Historical routing comparisons are separate from GPS matching.

**Research only:** This runs in `phuk-prog/DriveMate-Navigation` draft PR; production Android `phuk-prog/DriveMate` remains untouched, no APK, no real device GNSS, no sensor fusion, no multi-engine superiority claim.

## GraphHopper third-family comparison attempt (new stage)

A separate genuine local [GraphHopper 11.1 `/match` adapter](../benchmarks/graphhopper_match_reference.py) and [comparison programme details](DMN_GRAPHHOPPER_GPS_BATCH.md) have been added for the same four-fix public UK scenarios. It uses the documented `extended_json` snapped-observation output, with separate unknown/unmatched tracking. GraphHopper is **not** counted as third until an actual matching request has succeeded and its aggregate evidence exists. No 0–10 ranking from snapped-point proximity.

## Third external family tested: GraphHopper (later stage)

[GraphHopper 11.1 actual UK GPS matching run 38759091711](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38759091711) succeeded, bringing the exercised external GPS family count to **3/12** (OSRM, Valhalla, GraphHopper). It made twelve local `/match` GPX requests on the same synthetic four-fix real UK-map-generated cohorts: **3/12** matched all four fixes with unambiguous alignment, **5/12** did not return a matching trace, and **4/12** returned unalignable/partial observations. **12/12 assessable snaps** fell within 20 m of their own synthetic input fixes; **36/48 submitted readings are not independently aligned**. GraphHopper's match completeness appears weaker on this sample, but provider-specific diagnostics and different access/profile parameters are not yet controlled well enough to rank accuracy. See [complete third-stage evidence](DMN_GRAPHHOPPER_GPS_BATCH.md).
