# DMN comparison: identical final GPS observation vs generating road geometry

This is the **first COMMON final-fix diagnostic** for DMN single-fix, DMN existing temporal matcher, and externally executable OSRM Match, Valhalla trace_attributes and GraphHopper 11.1 Match. Until now DMN's 6/12 and 8/12 measurements represented exact mapped directed-edge identification, whereas competitors' figures represented snapped-GPS-input proximity. Those different outcomes cannot be ranked against each other.

## What this tests

Use the existing **identical 12 OSM-derived UK four-fix traces**, pinned `geofabrik-260901`, and compare the **last returned snapped GPS position** from each candidate against the **same known generating OSM directed-link segment**. The new shared helper `benchmarks/match_geometry_truth.py` projects all returned locations onto the same source-link geometry. For DMN a matched edge is projected onto its own geometry first, just like a snapped fix; an abstention stays withheld. Competing directed OSM edges within 10 metres (including reversed two-way traffic on exactly the same line) are explicitly counted, not treated as independently confirmed road identity.

Per engine (denominator always 12):
- Snapped location **near the generating OSM link (within 5 m)** — *proxy only*.
- Snapped location **farther than 5 m from that link**.
- **Withheld, unmatched or not safely alignable** — no invented success.
- **Other allowed mapped directed edges within 10 m** of a near snap — ambiguity warning, NOT proof of wrong road.

An observed location within 5 m of the generating graph segment can still represent an **incorrect carriageway**, the **wrong driving direction**, or a road whose lines overlap. The graph source is used both for injecting synthetic GPS and as scoring evidence: it is **not independent surveyed GPS truth**. The results must keep `navigation_score=null`, no 0–10 ranking, and no legal/arrival claim. Proximity to *input GPS noise* remains a separate historical metric. This new common proxy does **not replace the necessary independent source-road ID and travel-direction crosswalk**.

## How to execute and interpret

One opt-in local external reference run **at a time** using the existing version-pinned GraphHopper, OSRM and Valhalla GitHub CI fixtures. All three benchmark adapters now emit `common_last_fix_source_geometry_proxy` with exactly the same field schema and denominator for DMN and their own matching output. Only count a reference as actually re-measured after a successful live run and artifact. Keep old historical outputs intact. The next step is a source OSM-way/graph ID correspondence and multi-fix movement-direction validator with independent signs/road evidence, then harder UK roads and additional reference families.

**Privacy and licensing:** only ephemeral, public map-generated observations, no private GPS; no personal data, no app production modification or APK release; use each engine only as independent comparator.

## First CI failure (fixture boundary)

The initial geometry-proxy unit run [38764903859](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38764903859) failed 1/218 tests: a synthetic nearby road at 0.000045 degrees latitude was **slightly more than 5 m** from the expected road according to the meter conversion; the test incorrectly expected the 5 m proximity condition to be true. The fixture was adjusted to 0.000040 degrees (about 4.45 m). **The algorithm threshold stays at 5 m**. This was a test truth-boundary mistake, not evidence that a real external engine failed. Updated matcher tests and real UK comparisons still need to run.
