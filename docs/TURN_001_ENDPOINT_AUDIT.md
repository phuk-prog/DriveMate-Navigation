# TURN-001 — archived reference-engine endpoint attachment diagnosis

17 October 2026. **Engine-only Category 1**; no new registration, engine installs,
new map downloads, rerouting, category start, Android code or APKs.

## Purpose and method

Investigate the major wrong-road/endpoint-attachment disparity in the archived
[TURN-001 v1.3 four-engine baseline, run 39019749346](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39019749346)
without spending on another full benchmark.

A new [artifact-only analysis, run 39028874337](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39028874337)
**passed**. It reuses the **same 142 base-clip case-level records** for
DMN, OSRM, Valhalla and GraphHopper; validates engine revision, frozen
source/cohort/prepared hashes and identical case IDs, and writes a concise
summary and case-level JSON to the `turn001-endpoint-diagnostic` artifact.

Archived identifiers:
- Source map SHA-256 `2a8ef8e1f2533cb009b1ce248a6bf4eaabdd47e03979e64e24cd844f3b22acba`
- Cohort SHA-256 `f2949a8a9aab40b7f62bc658cf92778f440ab5cdcc7ffcc755e21dc1b83c391c`
- Prepared cases SHA-256 `8500d8f3d9cf99660fcc3267ad422134fce87cbb946fe25f6940763546707bf3`
- Source revision `0668fce23c146158dbfaff3399d329391419e387`.

No new external engine execution took place. This **cannot be presented as
a fresh competitive ranking**, and the raw base-clip counts are not directly
interchangeable with the original published final wide-clip counts.

## Actual observed results

| Engine | Raw base-clip off-target / 142 | Off-target with anchored DMN PASS comparator | Different start only | Different destination only | Both different |
|---|---:|---:|---:|---:|---:|
| GraphHopper 11.1 | 67 | 54 | 41 | 11 | 2 |
| OSRM 5.27.1 | 11 | 4 | 3 | 1 | 0 |
| Valhalla 3.9.1 | 18 | 8 | 0 | 8 | 0 |

The original TURN-001 v1.3 publication used **finalised results** (including
3× wider clip retries for no-route cases), and therefore reported
**68 GraphHopper off-target**. The 67 shown here come from the **archived
initial clip responses only**; they are not a historical correction.

**GraphHopper analysis:**
- Five off-target base responses had no matched OSM node path at all.
- In 54 cases where the DMN comparison route had a verified exact-edge
  PASS on the same frozen case, GraphHopper differed at its *origin*
  alone 41 times, destination alone 11 times, and both ends twice.
- In **41** of the starting-segment discrepancies, GraphHopper's returned
  coordinates still lay within 0.3 metres of the requested start point;
  **12** destination-segment discrepancies were also within 0.3 metres.
- Being geographically very close to a road therefore **does not prove**
  that a navigation system started on the right directed carriageway,
  slip road or junction approach. Loosening the graph anchoring threshold
  would incorrectly pass these cases.

The direct DMN endpoint path is used here **only where DMN passed the
harness's exact frozen OSM endpoint contract**. This comparison supports
an exact segment mismatch, but not any claim of independently verified
road-law correctness or real-vehicle GPS accuracy.

## Recommended investigation before any test adapter modification

1. Keep the strict benchmark oracle: exact origin segment, destination
   segment, heading and turn restrictions.
2. For GraphHopper specifically, inspect public `heading` and route
   point-attachment behaviour using a handful of the **41 verified
   start-segment mismatch examples**. Check whether the reference engine
   received/obeyed endpoint headings and whether conversion of route
   geometry to OSM nodes loses a partial first segment.
3. Separate external engine route behaviour from adapter/harness faults.
   Do not silently reroute to a different road just to award a pass.
4. If a *test-harness correction* is independently justified, freeze a
   new version and retest the affected **full comparable cohort** on DMN
   and all available applicable reference engines. Preserve original
   v1.3 evidence and distinct timing scopes.
5. The owner has prohibited external **registration-dependent** research.
   No new accounts, data subscriptions, or credentials are required for
   this follow-up analysis; if unavoidable, record as diagnosed and move on.

No production driving rule or original test verdict was altered.

## Status

**Completed research diagnosis.** A reproducible, registration-free
artifact-only check confirms substantial GraphHopper wrong-segment
start attachments; root cause (engine snap vs adapter geometry handling)
remains **UNPROVEN**. Future fixes need a separately justified benchmark
contract revision and full retest, not an assumption of fault.
