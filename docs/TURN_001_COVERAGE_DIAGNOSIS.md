# TURN-001 focused coverage diagnosis

**Status:** completed four-engine focused baseline; stop before DMN behavior changes.

> **Superseded finding:** the `16686773` DMN map rejection below was caused by a
> cached 92-byte empty wide clip, not a valid-map import failure. The corrected
> runner and fresh complete ten-case affected-cohort retest are recorded in
> [TURN_001_WIDE_CACHE_RETEST.md](TURN_001_WIDE_CACHE_RETEST.md). This document
> remains unchanged otherwise as historical baseline evidence.

This diagnostic replays the seven coverage outcomes from DMN's 142-case
TURN-001 v1.3 baseline. Every engine received the same frozen Greater Manchester
clips, origin/destination, headings and route audit. The oracle is the hashed OSM
restriction/tag snapshot, so these are **provisional map-derived** findings, not
independently surveyed UK legal truth.

## Provenance

- Run SHA: `3dd8d255c41236f24175bc0ae94ddf2bd93bd4db`.
- Cohort SHA-256: `f2949a8a9aab40b7f62bc658cf92778f440ab5cdcc7ffcc755e21dc1b83c391c`.
- Source PBF SHA-256: `2a8ef8e1f2533cb009b1ce248a6bf4eaabdd47e03979e64e24cd844f3b22acba`.
- Prepared cases SHA-256: `8500d8f3d9cf99660fcc3267ad422134fce87cbb946fe25f6940763546707bf3`.
- Structured per-case evidence: `references/turn001-coverage-diagnosis-20261017.json`.
- Cases: `4853555`, `7615778`, `10558420`, `13613008`, `14285234`, `16644804`, `16686773`.

Configurations were DMN at the run SHA; OSRM 5.27.1 MLD at its pinned container
digest; GraphHopper 11.1 car with the pinned JAR SHA-1 on OpenJDK 21.0.12.1;
and Valhalla 3.9.1 auto at its pinned container digest.

## Exact legal-route coverage ranking

Formula: `10 × exact endpoint-anchored legal PASS / 7`. A legal route whose
returned geometry did not anchor to both requested road segments remains
`UNRESOLVED_SNAP`, not a pass.

| Rank | Engine | Score /10 | Exact legal pass | Prohibited fail | Unresolved | Safe no route | Map reject |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1= | OSRM | 2.857 | 2 | 1 | 3 | 1 | 0 |
| 1= | Valhalla | 2.857 | 2 | 2 | 3 | 0 | 0 |
| 3 | GraphHopper | 1.429 | 1 | 0 | 2 | 4 | 0 |
| 4 | DMN | 0.000 | 0 | 0 | 0 | 6 | 1 |

This is a deliberately DMN-selected problem cohort. The table identifies DMN
coverage gaps; it cannot establish general engine superiority.

## Prohibited-turn safety ranking

Formula: `10 × (7 − FAIL_PROHIBITED) / 7`. A no-route answer avoids an illegal
route but supplies no navigation coverage, so this ranking must be read with the
coverage table.

| Rank | Engine | Score /10 | Prohibited-turn failures |
|---:|---|---:|---:|
| 1= | DMN | 10.000 | 0 |
| 1= | GraphHopper | 10.000 | 0 |
| 3 | OSRM | 8.571 | 1 (`10558420`) |
| 4 | Valhalla | 7.143 | 2 (`10558420`, `13613008`) |

## Per-case findings

| Case | DMN | OSRM | GraphHopper | Valhalla | Finding |
|---|---|---|---|---|---|
| 4853555 | Safe no route | Unresolved | Safe no route | Unresolved | No competitor produced an exact anchored pass. |
| 7615778 | Safe no route | Unresolved | Unresolved | Unresolved | All returned routes were absent or endpoint-misaligned. |
| 10558420 | Safe no route | **Prohibited fail** | Safe no route | **Prohibited fail** | DMN's withholding avoided the mapped `no_straight_on` violation. |
| 13613008 | Safe no route | Unresolved | Safe no route | **Prohibited fail** | No exact legal competitor route; Valhalla used the mapped `only_u_turn` violation. |
| 14285234 | Safe no route | **Exact legal pass** | Safe no route | **Exact legal pass** | Verified map-derived DMN coverage gap for diagnosis. |
| 16644804 | Safe no route | Safe no route | Unresolved | Unresolved | No exact legal competitor route. |
| 16686773 | Map rejected | **Exact legal pass** | **Exact legal pass** | **Exact legal pass** | Verified map-derived DMN import/coverage gap for diagnosis. |

## Timing

Only identical timing scopes are ranked. Reference figures are warm query time
and exclude graph build/import.

| Warm-query rank | Engine | Median ms | p95 ms | Samples |
|---:|---|---:|---:|---:|
| 1 | OSRM | 1.3 | 1.6 | 7 |
| 2 | Valhalla | 15.2 | 16.1 | 7 |
| 3 | GraphHopper | 80.2 | 84.1 | 7 |

DMN measured OSM import plus route: 95.8 ms median and 530.1 ms p95 over seven
samples. That scope is not comparable to the warm reference queries and is not
placed in their speed ranking.

## External-family audit

Four systems executed: DMN plus three external engines. OpenRouteService,
OsmAnd, Organic Maps and BRouter lack a configured TURN-001 adapter/native
engine harness. HERE, Mapbox, TomTom and Google Maps lack permitted configured
credentials and a same-fixture interface; paid calls are not authorised. Waze
has no permitted automated replay interface. They remain unranked, never zero.
Exact per-family reasons are in the structured evidence.

## DMN issues and proposed improvements

Two evidence-backed coverage issues remain:

1. Diagnose graph reachability and endpoint handling for `14285234`, where OSRM
   and Valhalla both produced an exact mapped-legal route.
2. Diagnose import filtering for `16686773`, where DMN extracted no motorcar
   edges while all three references produced exact mapped-legal routes.

The other five cases do not justify loosening DMN: no external engine produced
an exact legal route, and two cases exposed competitor prohibited-turn failures.
No DMN routing or acceptance behavior was changed in this baseline.
