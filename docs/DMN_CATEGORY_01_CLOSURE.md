# MAP-001 Category 1 closure — new six-region source audit

Owner-authorized implementation on the existing research branch. This
extends Category 1; it does not claim that all UK legal road data is verified.

## Problem addressed

Historical 120-way v3 scorecard is **109 PASS, 9 SAFE_WITHHELD, 2
NOT_JUDGED** on frozen but non-atomic OpenStreetMap extracts. The Manchester
two unjudged relations were subsequently diagnosed, and the DMN importer
was fixed to respect directional motorcar access; rerunning the old v2
oracle would conflate that new runtime with the old, direction-insensitive
oracle. Historical scores must remain unchanged.

This new audit independently derives source-way geometry, one-way flags,
direction-specific motorcar access and endpoint barriers from **exactly
the same six archived v3 map files and 120 original v2 way IDs**:
Manchester, Birmingham, Carlisle, Cardiff, Glasgow and Belfast.

- Check complete per-way edge IDs, endpoints and access values **symmetrically**
  for missing, extra and wrong directions. Failing mutations have unit controls.
- Retain all source unknown/private/destination/access uncertainty as
  **SAFE_WITHHELD**, even if DMN correctly encodes an unknown state.
- Keep conditional and unrecognised input **unjudged/withheld**; never
  reinterpret absent permission as general legal prohibition.
- Inspect selected ways' attached restriction relations for motorcar
  movement availability, missing members, conditional semantics and
  applicability. These diagnostics **do not score complete turn legality**
  or silently discard any original restriction.
- All case-level and region-level SHA-256 checks are mandatory.
- Cross-engine comparison remains in the separately scored native Valhalla
  12-way/108-segment cohort and the four-engine eight-case ordinary-driver
  binary-profile cohort. Do not pool their correctness denominators.
- Engine API success cannot prove full graph completeness. No cross-engine
  speed ranking from unlike HTTP, import/build and native measurement scopes.
- A source-fact PASS is not independent legal validation and the source may
  itself be stale or wrong.

## Actual independent official evidence — carefully bounded

Manchester City Council publishes a **King Street bus gate**: westbound from
Essex Street to Cross Street, permitting buses, black cabs and pedal cycles
but not ordinary cars at all times:
https://www.manchester.gov.uk/parking/tickets-and-fines/bus-gates/the-king-street-bus-gate

This is **independent location-level** evidence. We have not verified that
this restriction's precise geographical extent/orientation corresponds to
frozen source way 155729945 or a particular direction/segment in its old
archive. The evidence is NOT used as a way-specific road-law oracle.

Manchester City Council explains TRO and temporary TRO legal mechanisms:
https://www.manchester.gov.uk/licences-and-permissions/traffic-regulation-orders

DfT maintains the digital TRO API and model:
https://www.gov.uk/guidance/digital-traffic-regulation-orders-d-tro-service
and https://d-tro.dft.gov.uk/api-documentation/

Digital TRO records are machine-readable extracts, **not themselves the
legal orders**; provision and coverage may be incomplete. Other parts of
the UK and historical live signage require their own competent
authority/records. Neither provider-consensus nor frozen OSM alone proves
what a current UK driver is legally entitled to do.

## Immutable comparison and deployment restrictions

Frozen Manchester SHA-256:
`34438baa7a28c55958cd5ba7ac3909a551c51197911963364d27a26eefe8973a`

Source: OpenStreetMap contributors (ODbL), not a signed legal-road survey.
Results are research-only. The exact archived 120 IDs and all old artifacts
are preserved. No hidden access toggles, changes to reference engines,
paid-provider use, personal GPS, merge, app code, APK or Category 2 execution.

Result artifact: `results/map001-category1-closure.json` includes
case-level source-edge comparisons, relation evidence statuses, six hashes,
the proof-gap register and explicit non-comparability labels. Failure of a
new confidently judged source fact blocks the action; unknown is preserved,
not quietly transformed into PASS.

## Remaining genuine blockers

Independent **way- and direction-matched** current authority/signage evidence
for Manchester and corresponding authorities in all six study regions;
vehicle, purpose, effective period and timezone interpretation for
conditional restrictions; complete turn-pair auto-policy inspection
across all four engines; wider equivalent graph adapters across other
lawfully installed references. Unsupported or missing public interfaces
remain explicit, never scored as failed engines.

No promotion to full Category 1 road-law certification until those gaps have
verifiable, dated case-level proof.

## Additional native reference expansion — six regions

The approved second pass upgrades the read-only Valhalla 3.9.1 graph
inspector to accept a named frozen UK region, while leaving the existing
Manchester output and native probe semantics unchanged. The exact same
20 old source way IDs in each of the other five frozen regions are probed
against freshly built, unchanged native Valhalla tiles sequentially.

The workflow compiles the same independent read-only inspector once against
the pinned reference, carries its runtime tooling forward using an ephemeral
runner-local container image (never published), and checks that each region's
installed Valhalla version is 3.9.1. Each result contains the native output
hash and frozen region source hash. The separate six-region summary refuses
missing, wrong-version or mismatched source reports and only ranks genuinely
equivalent directed car-access cases. No scoring for unsupported context
or full turn legality.

Independent legal source verification still requires date/vehicle/extent
alignment; native source-map agreement cannot replace authority records.
The initial Category 1 expansion run 38969822742 passed the six-region
120-way **DMN-source auditor** but failed later due to a GraphHopper 11.1
JAR download returning Maven HTTP 404. Earlier successful runs remain
preserved. The corrected workflow tries both official Maven Central mirrors
and still requires the original JAR's published checksum. A fresh entire
affected Category 1 retest is required before reporting native expansion
results or treating the workflow as green.
