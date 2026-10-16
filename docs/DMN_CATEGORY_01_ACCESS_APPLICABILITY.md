# Category 1: access applicability and Valhalla direction inspection

Continues owner-authorized Category 1 investigation from `c763fea`.
This stage changes evidence collection and tests only. No importer, graph,
routing or navigation runtime behaviour is changed.

## Frozen cohort and separate meanings

Same original 20 Manchester ways, source SHA-256
`34438baa7a28c55958cd5ba7ac3909a551c51197911963364d27a26eefe8973a`.
Source comes from archived run 38945058272, artifact 12065915414. OSM data is
attributed to OpenStreetMap contributors under ODbL. Source agreement remains
provisional; source capture is not atomic or independently verified road law.

The existing direction contract is unchanged: 12 PASS / 0 FAIL / 0 SAFE_WITHHELD /
8 NOT_JUDGED, 108 directed-edge comparisons. This new report does **not** convert
those eight into legality passes. It explains why they cannot be scored and
separately inspects existing DMN edge access with no asserted authorization or
qualifying trip purpose.

| Source way | Road | Missing applicability evidence | Existing DMN edges |
|---|---|---|---|
| 4816180 | Bow Lane | Service-road motorcar permission unspecified | 7 unknown |
| 4721486 | Ridgefield | Service-road motorcar permission unspecified | 6 unknown |
| 8777654 | New Market | Service-road motorcar permission unspecified | 8 unknown |
| 4857542 | St. Ann Street | motor_vehicle=destination; qualifying trip purpose | 2 prohibited |
| 27255314 | Back Pool Fold | motor_vehicle=destination; qualifying trip purpose | 28 prohibited |
| 553071025 | Unnamed driveway | access=private; authorization | 4 prohibited |
| 553071026 | Unnamed driveway | access=private; authorization | 2 prohibited |
| 553071028 | Unnamed driveway | access=private; authorization | 2 prohibited |

Local archived-source inspection: all 8/8 cases are conservatively withheld
under the specified no-permission policy; 21 unknown + 38 prohibited = 59 edges.
This is an edge-access safety observation, not an exhaustive real-road route
trial. A private/destination tag does not establish an absolute legal prohibition
for every person and every journey. A service road with absent permission is not
proven legally closed. No physical barrier explains these eight in this snapshot.
The report retains the original NOT_JUDGED verdict and identifies needed evidence.

## Valhalla interface correction and fresh execution

`DirectedEdge::forward()` means forward relative to stored EdgeInfo geometry,
not inherently OSM way-node order. New inspection decodes JSON polyline6 and
aligns shape endpoints to unique frozen source nodes before using direction.
Repeated/closed/ambiguous geometry or absent fields remains unsupported. It
records both normal and filtered candidate buckets, graph IDs, end-node IDs,
car-access, destination/not-through flags and explicit schema limitations.

The same fresh /locate responses are saved with the source hash and ordered way
IDs, then reused within that execution. No prior competitor verdict is reused.
Responses and compact derived results are retained as Actions artifacts, not
as repository map copies. Exact response hash is in the applicability report.

Current limitations are confirmed in the pinned Valhalla 3.9.1 source:
- [directededge.h](https://github.com/valhalla/valhalla/blob/3.9.1/valhalla/baldr/directededge.h): `forward` is relative to EdgeInfo storage.
- [directededge.cc](https://github.com/valhalla/valhalla/blob/3.9.1/src/baldr/directededge.cc): JSON omits simple restriction mask, local edge index and opposing index.
- [locate_serializer.cc](https://github.com/valhalla/valhalla/blob/3.9.1/src/tyr/locate_serializer.cc): serializes correlated/filtered candidates, not an exhaustive graph traversal.

No exhaustive turn-pair or missing-edge ranking is possible through this JSON
interface. A native tile adapter is technically a different interface: it needs
GraphReader access to directed edge restrictions and outgoing local indexes,
source-way/geometry identity, connectivity and auto-profile/conditional/complex
restriction evaluation. Per-edge start/end flags alone are insufficient. A
native adapter is not implemented or validated by this stage. The previously
identified BSD-2-Clause OSRM reference remains an alternative; no OSRM equivalence
or execution is claimed here. Valhalla remains an MIT-licensed reference only;
no third-party implementation is copied into the DMN runtime.

## Verification and review boundary

Eight new synthetic test methods cover applicability evidence, permission
precedence, policy-versus-legality separation, malformed shape handling,
geometry orientation, filtered candidates and unsupported pair inference.
101/101 Category 1 and 595/595 repository unit methods pass locally. Compile,
privacy and whitespace checks pass. These fixtures are not real UK-road proof.
Fresh same-source DMN and Valhalla GitHub artifacts must be inspected before
reporting final outcomes. Existing workflow gates and historical results remain.

Remaining priorities: independent service-access evidence; explicit journey and
permission profiles for contextual cases; a native equivalent turn-pair adapter.
Source relations 7844441/7844443 remain inapplicable under the frozen movements,
not proven stale; 7876327 stays uncertain and 7844440 representable. No relation
is deleted or bypassed. No generic engine winner or speed rank is supported.
No Category 2 trial, Android application change, APK, merge or production change.
