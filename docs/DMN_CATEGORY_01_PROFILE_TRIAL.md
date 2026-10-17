# Category 1: actual isolated-way access-profile trial

Owner requested a profile test following the context-aware importer correction
3b5850d. This stage changes the test harness only. Both engines are exercised
freshly; no engine source/behaviour or production app is modified.

## Frozen contract

Archived Manchester source SHA-256:
`34438baa7a28c55958cd5ba7ac3909a551c51197911963364d27a26eefe8973a`.
Each case is an isolated real OSM way, preserving its directional/access and
barrier source facts. The same generated XML facts feed DMN and Valhalla via a
lossless, sorted PBF conversion. Manifest records each XML hash, parent snapshot
hash and ordered case IDs; conversion hashes are saved. These are isolated access
controls, not tests of the complete Manchester network or independent UK law.
Raw input derivation strips contributor account metadata and uses no personal
journeys. Attribution remains OpenStreetMap contributors; ODbL.

Eight contextual/uncertain ways: 4816180, 4857542, 553071025, 553071026,
553071028, 4721486, 8777654, 27255314. Run three profiles on each (24 checks):
1. Ordinary journey without asserted qualifying purpose/permission: unknown.
2. Declared qualifying destination on the tested way: allowed only for source
   `destination`; it does not grant private authorization or fill missing access.
3. Explicit private permission for the tested way: allowed only for source
   `private`; it does not supply a qualifying destination or missing service rule.

Add forward/reverse controls on King Street 155729945, Princess Street 115559329
and 548694371, and unrestricted way 35277147 (8 checks). Expected total: 32.
Destination/purpose/permission assertions are hypothetical test inputs, never
actual owner authorization or evidence of independently verified road legality.

## Proper reference execution and equivalence

Use unchanged digest-pinned Valhalla 3.9.1 auto. For each of the 12 isolated
inputs, build its graph and run its actual local `/route` API sequentially.
Reuse the installed image, not historical outcomes. Reachability zero permits
small isolated test components; verify returned route endpoints and nonzero
geometry so wrong snapping/empty routes cannot masquerade as correct access.
No ignore-access, ignore-oneway or ignore-restriction bypass is enabled.
Record full bounded requests/responses and distinguish known no-path/no-edge
engine responses from malformed requests or endpoint-correlation uncertainty.
Identical auto requests within one case share a same-execution observation;
we do not pretend a private grant was sent where its API has no equivalent field.

Expected comparable subset: eight ordinary binary direction controls, plus two
qualifying destinations on source destination-only ways (10 checks). Comparison
covers only those exact demonstrated conditions. For the other 22 checks, the
request API does not express the same per-way private permission or explicit
absence of qualifying through-purpose. Mark UNSUPPORTED_PROFILE_MAPPING;
returned routes alone do not prove equivalent legal entitlement. Default auto
can infer destination context from endpoints; an arbitrary penalty reduction
or global ignore flag is not an equivalent scoped permission grant.

Relevant pinned source: DynamicCost supports default destination handling and
private access penalties but no per-way authorized-ID request contract:
https://github.com/valhalla/valhalla/blob/3.9.1/src/sif/dynamiccost.cc and
https://github.com/valhalla/valhalla/blob/3.9.1/src/sif/autocost.cc.

DMN import+route milliseconds and Valhalla HTTP-request milliseconds have different
measurement boundaries and are not speed ranked. Builder/setup time is excluded
from the latter; neither is a live phone benchmark. Preserve the full vs partial
cohorts and unknown outcomes. A green workflow means execution/conformance
succeeded, not that every reference profile was supported.

## Verification before upload

Five new unit methods cover profile mappings, explicit restriction-respecting
flags, known no-route errors versus malformed requests, endpoint-correlation
uncertainty and reverse-prohibition controls. 134/134 map-data and 628/628 full
regression methods pass locally; compilation, privacy and whitespace checks pass.
All 32 DMN route-profile checks also passed locally on the frozen real-way inputs.
Actual Valhalla profile execution requires GitHub; do not infer it from fixtures.
The workflow retains all original graph/access checks, then runs profile builds
sequentially using the same image and bounded loop. Prior evidence is preserved.
No Category 2 trial, Android integration, APK, merge or production change.
