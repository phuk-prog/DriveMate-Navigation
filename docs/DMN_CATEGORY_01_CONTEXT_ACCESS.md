# Category 1: owner-approved permission and destination access

Owner approved replacing blanket private/destination prohibitions with
permission and journey-purpose checks. Base: aed44f6. Android, APK, production
branch, merge and Category 2 remain outside scope.

## Frozen semantics

- An explicit applicable OSM `no` remains a mapped prohibition, not an independent
  claim that current UK traffic law has been surveyed.
- `private` is unknown unless the trusted caller supplies permission for the
  exact source way/node. Permission does not override a more-specific or
  direction-specific `no`, one-way geometry or a blocking physical barrier.
- `destination` is unknown unless the trusted caller declares a qualifying
  destination purpose for that exact way AND the actual destination node belongs
  to it. Coordinate membership alone does not establish entitlement.
- Other purpose/permit tags stay unknown until their own applicability evaluator
  exists. Missing service-road permission stays unknown, even with an unrelated
  permission assertion. Unknown is not labelled illegal and is not assumed open.
- Context IDs are bounded immutable sets, must exist in the exact SHA-256-bound
  map snapshot, and destination grants require an actual destination. Each
  router rejects reuse of a destination-scoped graph for another target.
- Source contextual requirements remain available in an immutable per-edge
  mapping, respecting mode and direction specificity.

`JourneyAccessContext` is a trusted-caller assertion, not a permission discovery
service or legal evidence. This research API does not collect personal permission
information or publish driver data. `import_osm_xml(..., access_context=...)`
creates a journey view. The default map stays context-free. All three routing
entry paths enforce destination binding. Error wording describes missing allowed
routes rather than treating unknown access as proof of illegality.

`OfflineMapStore.route(..., access_context=...)` reconstructs a temporary view
from the active verified source bytes. Neither that view nor permission is saved
into the active base map. This prototype retains bounded source bytes in memory
and reimports for contextual routing; new latency/memory costs are not benchmarked
and no performance improvement is claimed. Map CLI/default callers still use
unknown contextual access until context is explicitly supplied.

## Source input and fair comparison

Same frozen 20 Manchester ways, source SHA-256
`34438baa7a28c55958cd5ba7ac3909a551c51197911963364d27a26eefe8973a`.
Keep all old source/failed execution evidence. Native Valhalla 3.9.1 is freshly
built from the same archive, installed with the established development/runtime
dependencies, and inspected across all three road levels. Engine/profile remain
unchanged. Both engines rerun the complete common 12-way / 108-directed-segment
binary access contract. The other eight remain NOT_JUDGED for road legality.

New `map001_context_access` adds 16 separately labelled policy scenarios across
the eight unjudged ways (eight default and eight hypothetical-context views).
Each includes its exact isolated import-input hash plus the enclosing archived
source hash. Assertions are hypothetical test inputs, never proof the driver
actually has permission or that the current road rule is independently verified.
Valhalla permission-profile equivalence is UNSUPPORTED for these scenarios;
there is no invented multi-engine ranking for them. Its established common
binary source-access comparison remains separate.

Expected no-context change on the eight ways: previously 38 prohibited and 21
unknown edges; now all 59 unknown. Relevant ways: private 553071025/553071026/
553071028; destination 4857542/27255314; unspecified service permission 4816180/
4721486/8777654. Hypothetical exact private authorization allows eight edges;
hypothetical qualifying destination context allows 30; the 21 unspecified-service
edges remain unknown. Permissions never become inferred facts or source-law passes.

## Verification before upload

New controls first reproduced seven failing subcases and nine missing-API errors
against the old implementation. Nineteen new unit methods now cover classification,
way/node permission isolation, destination purpose/binding, snapshot and ID
validation, unknown service access, unsupported time conditions, turn/one-way
preservation, barriers, three routing paths and offline permission non-leakage.
129/129 map-data unit methods and 623/623 full repository regressions pass locally;
16/16 frozen-source policy scenarios pass locally. Compile, privacy and whitespace
checks pass. A test invocation initially omitted the existing route-candidate
snapshot_id argument; the fixture was corrected without altering runtime acceptance.
No fixture is presented as independent UK-road proof.

GitHub exact-SHA native comparison, policy reports and research CI must be read
before claiming final completion. No full Category 1 ranking: contextual access,
independent legal evidence and complete native AutoCost turn evaluation remain
unresolved. Native pair mask 7844440 remains structural evidence only; source
relations 7844441/7844443/7876327 are not silently removed or declared stale.
