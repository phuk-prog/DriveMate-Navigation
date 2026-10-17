# DriveMate Navigation research: owner-confirmed testing workflow

## Every AI: read REGISTER.md first (owner, 2026-10-17)

Several AIs (Claude, Codex, others) work here. **[REGISTER.md](REGISTER.md) is the one
page to read first**: how to keep usage low, what is done (never repeat it), what is
in progress (leave it to its holder), what is pending (start at the top), and where
to find more, cheapest first. Open other files only if your task needs them.
`python3 -m tools.work_status --fetch` gives the same view live across all branches;
`where <topic>` points to a place. Claim work with `start <ID>`, record it with
`finish <ID> --summary --results --run --fingerprint`, queue follow-ups with `plan`.
These rewrite REGISTER.md; commit and push it and `work/` with your work. Register new
data locations with `source` (never personal data or private links: public repo).

## Permanent six-rule policy — owner approved 2026-10-16

Follow [the full permanent testing policy](docs/DMN_PERMANENT_TESTING_POLICY.md) for all future trials: (1) separate rankings for every navigation behaviour; (2) combine executions only where independently accurate and fair; (3) rank by the relevant actual measured metric, with optional correctness scores; (4) keep complete and partial common-case cohorts separately; (5) separate independently verified from provisional/map-derived rankings; and (6) stop for owner approval before fixes, then freshly rerun DMN **and all applicable competitors** on the entire affected comparable cohort after each approved improvement. Every test report must give ranked comparisons, a separate exact-case issue register and proposed improvements. Historical completed case evidence and any original scoring formula remain as recorded; prospective policy governs the next experiments.

## Later owner choice — separately execute all 23 category checks

Use the [ordered independent test catalogue](docs/DMN_SEPARATE_TEST_CATEGORIES.md),
[category register](config/dmn-separated-category-tests.json), and
[isolated CI unit runner](tools/category_test_runner.py). Run one category
at a time, not a combined test. One CI job may invoke independent processes
sequentially to reduce cost. Mark missing tests NOT_RUN; unit PASS never
implies real-road correctness or an external engine ranking. Publish separate
actual multi-engine ranks only for identical valid cases, calculated route
times only on comparable timing boundaries, per-case failures, then proposed
DMN improvements at the end. The later preference for **separate execution**
supersedes the earlier permission for multi-category collection. Preserve
approval before behavioural fixes, full frozen retests and safety gates.

## Standing owner decision (2026-10-16)

Use one named frozen category contract at a time; several categories may share one execution only when each remains accurately measured and independently ranked. Test DMN and every actually available,
applicable reference on identical inputs and a genuinely comparable output
contract. Use available engines now; report the exact executed count rather than
waiting for ten or pretending the minimum-ten objective is met. Original families
and access/interface reasons stay in a separate audit; unsupported engines do
not appear as zero-quality entries in the active ranking.

After each baseline, show the user:
- The test name, exact issues/cases tested and independent/analytical/map-derived
  oracle scope, versions/configurations, map/input/oracle hashes and run/CI links.
- A highest-to-lowest ranking per independent category based on its declared actual
  metric; show exact pass/total/failure/withheld/unresolved counts, optional
  clearly labelled out-of-ten correctness score, full-cohort ranking, and separate
  partial shared-case ranking where applicable. Keep VERIFIED and PROVISIONAL
  evidence in separate ranked tables; include case-level reasons.
- Raw measured calculation times in milliseconds where available. Separate
  cold/warm/setup/process/network scopes, medians,p95,sample count and errors.
  Rank speed only on equivalent valid workload/hardware/measurement scope.
  Journey estimates/maneuver durations are not calculation latency. Missing
  measurements are UNAVAILABLE, never invented.
- Verified faults versus ambiguous evidence, and proposed improvements as a
  separate item. Never declare a generic winner from unmatched cohorts.

STOP AFTER THE BASELINE FOR THE OWNER'S REVIEW. Do not tune DMN, implement
proposed improvements, change acceptance or begin the next trial until the owner
instructs continuation of that step. This explicit review choice supersedes the
earlier automatic improve/retest cycle. Authorized harness setup recovery may
continue before a baseline executes, preserving every failed attempt and inputs.
After an authorized improvement, freshly rerun DMN and **every available applicable
competitor** over the entire affected frozen comparable test set, including
unchanged external engines. Do not reuse historical competitor verdicts as fresh
retests. Also run full affected DMN safety regressions and separately labelled
additional cases; show new separate rankings and before/after DMN changes.
Reuse hashed source maps, downloads and prepared environments only, not old
execution outcomes.

Ask before material uncertainty or a proposed permanent workflow/scope change.
Do not silently switch from the requested comparable baseline to adapter expansion
or a different component. A DMN-only safety regression can be useful, but it is
not a competitive baseline or an engine ranking. Report that limitation plainly.

## Evidence and scope

Use real licensed maps for the requested road comparisons; only GPS observations
are simulated. Keep analytical invented-map unit controls separately labelled.
Source-map agreement and competitor consensus are not independent road/legal/GNSS
truth. Freeze expectations before tuning, retain failures and do not force matches.
UK40-case replay17correct/0confidentlywrong/23withheld and seven lost matches
remain unresolved; no promotion without safely resolving the readiness gates.

The method covers the whole app: rendering, map data, GPS/navigation, search,
storage/settings, networking, UI/startup/accessibility, lifecycle/offline,
privacy/security, builds/updates and resources. Use relevant alternatives for
non-navigation components, not arbitrary navigation engines. Private app inventory
and source remain private/outside this public repository. Test discovery is not
execution. No new standalone app, merge, release, APK, spending, paid provider,
credentials/signing changes, personal GPS, proprietary data, unauthorized scraping,
Waze automation, unsupported access or messages to other people.

