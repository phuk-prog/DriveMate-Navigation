# DMN engine-first programme — decision baseline (15 October 2026)

> **Status: 22 conversational decisions recorded; detailed scoring methodology and execution are still pending.** Ten reference families minimum, twelve proposed, none assumed fully benchmarked. Passenger-car first, full offline, out-of-ten descending category ranks, precision arrival and all relevant GPS strategies are required. See [the actual answers](DMN_DECISION_QUESTIONS.md).

## Confirmed objective and boundaries

**DMN means DriveMate Navigation.** Develop and compare the most accurate, legally safe and technically capable navigation *system* possible, with the eventual goal of improving the existing `phuk-prog/DriveMate` Android app. **Do not build or ship a second standalone DMN app.**

**Design freedom is intentional.** Do not accept limits in the present Android app, its maps, renderer, road-data pipeline, routing graph, map matching, GPS controller, voice or guidance merely to make a candidate fit. When an identified navigation requirement needs improved supporting technology, investigate alternatives and improve/rebuild the dependency *if justified by evidence*. A dependency improvement may reveal another dependency: follow and evaluate that chain. Existing code is reusable, not sacred.

**Order of work:** independent DMN navigation-engine research and rigorous comparable testing are the *primary* development programme. Develop changes to supporting technology as necessary, keeping affected parts consistent. Use the isolated DriveMate Android integration branch for occasional compatibility and system-level validation, **not** as the design constraint or acceptance oracle. Promote into the actual app only when evidence, interfaces, licensing and agreed acceptance gates justify it. Preserve current DriveMate production `main`; do not publish an APK.

Confirmed standing safety/ownership constraints: prioritize legal routing and navigation correctness over latency; use real UK road map geometry as the main basis, with synthetic cases for targeted failure reproduction; do not call unknown cases passes; preserve historical results; avoid personal GPS traces in public repos; prefer legally redistributable, commercially usable, owned/compatible components without mandatory paid services or seat royalties. Source/data licences, particularly OSM ODbL and provider/API terms, must still be reviewed rather than assumed compatible.

## Scope of the engine-led development programme

Direct navigation work: route computation and costs, legal turns/access and restricted manoeuvres, GPS positioning/map matching and confidence, reroute and recovery, roundabout exits, junction and lane decisions, prompt timing, arrival, route-line-to-map coherence, offline readiness, resource use and navigation reliability. Search/geocoding, map-data ingestion, rendering, traffic, UI, audio, storage, distribution and Android integration are **supporting dependencies** when a measured navigation requirement demands change; they are not separately prioritized UI-design projects within DMN.

### Dependency-change decision rule

1. Record the navigation problem with route/case evidence and confidence (e.g., lane connector unrepresented; prohibited turn offered; route line deviates from map geometry).
2. Identify whether the cause is algorithm, source data, graph, map/routing snapshot mismatch, format/schema, positioning, UI rendering or a combination.
3. Compare at least the credible alternatives: adapt an existing module, extend data/format, substitute an independently licensed component, or author a new one. Include cost, accuracy, freedom to distribute, time, Android resource impacts, and reversibility.
4. Validate the isolated fix on reproducible real UK roads and counterexamples; rerun relevant regressions. Continue into dependent subsystems only if necessary. Track **requirements and dependencies**, not an automatic rewrite mandate.
5. Test the changed component through stable contracts, and finally through DriveMate's isolated Android integration branch when it needs runtime validation. Preserve current Android engine as a control/fallback. Do not ship the candidate merely because a host test is green.

### Decision gates (owner goals fixed; implementation thresholds still to define)

- **Legality gate**: independently supported turns, one-way/access/vehicle conditions and prohibitions; critical errors block promotion. OSM is source evidence, not legal ground truth in every location.
- **Robustness gate**: adversarial and held-out real-road scenarios; route correctness and uncertainty behavior, no invented lane/exits or confirmation without evidence.
- **Fairness gate**: same route origins, destinations, departure/profile/map snapshot and replay where truly possible. Distinguish same-map comparative results from black-box provider observations that cannot share a dataset.
- **Ownership gate**: source, binary, data and derived-data terms examined; no copying proprietary implementations or buying subscriptions without explicit authorization.
- **Integration gate**: Android compatibility, stability, offline, download/update consistency, native memory/battery, safe baseline/fallback and rollback. Emulator tests are useful but not equivalent to a field trial.

## Actual evidence and status (not a projection)

