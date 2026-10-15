# DMN adaptive testing study — always expand when evidence justifies it

> Added 15 October 2026. **The 72-category / 216-assertion test matrix is a STARTING POINT, not a cap.** The separate 59 proposed modules / 236 checks inventory overlaps it. New evidence can identify previously unrecognized behaviors, new subcategories, tests, modules or independently observable failure types. Preserve all old tests and every historical failure.

## Mandatory discover → verify → test → improve → rerun loop

1. **Record** every new verified failure, unexplained observation, flaky result, competitor divergence, bad GPS/position/speed/timing, unknown legal/lane truth, unsupported capability, missing real-road case, resource spike or unexpected end-to-end interaction. A green status on a tiny subset can itself suggest a coverage gap, but does NOT prove success elsewhere.
2. **Classify** the distinct behavior against `NAV-001..072` and the 59 modular contracts, including separate checks for speed measurement, posted speed limits, ETA and routing computation time. Deduplicate by root failure signature, not simply the error count. One failure can implicate many modules but should not create redundant regressions.
3. **Expand** the test study: append an *evidence-backed candidate* to the discovery queue, with original case, real/public map snapshot, GPS-fault injection or scenario provenance, observable expected/actual, oracle/confidence, affected module, reproduction recipe and severity. If none of the existing categories fits, propose an **additional category and potentially an isolated module**, without renumbering previous IDs or arbitrarily forcing it into 72.
4. **Verify truth before a verdict:** independently confirm turn and U-turn legality where possible; classify absent or disputed sign/lane/speed evidence **UNKNOWN**, not failed or passed. Separate GPS replay input from measured phone sensor performance. Do not acquire or publish private GPS traces.
5. **Implement** a narrowly scoped executable regression with positive, negative, boundary and recovery variants; include a valid real-UK-road scenario plus fault injection as needed. New tests must be runnable, not simply labels. Keep hold-out cases separate; test as many different difficult junction classes as evidence requires.
6. **Compare** DMN and runnable legally accessible external reference engines on matching data/settings where possible. Record not-run/noncomparable references without fabricated scores; manual Google/Waze observations remain separate.
7. **Fix and rerun:** changed check, directly affected modules, nearby interacting modules, prior failures, held-out cases and full start-to-arrival journeys. Recheck GPS, speed, legal maneuvers, lane guidance, prompt timing, offline, resource pressure and arrival, not only geometry. Escalate regressions and newly discovered failure modes into the same loop.
8. **Publish one honest summary** of scores out of ten and descending ranks only on equivalent independently judged tests, plus correct/judged/planned counts, unknowns, failures and new test discoveries. Maintain full machine-readable evidence in run artifacts. Do not confuse planned 216 checks or 236 inventory names with completed test results.

**Acceptance:** This loop stays permanent. A 'complete' batch means every *available, applicable test* ran or was explicitly classified as unsupported/unknown/not-run with reasons; it never means we've learned every possible failure mode. Add further cases whenever results expose a gap. Severe credible new failures block promotion until investigated. New infrastructure may be written from scratch if it improves navigation and complies with ownership/distribution rights.

## Machine-readable discovery tool

`python -m tools.dmn_test_discovery --input results/normalized-observations.json --output results/dmn-discovery-proposals.json`

The input must identify a public non-personal source run and explicit per-case observations. Each observation needs a category/check (or **proposed new category**), unique failure signature, expected/observed behavior, replay recipe, evidence URL and a new executable test description. The program deterministically deduplicates repeated findings and makes reviewable proposals. It **never** marks the new regression executed, changes a score, pulls proprietary data or pushes code. Only implemented/verified tests are later promoted into the maintained suite. Output remains in ignored `results/` for controlled upload as a CI artifact.

For the existing public-road smoke, run:
`python -m tools.dmn_test_discovery --input results/public-road-smoke.json --public-smoke --output results/dmn-discovery-proposals.json`
from a GitHub Actions run (with `GITHUB_RUN_ID`), or supply `--run-url` for reproducible offline review. This identifies the **zero imported node-via forbidden turn pairs** as **UNKNOWN restriction-test coverage**, never as a verified illegal or legal route.

### What has already been highlighted

The real-public-map [8-route experiment](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38726726953) imported **0 prohibited-turn pairs**, so meaningful independently validated real-UK turn-restriction cases must be added before the restriction category can be judged. It measured algorithm cost agreement only; it did not test navigation GPS, vehicle-speed truth, speed-limit truth, lane instructions, traffic, arrival or all twelve reference families. Historical research also identified **4 failed short-approach arrivals and 80 unresolved GPS-replay journeys out of 100**; these are priority regression sources, not new measured results from this branch. They should be linked into the new discovery queue with their original evidence, without copying private traces.

## Boundary and resource guards

Do not automatically grant GitHub Actions write access just to submit newly suggested tests, and do not publish user location data. The discovery tool generates candidates; a reviewed code addition makes them executable. Keep PR-only research changes, controlled CI and minimal repeated setup costs. Use existing GitHub maps/engine caches when allowed, one costly workflow at a time, and no paid provider or APK until separately approved. Production DriveMate is not touched.

