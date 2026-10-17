# INTEGRATED-003: offline package and route-context integration

DMN passes **3/3** frozen synthetic cases at source `56603f7`:

| Case | Required result | Verdict |
|---|---|---:|
| valid replacement | Package B activates and the route created under A no longer matches the active package identity | PASS |
| corrupt replacement | Update is rejected; A remains active and its existing route identity remains valid | PASS |
| new replacement route | A route calculated after B activation carries B's exact package digest | PASS |

This proves the research components expose enough identity for a journey owner
to reject a route created from a superseded map. It does not automatically
cancel a controller route, install files, survive process crashes, authenticate
a publisher or exercise Android storage.

Oracle SHA-256:
`b5cecd1c22a7f97bf39f9088888ebc439dad2c58bf04619112aa6bbba9f3bf18`.
Map A SHA-256:
`c2f908d9d0904e6aeb70cfd87c4b36d9af4871d5dd2da215dd37b55e076501cb`.
Map B SHA-256:
`8b9d409865dd0b272456c2b99575c8dd29d3459602db7016377889b9b00ab465`.
[Exact DMN evidence](../references/integrated003-dmn-20261017.json) and
[all-family interface audit](../references/integrated003-scorecard-20261017.json).

DMN's isolated synthetic conformance score is 10/10. External families remain
unranked because their current adapters cannot execute this DMN package-schema
and live route-context contract. No result was mocked or imported from OFFLINE-001.
Single local whole-case timings are diagnostic only. No DMN behavior changed.

Real offline navigation, disk updates, interrupted installation, native routing,
Android lifecycle and independently verified road truth remain untested. The UK
17 correct / 0 confidently wrong / 23 withheld promotion block is unchanged.
