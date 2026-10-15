# DMN: proposed ten-reference navigation comparison protocol

> **Status: draft targets and method, not ten measured engines.** The target list follows the existing historical `benchmarks/reference-engines.json`, pending owner decisions in [DMN_DECISION_QUESTIONS.md](DMN_DECISION_QUESTIONS.md). *Ten* means ten external reference families alongside **DMN**, not eleven independent real-world runs already completed. This programme compares navigation equipment/components, not complete apps or appearance.

## Provisional reference portfolio

| # | Reference family | Nature / intended comparison | Limits to resolve |
|---|---|---|---|
| 1 | Valhalla | Open-source car routing, manoeuvre generation, matching | Existing app baseline is Valhalla Mobile; clearly label separate versions/profiles |
| 2 | OSRM | Open-source car routing, CH and MLD as **variants of one family** | Route/profile parity and route-matching/controller differences |
| 3 | GraphHopper | Open-source routing and path matching | Engine/profile and batch-vs-live matching comparability |
| 4 | OsmAnd | On-device offline navigation and routing behaviour | Build a legal, runnable reproducible adapter; no app-wide comparison claims |
| 5 | Organic Maps | Offline route and navigation reference | Public engine adapter, map format, turn/lane feature support |
| 6 | BRouter | Custom-profile offline routing reference | Driving profile validity and comparable motor-vehicle access |
| 7 | HERE | Commercial navigation/routing reference | Credentials, API terms, access and cost **not authorised by this list** |
| 8 | Mapbox | Commercial navigation reference | Equivalent map/route inputs often impossible; rights/fees unknown |
| 9 | TomTom | Commercial routing/navigation reference | Equivalent datasets and test GPS/controller access may not be possible |
| 10 | openrouteservice | Open-source reference (provisional tenth in historical registry) | Server/profiles/data availability and parity |

OSRM CH and OSRM MLD are separate *configurations*, not two distinct external families. Compare them separately when useful, never inflate the ten-family count. Potential extra references for later consideration (not automatically substitutes or "top-ranked"): pgRouting, RoutingKit, Navit and Google Maps/Waze as observational black-box outputs **only if lawful/available**. No claim is made that the provisional ten are objectively the ten best systems. User decides whether commercial names and replacements remain.

## Evidence tiers — do not merge them

**Tier 1 — matched road-data experiment**: identical public UK map extract/hash, equivalent car profile and restrictions where supported, same fixed origins/destinations, request type and host, replay inputs and timing scope. Compare routing geometry, legality, coverage and latencies after checking profile parity; write down residual differences.

**Tier 2 — product/provider comparison**: where identical map snapshot, turn policy, internal location replay or traffic feed cannot be controlled, use separately labelled observations with original source/version/date and their terms. May show how a provider responds to a route but *not* an apples-to-apples speed or correctness ranking.

**Tier 3 — historical/unavailable/unsupported**: previous evidence, synthetic-only results, untested provider features, software not installable, restricted endpoints. **No score or rank for an unjudged scope.** `N/T` is never counted as a success.

**Truth hierarchy (to confirm)**: independently verified official traffic orders and signs/surveyed junction evidence where legally available > corroborated authoritative map facts > dated OSM relation/geometry for stated map semantics; competitor agreement is only a diagnostic signal. Conflicts and missing support remain unresolved and receive an evidence-gathering task rather than a guessed legal verdict.

## Test categories — all planned for every applicable engine

