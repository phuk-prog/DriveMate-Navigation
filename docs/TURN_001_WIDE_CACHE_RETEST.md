# TURN-001 wide-clip cache correction and affected-cohort retest

**Status:** completed harness correction and fresh four-engine retest. Stop before
any routing-policy change.

The earlier focused diagnosis reported an `ENGINE_REJECTED_MAP` result for DMN
case `16686773`. The cached wide clip used for that fallback was a 92-byte empty
OSM document left by a failed setup attempt. The runner accepted it solely because
the file existed. This was a test-harness fault, not evidence that DMN rejected a
valid map.

The runner now parses cached wide clips and requires both frozen endpoint highway
ways to be present. Invalid files are deleted and regenerated, and generated files
must pass the same check. The check deliberately does not require those ways to be
drivable: private or uncertain endpoint access remains valid evidence and is still
withheld by the engine when permission is absent.

## Provenance and scope

- Run SHA: `a46574b888477a0785eb61fdb5e450b483ab145e`.
- Contract: TURN-001 v1.3.
- Affected cohort: all ten cases whose original DMN base-clip result was `SAFE_NO_ROUTE`.
- Cohort SHA-256: `f2949a8a9aab40b7f62bc658cf92778f440ab5cdcc7ffcc755e21dc1b83c391c`.
- Source PBF SHA-256: `2a8ef8e1f2533cb009b1ce248a6bf4eaabdd47e03979e64e24cd844f3b22acba`.
- Prepared cases SHA-256: `8500d8f3d9cf99660fcc3267ad422134fce87cbb946fe25f6940763546707bf3`.
- Runner SHA-256: `f1fd4ef6de38cf7f20f80d46fcc1ef14ac797f1c8da446057cd070bfd51b0b86`.
- Structured evidence: `references/turn001-wide-cache-retest-20261017.json`.

All four applicable engines were freshly executed on the same ten frozen cases.
The oracle remains the hashed OSM restriction/tag snapshot. Results are
**provisional map-derived evidence**, not independently surveyed UK road-law truth.
This DMN-selected fallback cohort cannot establish general navigation superiority.

## Exact legal-route coverage ranking

Formula: `10 × exact endpoint-anchored legal PASS / 10`.

| Rank | Engine | Score /10 | Pass | Prohibited fail | Unresolved snap | Safe no route |
|---:|---|---:|---:|---:|---:|---:|
| 1 | OSRM | 5.0 | 5 | 1 | 3 | 1 |
| 2= | DMN | 4.0 | 4 | 0 | 0 | 6 |
| 2= | GraphHopper | 4.0 | 4 | 0 | 2 | 4 |
| 4 | Valhalla | 3.0 | 3 | 3 | 4 | 0 |

## Prohibited-turn safety ranking

Formula: `10 × (10 − FAIL_PROHIBITED) / 10`. Safe withholding is not route
coverage, so this must be read with the coverage table.

| Rank | Engine | Score /10 | Prohibited failures |
|---:|---|---:|---:|
| 1= | DMN | 10.0 | 0 |
| 1= | GraphHopper | 10.0 | 0 |
| 3 | OSRM | 9.0 | 1 (`10558420`) |
| 4 | Valhalla | 7.0 | 3 (`10558420`, `13613008`, `14241462`) |

## Per-case result

| Case | DMN | OSRM | GraphHopper | Valhalla |
|---|---|---|---|---|
| 2263040 | PASS | PASS | PASS | PASS |
| 4853555 | Safe no route | Unresolved snap | Safe no route | Unresolved snap |
| 7615778 | Safe no route | Unresolved snap | Unresolved snap | Unresolved snap |
| 10558420 | Safe no route | **Prohibited fail** | Safe no route | **Prohibited fail** |
| 13613008 | Safe no route | Unresolved snap | Safe no route | **Prohibited fail** |
| 13759623 | PASS | PASS | PASS | Unresolved snap |
| 14241462 | PASS | PASS | PASS | **Prohibited fail** |
| 14285234 | Safe no route | PASS | Safe no route | PASS |
| 16644804 | Safe no route | Safe no route | Unresolved snap | Unresolved snap |
| 16686773 | **PASS** | PASS | PASS | PASS |

For `16686773`, regenerating the invalid cache produced wide-clip SHA-256
`c826e9173da51cedf379d26e0850c5bfe1560e6cc158a43ba5672d6241366e5f` and DMN returned an endpoint-anchored 133-node route audited
`LEGAL`. This corrects the earlier false rejection.

Case `14285234` remains unresolved. OSRM and Valhalla turn around using OSM way
`684626149`, tagged `highway=service`, `oneway=no`, with no access tag. DMN treats
an unqualified service road as uncertain and will not use it as a through road.
OSM/competitor agreement is not independent legal evidence, so the retest does
not justify relaxing that policy.

## Calculation time

Only the three equivalent warm-query scopes are ranked. Setup and graph build are excluded.

| Warm-query rank | Engine | Median ms | p95 ms | Samples |
|---:|---|---:|---:|---:|
| 1 | OSRM | 1.3 | 1.6 | 10 |
| 2 | Valhalla | 16.15 | 19.9 | 10 |
| 3 | GraphHopper | 90.3 | 159.9 | 10 |

DMN measured OSM import plus route: 101.3 ms median and 504.7 ms p95 over ten
base-clip attempts. Its wider scope is not ranked against warm reference queries.

## External-family audit and decision

DMN, OSRM 5.27.1 MLD, GraphHopper 11.1 car and Valhalla 3.9.1 auto executed.
OpenRouteService, OsmAnd, Organic Maps and BRouter have no configured compatible
TURN-001 adapter. HERE, Mapbox, TomTom and Google Maps lack permitted configured
credentials and a same-fixture interface; paid calls are not authorised. Waze has
no permitted automated replay interface. These nine families remain unranked.

The harness correction is verified and changes no DMN routing behavior. No route
policy change is supported by the remaining evidence. The separate UK 40-case
coverage tradeoff remains 17 correct, 0 confidently wrong and 23 withheld, so
promotion remains blocked.
