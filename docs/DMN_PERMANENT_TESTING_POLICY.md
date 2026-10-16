# DMN permanent category testing, comparison and improvement policy

**Owner approved:** 16 October 2026. **Scope:** DriveMate Navigation (DMN) research on the existing research branch. This policy applies to future trials and approved retests; it does not rewrite historical experiments, frozen acceptance criteria, artifacts, or recorded rankings. AGENTS.md is the entry point; this document gives the complete reporting contract.

## 1. Test and rank each navigation behaviour separately

Maintain independent test identities, evidence, rankings and issue registers for GPS position accuracy; road/direction/map matching; GPS quality, outages and recovery; route computation correctness; route calculation latency; route quality and detours; lawful turn/one-way/access restrictions; junctions and roundabout paths/exits; lane guidance; instruction accuracy and timing; wrong-turn detection; reroute correctness; reroute trigger and calculation latency; traffic/closure response; arrival position/approach; online/offline behaviour; resource usage; and any newly established behaviour. New genuine failure modes become their own reproducible, frozen cases and may require a new category, subject to owner review.

Do **not** collapse GPS, speed, rerouting, legality, roundabouts, lane guidance or any other category into a weighted global score. An engine can rank differently in every category. Keep legality as its own ranking and as an independent safety/release gate; a legal-routing fault cannot be offset by a fast time in a separate category. The test label must say exactly which behaviour and submeasure is judged.

## 2. Combine execution only when individual measurements stay valid

A single real-UK-road journey/replay may collect data for several categories **only** when every participating engine receives an equivalent input, profile, map/source snapshot, timing conditions and test contract, and the measurements remain isolated, attributable, independent and reproducible. For example, a shared journey can separately record navigation path, position accuracy and recalculation if the required interface and ground truth exist.

Otherwise execute a dedicated experiment per category or submeasure. A static routing API cannot be credited with a GPS streaming lifecycle test; an endpoint-only comparison cannot prove correct turns or lanes. Never combine incompatible clocks, host hardware, process/network overhead or inferred journey duration into one speed ranking. Run heavyweight reference engines sequentially and respect bounded budgets. Combined **collection** never creates combined **scores**.

## 3. Rank highest to lowest by the actual category measurement

Declare the primary measurement, direction (higher/lower is better), validity checks, tolerance, sample size, aggregation method and tie rule **before** execution. Rank only equivalent judged cases using the appropriate measurement rather than forcing a ten-point score:
- GPS position: verified correct road/direction and measured location error (metres); show correct/wrong/withheld and error distribution separately. If dimensions conflict, use parallel submeasure tables, not secret weights.
- Route correctness and legality: correct required movements/paths out of the frozen judged total, with wrong/illegal/no-route details.
- Route calculation latency: measured elapsed milliseconds for **valid outputs** under equivalent workload, setup, execution and measurement boundaries; show median, p95, sample count, errors and cold/warm boundaries separately.
- Rerouting: correct route/recovery coverage, missed-turn detection delay and recalculation milliseconds as distinct submeasures; don't allow speed to conceal an unsafe or missing reroute.
- Other categories: use explicit domain units (metres, milliseconds, exits correct/total, instruction timing offsets, bytes, CPU/RSS/battery where actually measured), and split unlike dimensions into separate rankings.

Show full passing/total counts, **failed**, withheld, unresolved and unsupported separately. A 0–10 correctness score such as 10 x passed/frozen judged cases may be an *optional labelled supplemental column* if meaningful; it is **not** the mandatory or universal ranking key. Ties share rank. Do not award fast-but-wrong results a speed victory; publish the validity failure separately. No invented measurements, extrapolated mobile timing, cross-worker speed ordering, or generic engine winner.

## 4. Full and partial comparable engine cohorts are different tables

For **every test**, attempt DMN ★ and every currently available, lawful, applicable reference engine on the identical complete frozen case contract, rather than waiting for a historical target of ten engines. The ten-external-family objective remains visible as unmet until actually executed on one applicable common cohort.

Publish a **main ranking** for engines that execute and complete the same full comparable set. If another engine completes only a subset, give it a **separate partial/shared-subset table**, judged only on identical case IDs supported by all engines in that partial comparison. Do not place an 80-case score alongside a 100-case score as though comparable. An executed supported case that fails its requirement stays a FAIL and in the full cohort; failure must not be reclassified as unsupported to improve rank. For unsupported, missing-credential, inaccessible, blocked or not-run engines, keep a separate named applicability/coverage audit with exact reasons; never score absent engines as zero or as passes. Never manufacture a competitor result from an adapter, proxy, different test or previous stage.