1. Response / legal motorcar route connectivity; one-ways, motorcar access, barriers, turn restrictions, conditional and via-way restrictions, U-turns, correct approach side; separately account for absent map data.
2. Route quality (shortest *legal* vs weighted preferred route, distance and estimated time separately), alternatives and deterministic repeatability.
3. Roundabouts: simple, mini, multi-lane, spiral, signalised, nested, unusual exits, restricted movements and signed exit-number correctness.
4. Junctions: crossroads, staggered, motorway/slip-road merges and diverges, grade-separated roads and legal manoeuvre instructions.
5. Lane choice: through/turn combined lanes, bus-only lanes, destination-lane continuations, lane-count confidence and unsupported lane claims.
6. GPS/map matching: urban canyon, dual carriageways, parallel frontage/service roads, slip roads, stacked roads, stops, jitter, false jumps, stale fixes and confidence handling.
7. GPS loss/recovery: tunnels, underpasses, indoor and car-park starts, tree cover, continuous corrupt readings, loss during turns and controlled reacquisition.
8. Rerouting: missed turns, rapid successive wrong turns, inbound-edge legal history, replanning debounce and no illegal U-turn shortcut.
9. Guidance: turn timing at speeds, junction transitions, advance warnings, spoken prompts, roundabout progress, no audio during uncertain match; separate audio output when engine interface does not support it.
10. Arrival: correct vehicle destination/entrance and approach, short final links, adjacent roads, overshoot recovery, avoiding premature/double arrival.
11. Route line adherence and navigation-map synchronization (physical network, bridges/tunnels, roundabout curves; never invent physical lane connectors).
12. Offline reliability, region seams, stale maps, mismatched map/graph generation, update/rollback and storage.
13. Efficiency: cold/warm route p50/p95/p99, time-to-detect-off-route vs time-to-compute, native/Java memory, CPU, battery proxy vs device measured, initial graph and update sizes.
14. Failure handling: timeouts, disconnected/damaged regions, no-route decisions, partial supporting evidence, resource pressure/crashes and recovery.

Test road selection: use an independently selected, version-pinned sample of real UK OSM roads and published attributes, with Greater Manchester/Wigan and the named Manchester roundabouts among proposed priority regions. Expand to UK cities, rural and long-distance motorway drives after approval. Keep directed synthetic graphs for targeted root-cause reproductions; they **never replace** a real-road score.

## Reproducible test pipeline

1. **Coverage inventory:** probe engine binaries, actual API permissions, licence, available adapters and their supported outputs; record `not-run`, `unsupported` and `not-comparable` before generating ranks. Do *not* spin up ten heavyweight stacks in one workflow.
2. **Canonical scenario registry:** case ID, pinned road extract/hash, start/end independent of private journeys, vehicle/time rules, optional GPS replay fixture, expected truth source/confidence, applicable category and mandatory counterexamples. Split development and held-out cases; avoid reusing a scenario to tune then call it held-out.
3. **Cheapest preflight first:** static import, legality-oracle validation, synthetic unit/property tests, native unit tests, interface and datum checks; fail fast. Reuse immutable map caches safely.
4. **Engine execution:** deterministic input, same host/profile where feasible; batch references sequentially or in controlled small sets, with an execution record for every target including omissions. Bound retries and cost. No commercial charges/SDK downloads without permission.
5. **Independent judgement:** check exact returned directed routes and any manoeuvre/lane/arrival outputs against permissible data; distinguish wrong, unobserved, unsupported and map-conflicting. A provider disagreement triggers diagnosis, not automatic correction.
6. **Reporting:** show `pass / judged / planned`, failures, unresolved, unsupported, not-run, route-level reasons, response time and RAM provenance, snapshot/profile versions, request interface, run SHA, CI link. Produce per-category **scoped ranks**, alongside a weighted ranking only if required category evidence is complete and comparable according to agreed rules.
7. **Improve and rerun:** reproduce failure, fix navigation candidate or dependent data/graph/rendering where required, rerun changed cases + full regressions + held-out cohort; retain before/after and release gate trace. Flag regressions.
8. **Hardware integration checkpoint:** only once evidence warrants it, run DMN with the existing DriveMate app on an isolated Android branch/emulator; compare existing Valhalla baseline and DMN. Android test run costs should be minimized; no APK publication.

## Results now versus planned

Existing historical Wigan comparison includes **DMN and 4 external engine configurations**, *not ten family references*; the 100-route legality categories were not all exercised. Separate experimental GraphHopper runs exist, but are not equivalent to a complete ten-engine end-to-end judgement. The current Android cross-engine component check is **48/48 each** for a restricted eight-route cohort; research GPS cohort **16 pass / 4 fail / 80 unresolved**. Existing snapshots and failing evidence must be carried forward without score inflation.

## Proposed decision thresholds, not yet approved

Propose legality and no fabricated driver instruction as hard blockers; approve a minimum real-road coverage denominator per category and region; record acceptable unknown-rate (especially independent lane ground truth); choose how to weight safety vs recovery vs speed; specify allowed use of proprietary references and owner cost ceiling; determine Android/emulator checkpoint frequency. [Answer questions](DMN_DECISION_QUESTIONS.md) before hardcoding thresholds in the scoring pipeline. No overall 100% claim for a sparse exercise.
