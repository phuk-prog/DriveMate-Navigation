# TURN-001 live-head DMN baseline

**Status:** completed DMN-only provisional baseline; no competitive ranking.

This run tested DMN at `a7ab71070be10dcf250800fb390214cc49ebfb46`
against the frozen TURN-001 v1.3 Greater Manchester cohort. The contract uses
OpenStreetMap restriction relations and road tags from a hashed snapshot. It is
real map data, but it is not independently surveyed UK legal truth.

## Inputs and execution

- Frozen cases: 169; testable geometry: 142; discriminating controls: 129.
- Cohort SHA-256: `f2949a8a9aab40b7f62bc658cf92778f440ab5cdcc7ffcc755e21dc1b83c391c`.
- Source PBF SHA-256: `2a8ef8e1f2533cb009b1ce248a6bf4eaabdd47e03979e64e24cd844f3b22acba`.
- Prepared cases SHA-256: `8500d8f3d9cf99660fcc3267ad422134fce87cbb946fe25f6940763546707bf3`.
- Result summary: `references/turn001-dmn-a7ab710-summary.json`.
- Focused regressions: 46/46 passed.

Two setup attempts failed and were retained in the compact evidence: first the
fresh workspace lacked `osmium` and the source PBF; then containerized `osmium`
could not write a newly created mode-0700 wide directory. The complete attempt
used the verified pinned source and ran the tool as the workspace user. The
benchmark resumed only identical-revision work and then completed all 142 cases.

## DMN results

| Verdict | Cases | Meaning |
|---|---:|---|
| PASS | 129 | Avoided the tested restriction, exact endpoints anchored, and whole returned route audited legal against the mapped rules. |
| SAFE_NO_ROUTE | 6 | Returned no route even on the three-times-wider clip; legal but unhelpful and unresolved for coverage. |
| ENDPOINT_WITHHELD_BY_POLICY | 6 | OSM tags barred cars at an endpoint; intentionally not counted as a pass. |
| ENGINE_REJECTED_MAP | 1 | The extracted map contained no motorcar graph edges. |
| FAIL_PROHIBITED | 0 | No route used the tested prohibited turn. |

The six safe-no-route cases are `4853555`, `7615778`, `10558420`, `13613008`,
`14285234`, and `16644804`. The OSM-barred endpoint cases are `4853640`,
`8798974`, `13119340`, `13119370`, `20158895`, and `21197635`. Case `16686773`
was rejected because no motorcar graph edges were extracted.

Local DMN import-plus-route time over 142 samples was 159.8 ms median and
628.5 ms p95 (21.5 ms minimum, 806.0 ms maximum). Wide-clip creation/fallback
work is outside that recorded field. These local timings cannot be ranked
against GitHub-hosted engine timings.

## Ranking and issue register

No engine ranking is valid for this live revision. A four-engine GitHub run
([run 39019749346](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39019749346))
completed successfully on different commit `0668fce`; this session received
HTTP 403 for its artifacts. Reusing those outcomes would violate the exact-SHA
comparison rule. On `a7ab710`, only DMN executed, so OSRM, GraphHopper and
Valhalla are `NOT_RUN` and unranked.

Verified DMN safety fault: none in this cohort (`FAIL_PROHIBITED=0`). Coverage
issues for review are the six safe no-route cases and the one map rejection.
They need case-level comparison against fresh same-SHA legal routes before any
routing behavior change. No behavior or acceptance policy was changed.
