# Category 1: prospective Manchester directional-access contract

Scope: ordinary motorcar, archived v3 Manchester OSM; no navigation/runtime,
Android, APK, production-branch or category-start change. Original v1/v2/v3 and
Valhalla failures remain historical evidence. This is a new isolated-way audit,
not a replacement score or a full relation-context retest.

## Reproducible contract

- Base: `ed9b0a3ce0df7cb325b8ebda048dcd04ccb824e5`, existing PR 4.
- Frozen archive: run [38945058272](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38945058272), artifact 12065915414.
- ZIP SHA-256: `577a5d99da2731dda7e44e2ca353e9270c6236f4a500b9868b8dbfd555dd5208`.
- Manchester bytes SHA-256: `34438baa7a28c55958cd5ba7ac3909a551c51197911963364d27a26eefe8973a`.
- Exactly the original 20 Manchester way IDs. No newly fetched map, personal trace
  or alternative case selection. The v3 closure snapshot is not atomic.
- `benchmarks/map001_direction_contract.py` is an evidence-only source oracle.
  Reports include oracle and importer hashes. Most specific car mode wins;
  within that mode the directional tag overrides its general value. Bus/taxi/
  bicycle permission does not grant ordinary-car permission. Unsupported car
  one-way exceptions and conditions remain unknown; contextual access needs a
  profile and cannot be equated with a hard boolean denial.
- Missing/extra directed edges and wrong endpoints/access are reported separately.
  Existing symmetric missing/extra turn-pair mutation controls remain active.
  Relation viability does not prove turn-pair correctness or road-law validity.

## Root cause and affected components

`map_data/osm_xml.py::_road_access` reads only `motorcar`, `motor_vehicle`,
`vehicle`, `access`. The edge builder computes one access value per way/segment
and assigns it to both orientations; `*:forward` and `*:backward` are absent
from that path. Eight synthetic controls reproduce this omission for four keys
in two directions. No runtime correction has been applied.

`RoadEdge.access` carries the resulting value into graph traversal; route and
map-matching consumers of imported graphs inherit it. `map_data/offline.py` and
`map_data/__main__.py` call the same importer. These are affected code paths,
not claims that every consumer has been independently tested here.

The older source oracle `benchmarks/map001_v2.py::source_edges` likewise uses
one undirected access value. v3 calls that audit before its symmetric turn-pair
check. Thus 109/120 historical passes do not exclude directional-access defects.
The follow-up diagnostic had directional denies, but its merge semantics and
boolean treatment of private/destination permission are insufficient as a general
oracle. It remains unchanged to preserve the old evidence; new evaluation is
explicitly separate. Valhalla's prospective candidate evaluation now uses the
new source contract, including unknown handling before one-way judgments.

## Local results before upload

85/85 Category 1 unit tests passed, including 23 new methods with additional
subcases. Compile, privacy and whitespace checks passed. Unit controls include
one-way orientations/exceptions, roundabouts, mode overrides, eight importer
directional-denial reproductions, contextual access, condition withholding,
barriers, extra/missing edges and turn prohibitions, relation exceptions,
incomplete members and unsupported via-way shapes. These invented-map controls
are not UK road proof. Only Category 1 was manually executed.

20 real-map isolated-way cases; 108 scored directed-edge comparisons:

|Engine/scope|Passed|Failed|Withheld|Not judged|Unsupported|
|---|---:|---:|---:|---:|---|
|DMN ★ isolated-way direction/access|9|3|0|8|Full turn-pair legality not scored|
|Valhalla matching exhaustive contract|—|—|—|—|Exhaustive edges and turn pairs unavailable|

No comparative rank is justified by these different interfaces. Eight unjudged
cases need contextual permissions/barrier evidence or unsupported semantics;
no ambiguity is counted as an engine pass. Runtime is unchanged; before/after
behaviour improvement and performance ranks are unavailable.

## Exact issue register, highest severity first

1. **DMN source-access defect:** King Street way `155729945`, five backward
   segments `w:155729945:0:r` through `:4:r`, source `vehicle:backward=no`,
   observed `allowed`. Bus/taxi/bicycle designated exceptions do not apply to
   ordinary cars. Same defect affects Princess Street ways `115559329` and
   `548694371`: five backward segments each, 15 mismatches total. This is frozen
   OSM agreement evidence, not independent verification of current traffic law.
2. **Harness false reassurance risk:** old undirected oracle omitted these tags.
   New independent edge contract detects the defect without changing runtime or
   replacing old reports. An evidence-collection job succeeding is not an engine
   acceptance pass: inspect the explicit FAIL counts.
3. **Source applicability:** relation `7844443` has no available ordinary-car
   movement under source interpretation; Cross Street relation `7844441` targets
   a one-way destination with no departure. They remain in evidence. Neither
   result establishes that the relation is stale or invalid. Relation `7844440`
   (`no_u_turn`, Cross Street way `246124643`) has a representable movement;
   relation `7876327` remains unresolved because adjacent access is unsupported.
   No restriction was dropped from runtime import or routing.
4. **Competitor interface:** spatial `/locate` candidates do not prove absent
   edges, exhaustive connectivity or exact turn-pair legality. Valhalla 3.9.1
   [DirectedEdge JSON source](https://github.com/valhalla/valhalla/blob/3.9.1/src/baldr/directededge.cc)
   comments out `restrictions`, `opp_index` and local edge indexes in JSON.
   New reports count available graph IDs/end-node IDs/simple masks explicitly.
   A native GraphReader/tile adapter plus auto-profile restriction evaluation may
   be feasible, but is not implemented or validated by this serializer study.
   No Valhalla engine defect is established by absent JSON fields.

If a native Valhalla adapter cannot provide equivalence, OSRM v5.27.1 is a
candidate alternative reference: its [BSD-2-Clause terms](https://github.com/Project-OSRM/osrm-backend/blob/v5.27.1/LICENSE.TXT)
allow redistribution with notices. No equivalent OSRM graph adapter or result is
claimed. Preserve OSM ODbL attribution and data obligations separately.

OSM interpretation references: [direction terms](https://wiki.openstreetmap.org/wiki/Forward_%26_backward%2C_left_%26_right),
[access hierarchy](https://wiki.openstreetmap.org/wiki/Key:access),
[conditional restrictions](https://wiki.openstreetmap.org/wiki/Conditional_restrictions).

## Review boundary

The Category 1 facts workflow will freshly run DMN and local digest-pinned
Valhalla 3.9.1 on the same archived Manchester bytes. It publishes per-case JSON;
original frozen map downloads/build inputs may be reused, original verdicts may
not stand in for new execution. Fresh GitHub outcome and candidate counts must
be verified before reporting them. Full-category rank remains unavailable.

Next recommended improvement is owner approval for a runtime directional-access
fix with its own frozen expected semantics and fresh affected-cohort tests.
Approval has NOT been inferred or requested before this evidence stage finishes.
Category 2 remains unstarted. General existing repository CI can run its standing
regressions on PR updates; that is not authorization or evidence of a new Category
2 real-road trial.
