# How the owner will know DMN is ready for the app

**Current decision: NOT READY FOR LIVE NAVIGATION or replacing existing navigation.**
A high synthetic score, fast route or agreement with other engines cannot override
an unresolved safety gate. Reversible prototype integration is research work, not
release readiness. No production app changes or release are authorized by this
readiness inventory.

Run`python -m tools.app_readiness --output results/app-readiness.json` for the
current evidence-backed gate inventory. The report has explicit blockers and no
misleading overall percentage. Historical evidence links remain available.

| Gate | Evidence needed before live adoption | Current state |
|---|---|---|
|Real-map correctness|Frozen real road/one-way/turn/closure cases checked against dated appropriate source evidence; no unresolved critical illegal maneuvers|Incomplete; invented-map controls do not fill this requested programme|
|GPS safety and usable coverage|Same simulated clear/noisy/gapped/speed schedules on real roads; required output on clear positive controls; safe ambiguity handling and recovery|Incomplete integrated proof; UK replay remains17 correct/0 confident wrong/23 withheld versus24/0/16 before|
|Independent expected truth|Expected answers fixed before tuning from appropriate map/authority/survey evidence; conflicts unresolved|Source-backed new case bank not yet established; competitor consensus is not truth|
|Comparable references|At least ten actually executed applicable external engines for the shared requested cohort, with exact versions/configs and same inputs|Incomplete; seven executed routing families across historical scopes do not constitute a ten-engine real-map GPS cohort|
|Component/app integration|Map/context changes, matching, progress, rerouting, guidance and arrival tested together without stale or false instructions|Isolated components exist; integrated replay/app proof incomplete|
|Offline and Android lifecycle|Actual integrated native/local routing; permissions, background, stop/restart, screen-off, loss/recovery|Host Python namespace proof exists; Android/native proof remains unverified|
|Target-device resources and soak|Budgets frozen before tuning for chosen device class and workload; acceptable latency/memory/storage and sustained behavior|Not established by host invented-grid timings; budgets and device/emulator proof pending|
|Safe adoption/rollback|Reversible integration, fallback to existing navigation where appropriate, failure containment and rollback/upgrade checks|Not implemented/verified in the app|

WITHHELD in the UK matcher means DMN did not claim a road confidently. It is
safer than a confident wrong assignment, but it reduces availability and cannot
be hidden when judging usefulness. Conversely an all-withheld engine cannot pass
clear-fix required-output cases. Zero observed confident wrong answers in a small
map-derived sample is not proof of zero real-world error or legal road truth.
The seven UK backward-adjacent cases remain unresolved; do not force matches to
make a coverage target green.

Every completed trial should show real-map/oracle hashes, expected versus actual
per case, exact errors, output coverage, confident wrong road/direction, illegal
turns, false arrival, unnecessary reroutes, recovery delay, and speed/resource
measurements with their scope. An improvement list identifies the evidence,
reproduced DMN cause, fix, changed-case retest, full regressions and extra controls.
No case is dropped or acceptance loosened after seeing a failure.

DMN runs independently against that evidence. Reference engines run separately
on the same frozen inputs, never as DMN dependencies or hidden correctness judges.
Shared CPU/map-cache state, transport overhead, preparation and ambient load can
confound speed comparisons; isolate processes, run heavyweight tests sequentially,
separate cold/warm measurements and record the environment. A winner in one scoped
cohort is not automatically the engine ready to guide real journeys.

The owner requested emulator checks, which may require private ephemeral debug/
test APKs. Those are not release artifacts or a new standalone DMN app. No Android
execution has occurred in this work: no usable local adb/emulator/research Android
project was found. Actual integration/harness/platform evidence must precede any
claim that phone behavior passes. Physical RF, battery and thermal behavior are
not proven by injected emulator coordinates.

This report is a concrete evidence inventory, not certification or a substitute
for the missing work. As stages complete, link their actual runs and update the
gates. Keep draft PR4 and promotion blocked until the required evidence supports
an adoption decision; no automatic merge/release follows from a green test suite.
