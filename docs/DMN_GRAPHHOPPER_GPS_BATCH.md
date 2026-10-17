# GraphHopper 11.1 public UK GPS matching — third reference attempt

The first two external GPS engines actually executed on the same pinned public UK UK-road GPS test are OSRM Match 5.27.1 and Valhalla 3.9.1. This third attempt adds a **genuine GraphHopper 11.1 /match endpoint adapter** using the official `graphhopper-web-11.1.jar` Java 25 server with a separately cached public OSM road graph. It is NOT a GraphHopper routing-only proxy.

**Verified API contract:** [GraphHopper 11.x map matching README](https://github.com/graphhopper/graphhopper/blob/11.x/map-matching/README.md) documents posting GPX to `/match?profile=car&type=json`. The [official 11.x MapMatchingResource](https://github.com/graphhopper/graphhopper/blob/11.x/web-bundle/src/main/java/com/graphhopper/resources/MapMatchingResource.java) offers `type=extended_json`, returning observation snaps in `diary.entries[0].links[*].wpts[*]` where `x` is longitude and `y` latitude. One-to-one fix alignment is counted only if number of returned snapped points equals number of submitted fixes. Otherwise the case is **unaligned/unknown**, not a success. HTTP 404 is an **unavailable matching endpoint**, not a no-match result.

The opt-in experiment launches a real local GraphHopper server with the **same pinned Greater Manchester OSM extract** as OSRM and Valhalla, sends the **same public-map-derived four-fix GPS sequences** through a transient GPX POST, and records its snapped fix proximity plus DMN single-fix/temporal last directed-edge results. Distinct car profiles, OSM graph compilation, metadata, travel direction and match interfaces still prevent a fair navigational safety ranking. The public XML is contributor-metadata stripped and omitted from Git commits and result artifacts. Avoid private traces and retain the Apache 2 licensing of GraphHopper as independent source provenance.

This stage requires a successful actual run. Unit mocks or routing results alone do not make GraphHopper the **third of 12** reference families executed for GPS. All outcomes must be labeled as simulated-vs-map diagnostics, with independently surveyed true vehicle roads and signed legal turns remaining untested. Continue to difficult UK roads, robust direction crosswalk and repeatable multi-family category comparisons after this run.

## Verified actual GraphHopper GPS matching result — 15 October 2026

**[GitHub Actions run 38759091711](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38759091711): SUCCESS**. Source snapshot `geofabrik-260901`, original imported public UK OSM XML SHA-256 `b3a883ae9b7c85072d24afeee7a1079aea00c22264516a0e1e71d49221ad27d5` — same as the preceding OSRM and Valhalla runs. **210 of 210 unit/contract Python tests passed**, plus a genuine locally hosted GraphHopper 11.1 Java 25 `/match` executed. The aggregate-only report was uploaded as artifact `dmn-vs-graphhopper-match-public-uk` (30-day retention).

| Observed on same 12 map-derived UK-road four-fix sequences | Count | Interpretation |
|---|---:|---|
| Actual GraphHopper map matching requests | **12** | Third executable external GPS reference family, not 12 external families |
| Full four-fix aligned matches | **3 / 12** | Only these cases allow per-observation snap distance comparisons |
| No matching result | **5 / 12** | Failure to match this synthetic trace; not independent wrong-road proof |
| Partially returned or unalignable observations | **4 / 12** | **UNKNOWN** per-reading position truth, not a successful trace |
| Properly aligned matched positions | **12 / 48** | Three fully aligned four-fix traces |
| Aligned matched positions within 20 m of injected fix | **12 / 12 aligned** | This is *GPS input proximity* only, not exact directed road identity |
| Unmatched or unalignable observations | **36 / 48** | Includes 5 no-match and 4 unaligned whole traces, not necessarily 36 independently failed points |
| DMN single-fix exact generating directed road | **6 / 12** | 0 confident wrong, 6 withheld |
| Existing DMN temporal exact generating directed road | **8 / 12** | 0 confident wrong, 4 withheld |
| Actual surveyed GPS, real vehicle, signed legal turn truth | **0** | Not evaluated |

GraphHopper run measured a local HTTP median of about **8.9368 ms** for 12 requests, **not a cross-engine speed ranking**. Both the underlying road graph and profile differ from DMN, and GraphHopper `extended_json` observation positions cannot be equated to a verified source OSM directed way/edge. Therefore, **DO NOT** award GraphHopper, DMN, OSRM or Valhalla an accuracy score or declare a winner from these heterogeneous metrics. In particular, `12/12 snapped near input` **does not** mean 12/12 completed or 12/12 were placed on the correct carriageway.

**Discovered follow-up cases:** (i) characterize the five map-matching no-results using nonpersonal aggregate error categories, including whether local OSM graph/profile differ; (ii) examine four partial/unaligned matches without silently assigning their points to wrong input timestamps; (iii) create a common directed-way/heading/geometry oracle across DMN, OSRM, Valhalla and GraphHopper on real UK junctions, service roads, slip roads, bridges and roundabouts, independently corroborated against publicly available actual restrictions/signs; (iv) only then compute a fair score, separate from snapped-point proximity. Continue adding more of the 12 families only where match APIs can be run legitimately without paid services or prohibited scraping.

**No production DriveMate changes, APK, paid calls, personal GPS traces or automatic OSM edits.** One-off GraphHopper CI marker has been cleared.
