# INTEGRATED-005: closure evidence and legal rerouting

DMN passes **4/4** frozen synthetic integration cases at source `579d67c`.

| Case | Traffic decision | Route action | Verdict |
|---|---|---|---:|
| current verified closure, legal detour | `VERIFIED_CLOSURE`, propose | Exact `w:95 → w:100 → w:50` detour | PASS |
| stale closure | `STALE`, do not propose | No route search | PASS |
| unverified closure | `UNVERIFIED_CLOSURE`, do not propose | No route search | PASS |
| verified closure, no legal detour | `VERIFIED_CLOSURE`, do not propose | `NO_ROUTE` | PASS |

Oracle SHA-256:
`f22361414c4630ac8929f9a3a34ee80a3fd39d70e48721dfa2bb4a11491b3178`.
Map SHA-256:
`c2f908d9d0904e6aeb70cfd87c4b36d9af4871d5dd2da215dd37b55e076501cb`.
[Exact DMN evidence](../references/integrated005-dmn-20261017.json) and
[all-family interface audit](../references/integrated005-scorecard-20261017.json).

DMN's isolated analytical conformance score is 10/10. External families remain
unranked because the available adapters cannot consume the identical verified/
stale closure state and expose DMN's integrated decision contract. No historical
route result or mocked traffic response was substituted. Single local case times
are diagnostic only.

The closure facts are declared synthetic inputs. This does not prove a live
traffic provider, current UK closure, source authenticity, road legality or
automatic controller switching. No engine behavior changed. INTEGRATED-004's
stale active-route failure remains unresolved, as does the UK GPS promotion block.
