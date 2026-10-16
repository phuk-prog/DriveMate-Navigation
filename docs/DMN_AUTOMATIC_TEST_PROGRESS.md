# DMN automatic engine-category testing — owner-approved 16 October 2026

## What now runs without asking each question

All **21 frozen category unit-test groups** are automatically executed in
their existing logical order on every active research PR CI revision. The
existing `tools.category_test_runner --all` runs each in its **own subprocess**
and writes immutable-per-run case-level `<category>.json`, `index.json`
and `summary.md`. It **already had this execution behaviour** before this
change. The new `tools.dmn_auto_progress` validates all 21 same-run outputs
against the category register and every recorded case count and writes
`dmn-auto-progress.json` and `dmn-auto-progress.md`. No duplicate category
test passes are launched just to generate the new report.

If one category has a unit failure, subsequent independent test groups
continue collecting their own outcomes; the failure remains visible,
first in the next-investigation priority, and the overall research CI
still **fails**. A category with no measurable tests is NOT_RUN, never passed.
The owner no longer has to answer “start Category N” for research tests.
Unsupported private/proprietary/paid engines are not silently installed or
ranked as zero; reference tools are run only through already authorized
lawful, comparable frozen test contracts.

**Automatic testing is not automatic route-policy replacement.** No test
outcome may rewrite a frozen road truth expectation; no unit-only evidence
may certify current UK road restrictions, physical-GPS accuracy, roundabout
lane signs, traffic legality or external engine ranking. Future road
experiments must define a reproducible, legally usable oracle and identical
actual applicable competitors for that *specific* category. One test category
being research-provisional does not suppress independent tests of others.
The difference is explicit in every per-category report.

## Research CI wiring

- Trigger: existing pull_request CI whenever the active draft research branch
  is pushed, and main push (original behaviour). This also covers new
  automatically committed test additions. A completed successful CI does
  not, by itself, create infinite GitHub Actions or code modifications.
- Sequence: privacy guard, compile, **all 21 separate category subprocesses**,
  fresh automatic case-level cross-check/report, artifact upload. Existing
  bounded category-specific research batches remain in their normal CI
  locations. No additional heavyweight engine CI is launched by the
  auto-progress summariser itself.
- Evidence: GitHub Actions artifact `dmn-independent-category-tests`, now
  containing both original results and `dmn-auto-progress.*`.
- Priority: first failed or unimplemented category, else first category
  awaiting stronger independent road and applicable competitor evidence.
  A unit PASS is never falsely promoted to an engine or legal ranking.
- Fail-closed: absent individual JSON, truncated case counts, false navigation
  scores, tampered identity/order and unknown statuses fail the analysis.

## What still requires genuine new evidence

A comprehensive four-engine road-legality score, independent current road-law
facts, signed orders, contextual permission entitlement, lane/sign surveys,
on-device GNSS accuracy, comparable speed workers and fully equivalent native
AutoCost turn/node traversal are **not automatically created** by a unit
runner. They stay not judged until supported data and methods exist.

Do not release an APK, merge draft PR #4, open/change private Android
repository `phuk-prog/DriveMate`, access personal data, submit public OSM
comments, change commercial licences or run paid provider services.
Do not generate infinite CI loops, and preserve GitHub resource limits.
The previously owner-controlled category start document remains as
historical context with a newer superseding notice.