## Next executable candidate: bounded real UK OSM turn-rule cases

A new opt-in `[turn-restriction-smoke]` CI stage downloads the fixed public Greater Manchester extract, collects public OSM `type=restriction` relations **with referenced roads/nodes**, strips contributor metadata, and checks candidate node-via mapped turn restrictions against DMN's imported directed graph and routing decisions. It distinguishes valid test cases from unsupported or unavailable relation forms and records aggregate counts, no private road traces. The stage outputs a JSON artifact; any **zero tested restrictions stays a coverage gap**. This checks **adherence to mapped restrictions**, not independently proven UK road legality or real GPS/lane correctness. It must not receive an out-of-ten navigation score. The module `gps/fix_quality.py` and tests separately exercise basic fix validation, timing, heading availability, reported vehicle-speed spikes and coordinate jumps; real phone GPS, road matching and fused-sensor accuracy remain untested.

## Measured second batch and automatic new discovery

[Public-UK OSM turn-rule run 38734700233](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38734700233) passed **133 Python unit/contract checks** and exercised **12 mapped OSM restricted-turn pairs across 12 real UK source cases**. It produced **11 no-route** outcomes from deliberately cropped from/to road subgraphs, plus 1 alternative path. Those 11 are **UNKNOWN** for real full-network detour feasibility. No independent sign/legal oracle, GPS device, lane, voice, or external-engine comparisons ran. See [the detailed measured report](DMN_SECOND_BATCH_RESULTS.md). This exposes a genuinely new regression requirement: evaluate no-route and legal alternatives on **complete buffered public UK road neighborhoods**, not on tiny two-way samples.

The `batch_from_real_turn_probe` analyzer adds a deduplicated **NAV-042** coverage-gap proposal using `--public-turn-smoke`; it does not count as a new executable full-network rerouting test until implemented. The opt-in CI turn-rule artifact now includes its discovery proposal report.

## Bounded detour test discovery from the third batch

The first real UK buffered-neighborhood study found two map-rule detours in the two tested neighborhoods but flagged two further neighborhoods **UNSUPPORTED** because a neighboring restriction referenced a road beyond the selected boundary. This motivated an at-most-once modest boundary expansion, with remaining missing objects still classified as unsupported. See [batch 3 evidence](DMN_THIRD_BATCH.md). Future tasks: independently verify movement legality, assess longer held-out legal detours, compare alternative route qualities, and start GPS/map-matching replays with accurate speed and positioning evidence.

## New real map import capacity gap (15 October)

[Run 38737339329](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38737339329) found that expanding two incomplete public UK junction neighborhoods made their raw extracts exceed the conservative prototype **6 MB importer cap**. That is an **import-capacity limitation, not a verified routing failure**. Prioritize safe prefiltering of irrelevant buildings/footways while retaining drivable roads, barrier nodes and all applicable restrictions; test that conditional motorcar rules still fail closed and rerun the pinned real-data benchmark.

## Confirmed research improvement and remaining source-data issue

[Run 38737832538](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38737832538) demonstrated **3/4** supportable UK OSM restriction neighborhoods versus **2/4** before safely discarding irrelevant non-car map features. All **146** Python unit/contract tests passed. **One** real selected neighborhood remains incomplete (`incomplete_neighbor_restriction`); its source relation must not be silently ignored. Add an independent road-completeness/turn-legality oracle and extra challenging UK junction scenarios. This successful narrow benchmark does not establish actual UK legal navigation safety, traffic-aware rerouting, real device GPS accuracy, any competitor win, or Android arrival correctness.

## Fourth stage: GPS candidate positioning and confidence

Added independent prototype `gps/matcher.py` and [public-UK geometry-derived controlled-error benchmark](../benchmarks/public_gps_matching.py). Run a sequence of fix-quality, directional edge, near-parallel opposing road, degraded accuracy, stale fixes, invalid reported speed and simulated offset tests. Record **correct/ambiguous/unknown/confident-wrong** separately, as well as sample size and whether a true field/oracle was used. A confidently wrong edge is a priority failure; ambiguous on insufficient information is safer than an invented precision claim. This is **not** phone GNSS, IMU fusion, speed-limit source validation or a complete driving navigation session. Expand to multi-fix wrong-road, service/slip roads, bridge levels, turn restrictions, loss/reacquisition and rerouting after measuring first test results.

## GPS second-pass safety study — harder ambiguity checks

After the first 90/90 easy geometry-derived UK fixes, extend evidence to two overlapping opposite-direction mapped links (travel heading matters), parallel **same-direction** nearby roads (position alone insufficient), stopped/heading-less fixes, and clean recovery after a rejected speed spike. Check safe UNKNOWN/AMBIGUOUS responses separately from correct MATCHED values. Add progressively complex true UK road intersections and GPS-replay trajectories; no field GPS truth or device IMU claims are established by injected coordinate tests.
