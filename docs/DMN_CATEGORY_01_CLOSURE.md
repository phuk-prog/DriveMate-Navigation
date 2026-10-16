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

## Independent authority/corridor correlation

The archived Manchester source geometries were compared with the official
Manchester King Street bus-gate description. Source way **155729945**
starts at the Cross Street junction shared with source way 246124643,
and ends at Essex Street shared with source way 8878437; its reverse
direction is westbound, Essex to Cross. The OSM
`vehicle:backward=no` fact is consistent with the council's
description prohibiting ordinary cars westbound at all times. This is
now a **geographically correlated independent authority statement**, but
not a signed order or a current on-site signage survey.

New test guard: the official correspondence is withheld if any frozen
street identity, shared junction, geometry orientation or directional tag
is inconsistent. The evidence record does not grant permission to other
vehicle classes or fabricate effective-date/legal certification.

## Bounded conditional-syntax diagnosis, not runtime override

The archived UK regional material contains seven selected ways and four
Glasgow turn relations with simple time-window conditions. The bounded
research-only evaluator parses daily local clock intervals with explicit
`Europe/London` timezone and overnight handling, including
Glasgow `no @ 07:00-19:00` and Belfast
`delivery @ (18:00-11:00)`. Complex calendars, bank holidays,
different rule types, absent purpose/permit declarations and stale council
orders remain unjudged; no driver permission is inferred and the existing
conservative importer is not bypassed.

Authoritative context includes:
- Glasgow City Council's 2026 People First Zone programme records,
  which describe a delayed operational bus-gate period:
  https://onlineservices.glasgow.gov.uk/councillorsandcommittees/viewSelectedDocument.asp?c=P62AFQDNUT0G2U810G
- Northern Ireland's pedestrian-zone permits and Belfast vehicle-access
  exceptions: https://www.nidirect.gov.uk/articles/pedestrian-zone-permits
- Belfast City Council's documented delivery period and exceptional access
  requirements:
  https://minutes.belfastcity.gov.uk/mgAi.aspx?ID=49246

These records cannot automatically establish when the 2026 frozen OSM
source became legally effective. New artifact
`results/map001-conditional-syntax.json` separates parsed source
time windows from independently verified permission.

## Preserved native reference startup failure and correction

The first six-region Valhalla runner passed Manchester and Birmingham
native graph inspections but stopped on the next regional build because
the scripted HTTP /status endpoint did not respond. Failed run:
https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38970391800
Birmingham's first native partial cohort (source-derived):
**DMN 11/11 and Valhalla 11/11 ways, 68 directed segment checks each**.

The revised inspector no longer assumes a routing HTTP server is required
to inspect a read-only native graph. It verifies stable completed tile
hashes and that the original container has exited or the service is
healthy, runs the unchanged pinned 3.9.1 native graph reader separately
against those immutable tiles, and keeps per-region startup logs.
If there are no complete native tiles, the trial **fails and records
SETUP_UNAVAILABLE** instead of declaring an engine quality failure.
A fresh six-region retest is required.

## Native reference graph absence is not an incorrect DMN road

The next attempt https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38971214208
freshly confirmed the same Birmingham partial 11/11 comparable native-way
agreement for DMN and Valhalla, but Carlisle's Valhalla scripted build
exited during "Parsing ways" and created **no graph tiles**. It is
incorrect to infer that DMN is better or that Valhalla is unsafe from
a missing native graph. This is a setup/availability limitation.

The coordinator now emits `map001-native-unavailable-<area>.json` with the
exact source hash, unchanged reference engine version, container exit
status and startup log digest, then continues to other regions.
The full 120-way selected cohort is still accounted for, but a native
reference rank contains **only regions with complete inspected graphs**;
unavailable reference rows are not counted as PASS or FAIL.
This protects comparisons from being blocked by one reference startup,
without inventing test outputs or loosening road-safety acceptance.

## Root cause of two previously unavailable native graphs