The 15 October register in the DriveMate integration test branch documents:
- 100 Wigan routes in a real-map research cohort with **DMN + four reference configurations** (GraphHopper, OSRM MLD, OSRM CH, Valhalla). CH and MLD are **two OSRM configurations, not two independent providers**. Route response/connectivity/one-way/access each had 100/100 per configuration on this cohort. Unsupported turn-restriction and independent UK legal truth categories remained unjudged. Do not call this a comprehensive twelve-engine (or ten-engine) result.
- Research simulated-GPS journeys on real road geometry: **16/100 fully passed, 4 failed and 80 unresolved**. The four historical failed arrivals were heldout-044, -050, -052, -073, and remain part of the evidence register.
- Android isolated-branch comparison: existing Valhalla Mobile and candidate DMN C++ **48/48 common short-component checks each**, plus 8/8 DMN native-host parity. It does **not** establish complete turn, lane, speech or full-session equivalence.
- Latest evidenced Android returned-path map-rule run [38717929614](https://github.com/phuk-prog/DriveMate/actions/runs/38717929614): **68 judged correct of 112 planned checks, 44 unresolved** (combined engines), no detected failures in judged cells. It does not prove independent road legality. The wider 176 Android category checks are still unresolved.
- **11 of 12** tracked engineering/validation workstreams remained open in that register. Distinct counts are not additive.
- Research legality result [38714110676](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38714110676) and permanent research snapshots remain retained; conclusions must be scoped to the actual samples.

These numbers are a dated baseline, not fresh evidence for the proposed programme. Re-audit before new rankings. Earlier default-branch README/ROADMAP statements saying no real references have ever run, and implying one specific unapproved integration order, are historical, not current evidence.

## Revised working stages (no commitment to exact target counts yet)

**A. Apply confirmed owner decisions.** The 22 spoken questions were answered on 15 October 2026. Do not assume the earlier differently-worded draft was answered. Resolve technical weighting, reproducibility and licence details openly, without inventing agreement.

**B. Establish the reusable comparison spine.** Canonical public road scenarios, immutable map provenance, objective expected results and supported/unsupported capabilities. Make each run report raw counts, per-case diagnosis, execution metadata, map/profile hashes, route geometry correctness and outcome class. Reuse historical tests unchanged.

**C. Compare DMN against at least ten external reference families**, [listed here](DMN_TEN_REFERENCE_PROTOCOL.md); **12 are currently proposed** including Google Maps and Waze as conditional, potentially observation-only references. Add other suitable families when justified; never substitute engine variants for distinct families. Benchmark real executables where feasible. A named reference is not automatically provisioned or benchmarked; isolate black-box comparisons. Treat reference disagreements as diagnostic leads, not majority-vote truth.

**D. Improve navigation core and dependent technology.** Rank safety/correctness failures first, then performance; fix and repeat affected cohort, full regression, held-out tests. If a map/data/graph or renderer gap blocks correctness, work on it as a DMN dependency, rather than accepting a lower-quality engine.

**E. Confirm readiness for app integration.** Mix many cheap targeted replays with fewer complete journeys in the isolated Android emulator branch; physical-device testing comes later. Require full offline, verifiable lane/roundabout guidance, correct-side/entrance arrival, broad GPS/sensor testing, acceptable resources and rollback. **DMN must aim to outperform every fairly comparable tested competitor on each issue, not only match the old engine.** No unsupported universal victory claims, release or production changes without authorization.

## Permanent evidence/reporting contract

Every comparison row MUST record `system + exact version/config + map snapshot/hash + vehicle profile + route/scenario ID + capability + pass/fail/unresolved/unsupported/not-run + oracle/provenance + elapsed metrics (when valid) + failure notes`. Count **correct / judged / planned**, with failures and unresolved separately. Use per-category rankings only for comparable judged cohorts. Overall ranking stays **UNRESOLVED** until preagreed completeness and fairness gates are met; no percent-over-all-tests if omitted cases disappear from the denominator. Record cold vs warm times, same hardware, confidence interval/repeats and resource use; never treat a host-only microbenchmark as app/battery performance. Preserve historical evidence immutably and maintain workstream/open-tests registers with distinct units.

## Assumption and repository cleanup policy

**Stop perpetuating unsourced assumptions in active planning documents.** In particular:
- Do not say we are building another DMN app or that current DriveMate architecture fixes the final design.
- Do not imply **twelve** proposed references (or the old ten) have all been run: the historical ten-system matrix listed targets, many unexecuted. Google Maps and Waze are conditional additions, not permission to access or automate proprietary services.
- Do not treat OSM-only checks as independently witnessed UK legality.
- Do not treat 100% on exercised checks as 100% of planned navigation quality.
- Do not infer a single global speed or quality winner from divergent provider APIs, profiles and data.
- Do not impose an arbitrary roadmap feature such as machine learning, UI redesign or a component rewrite without navigation evidence and an owner decision.

Preserve legacy docs, branches, source and measured artifacts for auditability. The new programme **supersedes their conflicting plans and unsupported status claims**, but it does not delete them or retroactively rewrite results. A separately reviewed cleanup can update status links, archive superseded proposals and remove only verifiably redundant or unsafe material; no mass deletion of code/tests/results. App and data repositories remain outside this planning branch.

## Links

- [Minimum-ten, currently-twelve reference comparison design](DMN_TEN_REFERENCE_PROTOCOL.md)
- [Owner decisions — questions and proposed defaults](DMN_DECISION_QUESTIONS.md)
- [Existing research scope](DMN_SCOPE.md)
- [Current DriveMate integration register](https://github.com/phuk-prog/DriveMate/blob/codex/dmn-integration-tests-20261015/docs/dmn-integration-register.md)

## Agreed scorecard and dependent-system interpretation (15 October 2026)

One owner-facing summary with highest-to-lowest category scores **out of ten** and DMN highlighted; keep full correct/judged/planned/fail/unknown/unrunnable records for audit. An individual unavailable test is unranked and does not prevent testing others. Missing lane data is **UNKNOWN**, not a failure; genuinely wrong verified lane instructions are failures. There is **no predetermined scenario-number minimum**: justify difficulty mix, repeatability and coverage. Legality of turns/U-turns must be established rather than presumed from the appearance of the junction; legal U-turns may be needed at dead ends. Test complexity-first across real UK roads, including control roads. Full offline operation, broad positioning/fusion tests and exact usable vehicle entrance are required. Initially keep the renderer stable but follow evidence-led map/data/graph/rendering dependency changes instead of compromising navigation accuracy. Google/Waze manual observations are non-comparable. The numerical scoring formula/weights remain to be specified **before publishing any new ranks**. See [owner decisions](DMN_DECISION_QUESTIONS.md).

## Executed research evidence update (15 October 2026)

Following the [first eight-route road smoke](DMN_FIRST_BATCH_RESULTS.md), the [second research batch](DMN_SECOND_BATCH_RESULTS.md) executed 12 mapped OSM restriction cases and independent GPS input-quality unit checks. **133 Python unit/contract tests passed**, while the map-only restriction probe reported 11 no-route outcomes on deliberately truncated road subgraphs; these remain **UNKNOWN as full-network reroute verdicts**. The [adaptive test loop](DMN_ADAPTIVE_TESTING.md) now records a specific follow-up regression to test real legal detours with complete public-road neighborhoods. This is not proof of independently legal real-world maneuvers, GPS map matching, corrected speed limits or superiority against other systems. The production app remains unchanged.

## Bounded public UK graph import result (15 October)

The [third batch](DMN_THIRD_BATCH.md) tested four public OSM restricted-turn neighborhoods: the improved strict importer supports **3/4**, exercising three mapped forbidden incoming/outgoing movements with three mapped-rule-preserving bounded alternatives. **One** incomplete restriction is still unranked; 146 Python unit/contract tests passed on the [verified GitHub run](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38737832538). This is map-rule adherence, NOT independent signed UK legality or an external engine score. The adaptive study now retains the unresolved neighborhood and prioritizes correct GPS/position/speed, legal detours and full drives.

## Experimental directed GPS matching evidence (15 October 2026)

The isolated `gps/matcher.py` prototype has started real UK *map geometry-derived* GPS replay, including noise, heading, speed spikes and ambiguity. [Latest recorded run](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38739434272): **163/163 Python tests passed**; 74/90 simulated normal fixes confidently matched their generating directed link, 16/90 withheld as ambiguous, **0 confident wrong**. Complex bidirectional tests: 10/30 correct, 20 withheld, 0 wrong; 15/15 stopped fixes withheld; post-spike 28/30 recovered, 2 withheld. These are **not device GNSS/IMU measurements**, not end-to-end GPS navigation, and not externally compared. See [GPS batch results](DMN_GPS_MATCHING_BATCH.md) and expand the study with sequential matching and road-class adversarial replays. Preserve the production app and licence safeguards.
