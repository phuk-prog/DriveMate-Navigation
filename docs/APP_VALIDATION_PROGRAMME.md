# Whole-app evidence and improvement programme

Owner authorization extends the test/compare/diagnose/improve/retest approach to
anything the app is responsible for. Navigation R&D remains here; app source,
private architecture and implementation stay in the existing private repository.
This programme changes no production code or dependencies and authorizes no
merge, release, APK, signing/credential change or paid access.

## One repeatable loop

For each component, inventory its exact version/configuration, define its public
contract, freeze a small real applicable workload and justified expectations,
then execute the current implementation and runnable alternatives separately.
Report every case including errors, unsupported features and missing evidence.
Reproduce a verified deficit, implement a scoped reversible improvement, retest
changed cases, safety regressions and additional cases before considering adoption.

Real licensed maps and public source-backed facts are required where applicable.
Only GPS signals are simulated for the requested road tests. Unit controls remain
labelled analytical and never substitute for real-map/app/device evidence.
A competitor, screenshot resemblance or a green build is not the correctness oracle.

## Ranked results and measured units

Correctness:10*passed/frozen judged cases, highest to lowest, ties share rank,
only applicable actually executed comparable cohorts. Unavailable options appear
in a separate audit, never as zero-quality or mocked passes. Original twelve
navigation families remain auditable; navigation competitive cohorts target ten
actually runnable external families. Other app components use genuinely relevant
alternatives/configurations, not ten arbitrarily named navigation engines.

Speed:retain raw milliseconds with workload/map/oracle/version/run hashes,
hardware/runtime, repetitions, timeout/error count and precise measurement scope.
Separate setup, cold first request, warm request, end-to-end network/process/UI,
and predicted journey duration. Only equivalent valid workloads/scopes/hardware
may share a timing rank. Show median,p95,sample count and memory/CPU where measured;
mark unavailable metrics UNAVAILABLE. Small sample counts remain exploratory.
Wrong or missing results cannot win by finishing quickly. No weighted global
score may hide an unsafe route, wrong-road claim, lost data or broken permission.

Freeze target-device budgets before optimization after selecting real target
hardware. Do not invent absolute latency/battery targets without that context.
Track unique base cases, generated variants, repeated measurements and independent
truth records separately. Scale only after the oracle/harness works; bound and
checkpoint large runs. A million variants are not a million independent roads.

## Component register

Every row below is planned whole-app validation, **NOT_RUN as a complete app
cohort**. Existing isolated research evidence is linked separately, not credited
as integrated app success. Candidate comparisons require executable adapters.

| Area | Specific cases | Correctness/error checks | Measured units |
|---|---|---|---|
|Map source/import/update|Known roads, restrictions, borders, partial/corrupt update|Coverage, attribution, provenance, unsupported rules, atomic retention of known-good data|Import/update ms, bytes, peak memory|
|Map rendering|Dense/sparse areas, road classes, night/day, pan/zoom, screen sizes|Visible roads/labels, no missing tiles, map/overlay alignment, readable text|Frame ms,p95, dropped frames, tile ms, GPU/memory|
|Location acquisition|Precise/coarse/denied permission, stale/order/future fixes, gaps|Freshness, safe unavailable state, no personal trace logging|Fix receipt latency ms, recovery time/distance|
|Matching/progress|Real parallel/grade-separated roads, drift, accurate/weak fixes|Wrong-road claims, clear-fix availability, withholding, direction/progress|Update ms, correct/wrong/withheld counts|
|Routing/rerouting|Verified one-way/turn/access cases, wrong turns versus drift|Legal endpoints/path, no illegal recovery, no stale installation|Cold/warm calculation ms, detection delay, route length|
|Instructions/arrival|Forks, merges, roundabouts, parallel destinations, overshoot|Correct outgoing road/exit, timing, no unsupported lanes or false arrival|Instruction timing ms/metres, false events|
|Search/places|Exact/partial address, postcode, misspelling, ambiguous names, offline|Source-backed expected places, relevance, no stale results after query change|Response ms, result accuracy, errors|
|Offline packages|Disconnected start, missing/corrupt map, interrupted install/update|Actual native local route/search, integrity, explicit coverage errors|Download/import ms, storage bytes, recovery ms|
|Storage/history/settings|Restart, migration, interrupted write, invalid/corrupt record|Persistence, defaults, no data loss, privacy/deletion, rollback compatibility|Read/write/migration ms, bytes|
|Networking/providers|Timeout, disconnect, malformed response, rate limit, reconnect|Bounded retry, cancellation, stale-result rejection, no hidden fallback|End-to-end ms, retry/error counts, transferred bytes|
|Startup/UI|Cold/warm launch, navigation across screens, repeated interactions|Usable state, no freeze/crash, state retention, clear errors|Startup/interaction/frame ms, allocations|
|Android lifecycle|Background, screen-off, stop/restart, service kill, permission change|Safe notification stop, no stale guidance, restored context|Resume/recovery ms, crashes/ANRs|
|Accessibility|Large text, contrast, screen reader, touch targets|Readable actionable controls, semantic labels, driving interaction constraints|Task success/errors; measured target sizes|
|Privacy/security|Location consent/retention, export/deletion, logs, provider payloads|No personal GPS leaks, least privilege, safe parsing/storage|Findings by severity, retention/deletion evidence|
|Build/version/update|Version/config changes, install/upgrade/downgrade boundaries|Exact artifact identity and compatibility, verified rollback; no release inferred|Build/test duration, artifact/storage bytes|
|Long runs/resources|Sustained real-map replay, repeated reroutes/searches, low memory|No growing leak, correctness throughout, graceful pressure handling|CPU ms,RSS/heap bytes,battery/thermal on real hardware|

## Current evidence and next execution

[Executed research results](DMN_RESULTS_OVERVIEW.md) consolidates historical
per-case rankings, real-map endpoint probes and available calculation times.
GPS-003 is the next bounded actual real-map matcher/fault/recovery stage; its
source-map labels are not independent real-world road/GNSS truth. Private app
build/dependency and test-file inventory was inspected read-only and saved
locally outside this public repository. Discovered test files are NOT executions;
no app unit, emulator or physical-device pass is claimed here.

Next app stage: establish a reproducible private app unit-test baseline against
its live head, then choose one component's bounded workload. Do not create a
standalone replacement app or publish private source. Device-dependent work
remains unavailable until an appropriate harness/runtime exists. Keep the UK
seven-case coverage regression and source-backed road-law gap visible. The
current adoption decision stays NOT_READY_FOR_LIVE_NAVIGATION.

## Owner-confirmed review gate

The owner selected **stop after each baseline for review**, then explicitly
authorize any improvement/retest. The baseline table, failures and proposed
improvements must be separate items; do not automatically tune from the baseline.
Use available applicable engines now, state their exact count, and keep the
ten-external-engine objective visibly unmet until a common cohort actually runs.
See AGENTS.md for the standing instructions. This supersedes the earlier automatic
improve/retest wording. No permanent scope/rule changes without checking first.

## Resource budget

Each test specification must include a bounded execution budget: maximum cases,
engine runs, retries, wall time, memory/storage and retained artifact size. Reuse
unchanged map/input/oracle hashes and prior successful setup evidence. Prefer one
representative baseline over repeated confirmations; add scale only when a smaller
cohort has demonstrated that the harness and oracle detect the intended faults.

Run focused checks during development and one full affected regression pass before
upload. CI should perform work that cannot be proved locally or from unchanged
retained evidence. Reports should be generated from compact evidence summaries and
links rather than duplicating raw logs. The budget cannot reduce safety coverage,
hide failures or make unlike engines appear comparable.