Independently record case IDs, versions/profiles, frozen map/input/oracle hashes, source and timestamp, raw evidence, CI commit/run URLs, exact verdict, reason and actual measured units. Keep results reproducible and auditable.

## 5. Independently verified and provisional evidence stay separate

Freeze expected answers *before tuning*. Publish separate **VERIFIED** rankings for independently justified real-world road/legal/position truths, and clearly labelled **PROVISIONAL** rankings for tests judged against OSM/map-derived, analytical or otherwise unverified expectations. Also label historical invented-map controls **SYNTHETIC / ANALYTICAL**; never imply they verify physical UK roads. Current OSM tags, engine consensus or plausible geometry alone are not independent proof of road law, GNSS accuracy, exits or lane markings.

Investigate source contradictions and record truth as UNKNOWN when it cannot be established. Do not silently score UNKNOWN as pass/fail or change an oracle after seeing engine output. Keep all ambiguity/withheld events visible: safe abstention and required clear-fix availability are different checks. Verified and provisional tables must not be merged into one headline ranking.

## 6. After every baseline: report, ask, improve only with approval, fully retest

Immediately after **every named test**, report to the owner and **STOP for review**. Separate the following blocks:
1. **Test definition:** exact category/submeasure, real routes/cases and issues tested, frozen expectations and whether VERIFIED / PROVISIONAL / SYNTHETIC, map/input/oracle hashes, environment, reference versions and CI links.
2. **Ranked comparison:** highest-to-lowest MAIN full-cohort table (DMN ★ visibly marked) with actual measurements, correct/total, fails, scope and ties; plus any separate PARTIAL shared-subset table and a named unsupported/unrun audit. A DMN-only test is labelled DMN-only conformance, **not** a comparative rank.
3. **Separate failure/issue register:** case by case, engine, expected versus actual, verified defect versus source ambiguity/unsupported/setup error, severity/impact, reproduction and evidence URL. Keep failed tests as failures; UNKNOWN as unresolved.
4. **Proposed DMN improvement:** defect root cause, proposed bounded fix, safety/compatibility risk, expected benefit, regression/holdout tests and whether a changed decision needs owner approval.
5. **Decision required:** wait for explicit owner approval of improvements or of the next experiment; never auto-tune or alter safety confidence/acceptance.

After an improvement is **approved and implemented**, freshly execute **DMN and every currently available applicable competitor** again on the **complete affected frozen comparable case set**, even if competitor versions have not changed. Do not reuse historical competitor *execution results* as the post-improvement retest. Also run full affected DMN safety regressions and separately labelled additional/holdout cases; compare only engines with equivalent supported interfaces in each additional comparison. Present new high-to-low rankings, **BEFORE vs AFTER** DMN values, per-engine results, regressions, remaining faults and the unchanged frozen oracle. A failed fix remains visible; do not discard or loosen cases. Then stop for review again.

## Execution efficiency and hard boundaries

Full fresh competitor retesting after an approved improvement is an explicit owner choice and overrides any older suggestion to rerun **only DMN** or recycle old competitor scores. Resource economy is still required: keep runner and download work bounded, run heavyweight engines sequentially, reuse unchanged **map data, cached builds, inputs, version-pinned assets, manifests and deterministic setup** after hash verification, and avoid duplicate/overlapping jobs. Do not rerun **unchanged baselines** for mere documentation changes or while awaiting owner approval. The requirement to freshly rerun all comparable competitors applies **after an approved behavioural improvement**, not to documentation publication.

Do not modify production DriveMate, automatically merge, release an APK, relax safety/accuracy thresholds, publish unsafe navigation or purchase proprietary access. Ask the owner before any uncertain permanent process/scope/safety change. Live-app readiness requires separately documented real-world independent truth, GPS coverage/safety, integrated navigation, Android/offline/emulator, resource and rollback gates; a green scorecard never overrides those gates.

Historical evidence remains authoritative for what was actually done: `docs/DMN_NUMBERED_TRIALS.md`, `docs/DMN_RESULTS_OVERVIEW.md`, `docs/GPS_003_RESULTS.md`, `docs/DMN_APP_READINESS.md` and the original `references/` artifacts. Applying this policy does **not** itself execute or validate a test.