Read-only logs in successful partial run
https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38971682665
show the exact same setup exception in Carlisle and Glasgow:
`std::runtime_error: Detected unsorted input data`.
The reference importer requires object-sorted PBF input, but this stage had
converted the archived XML with `osmium cat` (which retains original object
order) rather than `osmium sort`. Fix **only** the derived PBF conversion
for the five additional native regions. Do not change the original frozen
OSM snapshots or their SHA-256, case selection, source/access expectation,
Valhalla/DMN behaviour or scoring policy. Record the new derived PBF hashes.
Re-execute all affected Category 1 source, native and route-profile checks;
previous partial, unavailable and failing attempts remain preserved.

## Glasgow Hanover Street: a node-barrier comparison, not a proved engine fault

The first **complete six-region native graph execution**, after sorting
the same frozen source objects, exposed one native access mismatch on
Glasgow source way **827453788**, Hanover Street. Its archived first
node 7725157389 has `barrier=block`, though the way itself has
no explicit car-access prohibition. DMN represents the physical barrier
as prohibited segment access. The unchanged Valhalla 3.9.1 native reader
reported both directed edges `car_access=true` and exposed
additional start/end restriction metadata; **the presence of a native
edge-access flag is not proof the node can be legally traversed**.

Initial full-cohort failure evidence:
https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38972097042
The frozen input and the engine source are unchanged. Full native output,
node barrier and initial provisional FAIL remain archived in this run.
The corrected comparison explicitly classifies any selected way with an
OSM endpoint node barrier as `UNSUPPORTED_NODE_BARRIER_EQUIVALENCE`
(reason field `SOURCE_NODE_BARRIER_NOT_EQUIVALENT_TO_NATIVE_EDGE_CAR_ACCESS`)
and retains source barrier IDs + native directed-edge/restriction indicators.
It must **not** quietly award Valhalla PASS or DMN a competitive safety victory
on this non-equivalent interface. New mutation tests prove explicit
vehicle-way access mismatches without endpoint barriers are still FAIL;
only the genuine ambiguous policy dimensions are excluded.

Independently verified node-traversal and signed legal-road entitlement are
still a separate Category 1 prerequisite before road legality certification.


## Owner-approved remaining Category 1 comparison batch (16 October 2026)

**All 34 previously uncertain-access ways** now receive three executed DMN
import/route profiles: default no asserted right, a deliberately unrelated way
permission, and an exact-source hypothetical permission/destination. Frozen
source classifications: 14 unspecified service ways, 9 private, 8 destination,
2 permit-restricted, and 1 unknown physical node gate. The latter three
categories cannot be unlocked by generic user assertions; permission evidence
is not independently confirmed. Results preserve road-legality NOT_JUDGED.

**Seven conditional source ways** (Glasgow 2 and Belfast 5) are each checked
against the current fail-closed importer and evaluated at four explicit UTC
instants including both winter and UK daylight saving. Four Glasgow timed
turn relations are tracked separately. Parsing a source time window is not
proof of an active legal order or a motorcar permit.

**Native turn and node-barrier inspection** examines all 26 restriction
relations connected to the original 120 selected ways across six freshly
built pinned Valhalla 3.9.1 native graphs. A simple no-turn relation's
restriction-mask bit can be judged against the frozen source only if the
source movement is confidently representable, its via-node geometry and
native graph node match, there is a single native edge pair, and neither
edge signals access, complex restriction or destination context.
Only-turn completeness and physical-node traversal rules remain unsupported
when the native interface cannot prove them. Do not call a native edge
car_access flag a proof of traversability through a block or gate.
Any confidently comparable source-mask disagreement fails the test; full
AutoCost turn legality and UK signed legal truth remain unverified.

Official category-level guidance, not exact signed source-way legal truth:
Birmingham bus gates:
https://www.birmingham.gov.uk/directory_record/136446/moor_street_queensway_outside_moor_street_station
Cardiff traffic access permits:
https://www.cardiff.gov.uk/trafficaccesspermits
Northern Ireland pedestrian-zone permits:
https://www.nidirect.gov.uk/articles/pedestrian-zone-permits
Glasgow People First Zone official project update:
https://onlineservices.glasgow.gov.uk/CouncillorsandCommittees/viewSelectedDocument.asp?c=P62AFQDNUTDNDN0G2U

New evidence artifacts: results/map001-remaining-access.json and
results/map001-native-turn-barrier.json. Preserve historical runs;
no Android app changes, APK, production merge or Category 2.
