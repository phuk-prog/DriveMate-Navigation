# Run B2 — LANES-001 (category 10) and LIMITS-001 (category 15)

Separate tests, one shared run ([39051017075](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39051017075),
revision `6190d72`). Harness `benchmarks/b2_lanes_limits.py`; truth from the hashed OSM
snapshot's own tags, read by the harness's own parser. Map-derived, not road paint or law.

## LANES-001 — which lanes to use (36 junction movements: 12 left, 12 right, 12 straight)

Approach roads with clean directional `turn:lanes` (only left/through/right arrows).
Correct = exactly the lanes whose arrows include the movement.

| Rank | Engine | Correct / judged | Wrong | No lane answer |
|---:|---|---:|---:|---:|
| 1 | DMN | **35/35** | 0 | 0 (1 not judged: different road) |
| 2 | OsmAnd | 25/34 | 0 | 9 |
| 3 | OSRM | 22/36 | 2 | 12 |

Valhalla, GraphHopper, openrouteservice, BRouter: no lane output (NOT_AVAILABLE).

## LIMITS-001 — speed limit on the road driven (70 roads)

10 roads each with a single mapped 20/30/40/50/60/70 mph limit, and 10 with none (the
correct answer is "unknown"). No road in this map has a clean different limit per
direction, so that kind is empty.

| Engine | Correct / judged | Wrong | Not given | Guessed where none mapped |
|---|---:|---:|---:|---:|
| DMN | 61/61 | 0 | 0 | 0 |
| GraphHopper | 68/68 | 0 | 0 | 0 |
| OsmAnd | 65/65 | 0 | 0 | 0 |

All correct where judged, so not ranked; judged counts differ only by roads an engine
did not drive. OSRM 5.27 has no speed-limit output; the others have none either.

## Harness fixes before this result

OSRM's `annotations=maxspeed` does not exist in 5.27 (first B2 run: all OSRM InvalidQuery);
a zero-length joint between an engine's road pieces was read as "no limit"; OsmAnd's
departure instruction is skipped like every engine's.

## Proposed DMN improvements

None for these cohorts.