Keep heavy references sequential and bounded; no duplicate jobs. Use routine
reversible research branches/draft PRs and nonforced SHA-checked writes. Preserve
progress in docs/DMN_NUMBERED_TRIALS.md and per-trial evidence. Missing tools are
unavailable, never passed. A green research CI or score is not live-app readiness.

## Resource-efficient execution

Minimize Codex tokens, tool calls, CI minutes, downloads, storage and repeated
computation while preserving correctness and auditability:

- Read the smallest relevant files/ranges and summarize retained evidence instead
  of repeatedly loading raw logs or large JSON reports.
- Batch independent read-only checks. Reuse verified hashes, versions,
  maps, frozen cases and successful setup artifacts when unchanged; never
  substitute prior competitor outcomes for owner-required fresh post-fix retests.
- Check active/queued jobs once before launch. Never start duplicate workflows.
- Run focused local tests first. Run the full affected suite once before upload;
  do not repeat unchanged green checks without new code, evidence or a failure.
- Use one baseline execution per frozen cohort. Confirmation runs require a
  concrete reproducibility risk, material nondeterminism or owner request.
- Keep heavyweight engines sequential, use the smallest representative real-map
  extract and case cohort that can expose the tested behavior, and set time,
  memory, retry and output limits.
- Cache/reuse legally obtained public data and prepared engine state when hashes
  prove identity. Do not redownload or rebuild merely to create another run.
- Store compact summaries plus hashes and links. Retain raw artifacts only when
  needed to reproduce a failure or substantiate a result; avoid duplicating large
  evidence in repository files, PR text and chat.
- Keep commentary and final reports concise: show the requested ranking, exact
  failures, timing scope and decision. Link detailed evidence instead of copying it.
- Stop after the owner review gate. Do not spend resources on fixes, retests,
  adapter expansion or the next cohort before authorization.

Efficiency never permits fewer required engines within an applicable baseline,
discarding failures, weaker acceptance, invented evidence, mixed timing scopes or
skipping a check needed to support the claimed result. Record saved/reused work
and any unavailable measurement so lower usage remains auditable.


## Current owner scope — strictly engine research

Implement, test and compare the DMN navigation **engine only**. Do not launch
Android integration, audio/Bluetooth, map UI, emulator, app builds, APK release
or production DriveMate changes. The active independent category catalogue is
21 engine-only categories. Any complete-navigation test is a non-app engine
replay; report absent live GNSS/UK verification honestly. No app readiness claim.


## Latest owner instruction — explicit category start required (supersedes earlier automatic continuation)

The owner wants to **improve and review the tests one navigation-engine category at a time**, then **personally decide when each category begins**. Follow [the 21-category approval queue](docs/DMN_CATEGORY_BY_CATEGORY_APPROVAL.md) and start with [Category 1 map-data test design](docs/DMN_CATEGORY_01_MAP_GRAPH_TEST_DESIGN.md). Never run an existing category unit suite, a new GitHub workflow, a benchmark, or an external engine just because a category review or preparatory improvement is requested. Do not interpret 'next' or 'continue' as permission to start a category. Require an explicit named or numbered start instruction for every category. After its results, stop for review and do not start the next category or implement a navigation behaviour fix without a separate approval. Only **engine research**, no Android app. Preserve all existing engine functionality and both GPS methods.


## Latest owner override — automated engine-category test continuation (2026-10-16)

The owner now explicitly authorizes implementing and running outstanding **research
tests** automatically, advancing to the next separate category test without
another per-category question or start approval. This is a NEWER instruction
that supersedes the older "owner personally starts every category" gate **for
tests and reproducible test-harness corrections only**. Follow the canonical
21-category order in config/dmn-separated-category-tests.json. The normal
research PR CI already executes each category in an isolated subprocess;
tools/dmn_auto_progress.py now checks the fresh case-level reports and writes
a non-fabricated progress/issue register and the next research priority.

Do not pretend that UNIT_PASS means independent road-law, field GPS, native
graph parity, live reference ranking, or whole-category scientific completion.
Where no independently equivalent external engine or case truth exists, keep
UNKNOWN/NOT_JUDGED/NOT_EXECUTED and advance to the next test's diagnostics.
A failed category remains FAILED in the report even when subsequent separate
research tests execute. Investigate the failure; never auto-change verdicts,
delete historical results, bypass safety gates or silently reclassify failures.

No automatic changes to production driving legality, engine routing behaviour
or its accept/reject policy merely to make a test green. Source-modifying
research and behavioural fixes require explicit valid evidence and a fresh
whole affected frozen cohort retest; preserve separate engine comparisons.
No production repo, Android, APK, merge, release, private user data,
proprietary reference automation, paid providers or increased compute budget.
GitHub PR pushes trigger the continuous research unit suite automatically;
an automatic question-advance does not establish a new independent test that
cannot be built from legally usable available evidence.


## Owner instruction — lower usage (2026-10-17)

- One AI per branch: do not push to a branch another AI session is working on;
  use your own branch and merge (never force-push).
- Long multi-engine runs go to GitHub Actions (public repo: free), e.g.
  `.github/workflows/turn001.yml`; read only the job summary
  (`tools/turn001_brief.py` output), not raw logs.
- Start each session from [docs/HANDOVER.md](docs/HANDOVER.md) and end it by
  updating that file in a few lines.
