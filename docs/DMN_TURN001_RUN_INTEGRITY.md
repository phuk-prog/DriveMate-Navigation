# TURN-001 fresh-result integrity gate — 17 October 2026

Scope: research test harness only; **no navigation engine behaviour changed**.

## Why this gate exists

TURN-001 previously loaded any existing \`results/turn001/run-ENGINE.json\`
and skipped its case IDs, even if the routing engine, clip preparation, frozen
cohort or source revision had changed. Its scorer then combined whatever
per-engine files happened to be present. That can make historical results
look like a fresh post-fix comparison. The harness must not silently
reuse old competitor verdicts after an improvement.

## Implemented

Every newly written TURN-001 result now contains \`_provenance\` with
engine name, checked-out source revision, frozen cohort hash, pinned
source map hash, prepared manifest hash and runner code hash. A run can
resume interrupted cases **only if all provenance fields match**.
The scorer rejects legacy results, mixed revisions, changed inputs and
per-case clip-hash mismatches rather than producing a false ranking.

\`run --engine DMN --fresh\` explicitly archives the prior DMN result as
\`run-DMN-prior-<sha16>.json\` before starting a new full applicable cohort.
Use the same \`--fresh\` flag separately for OSRM, GraphHopper and Valhalla
after a change. The prior bytes are preserved. Without \`--fresh\`, a
mismatch stops before executing any case. If a current run was interrupted
and nothing changed, the normal \`run --engine ENGINE\` resumes safely.
The selector refuses to overwrite the existing frozen cohort.

Example when the *same pinned* source and prepared case clips are available:

\`\`\`sh
python -m benchmarks.turn001_restrictions run --engine DMN --fresh
python -m benchmarks.turn001_restrictions run --engine OSRM --fresh
python -m benchmarks.turn001_restrictions run --engine GraphHopper --fresh
python -m benchmarks.turn001_restrictions run --engine Valhalla --fresh
python -m benchmarks.turn001_restrictions score
\`\`\`

The commands are **not** evidence that these reference runs happened in this
change. A full same-source four-engine run remains outstanding until the
pinned PBF, per-case clips and lawful engine runtimes are available and
verified. Do not substitute a newer snapshot or historic reference outcomes.
A different source snapshot requires a separately frozen named cohort,
not a silent overwrite.

The \`tests/test_turn001_run_integrity.py\` suite exercises same-run resume,
cross-revision rejection, prepared/cohort drift, exact-byte archival,
legacy competitor-score rejection, case-clip mismatch and frozen selection.
It uses small synthetic metadata fixtures only. Passing those unit tests
does **not** verify any UK restriction, engine correctness or live ranking.

Separately, the existing INTEGRATED-004 baseline still records one
safety-critical stale active-route failure after a valid offline map
replacement. Unit CI success does not resolve that failure; see
\`docs/INTEGRATED_004_RESULTS.md\`. No automatic engine policy change is
authorised by this test-harness patch.
