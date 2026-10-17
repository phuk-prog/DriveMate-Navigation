# INTEGRATED-004: active-route safety after map replacement

**Baseline result: 2/3, one reproduced DMN integration failure.** Source
`0971f23`; analytical oracle was frozen first at `9dc301c`.

| Case | Required result | Actual | Verdict |
|---|---|---|---:|
| valid replacement | Activating B invalidates/stops the active route created under A | Controller remained active and retained the A route | **FAIL** |
| rejected corrupt update | A remains active and its route remains installed | A and its route remained active | PASS |
| explicit stop fallback | Caller stops after B activation | Controller became inactive and cleared its route | PASS |

The failing case records package A digest
`c2f908d9d0904e6aeb70cfd87c4b36d9af4871d5dd2da215dd37b55e076501cb`
and active package B digest
`8b9d409865dd0b272456c2b99575c8dd29d3459602db7016377889b9b00ab465`.
The digests differ, but `ReroutingController.begin` accepts only a bare `Route`,
so package identity is not retained and the controller receives no replacement
event. This is a verified component-integration gap, not a real-road observation.

Oracle SHA-256:
`108360c97f6f1ec43a4fd5d5f1412c8b6352609017d7698835b592d6a29ce72c`.
[Exact failing baseline](../references/integrated004-dmn-baseline-20261017.json)
and [all-family audit](../references/integrated004-scorecard-baseline-20261017.json).

DMN passes 2/3, giving an isolated analytical conformance score of 6.667/10;
it is not ranked as a competitive winner. All external families are unranked
because current adapters cannot execute the same DMN package/controller contract.
The full unit suite remains green because its regression explicitly preserves
this known benchmark failure; the benchmark executable exits nonzero.

No behavior fix is included. The narrow proposed correction is to carry an
immutable package/context token into the active navigation context and stop or
require recalculation when activation changes it, while preserving the route on
a rejected update. That change affects live route state and requires owner
approval plus fresh INTEGRATED-004, rerouting, offline and full safety retests.
