# Category 1: owner-approved directional-access importer correction

Owner approval follows investigation commit
`940afab336cfea03d7c39cbc416f2fc2fc382146`. Scope is the directional-access
importer defect only, not new one-way exceptions, contextual permission policy,
turn semantics, Category 2, Android integration, merge or release.

## Frozen semantics and implementation

For each existing oriented edge, resolve `motorcar`, `motor_vehicle`, `vehicle`,
then `access`; within each mode use the directional value before its general
value. OSM way node order defines forward/backward. Keep existing allowed,
prohibited and unknown value policy. Keep geometry, one-way processing, barriers,
conditional rejection and turn-restriction processing. A directional permission
cannot override a physical barrier or create a wrong-way edge. Bus/taxi/bicycle
exceptions do not grant ordinary-car permission.

`map_data/osm_xml.py` now resolves access separately for forward and backward
edges. Importer callers and route consumers receive the corrected edge access.
No reference-engine or source-oracle semantic tuning is included. The source
oracle report now truthfully records the approved runtime change; this metadata
edit changes its file hash, not its expected access semantics.

## Tests and unchanged cohort

New synthetic regression methods first failed with 16 subcase failures against
the previous importer. After correction: 93/93 map-data unit tests and 587/587
repository regression methods pass locally. Compile, privacy scan and whitespace
checks pass. Full regression execution is safety verification, not a new category
trial. Existing bug reproductions now require correct access, with an additional
mutation control proving the harness still catches the original wrong-access bug.

Archived Manchester source SHA-256 remains
`34438baa7a28c55958cd5ba7ac3909a551c51197911963364d27a26eefe8973a`.
Exactly the same 20 ways and 108 directed-edge checks are used:

| DMN isolated-way source agreement | Before | After local fix |
|---|---:|---:|
| Passed | 9 | 12 |
| Failed | 3 | 0 |
| Safely withheld | 0 | 0 |
| Not judged | 8 | 8 |

All 15 previously wrong reverse segments now have prohibited access:
King Street `155729945`, Princess Street `115559329` and `548694371`,
segments 0 through 4 in each way. Unknown/contextual cases are not passes.
Original 109/120 v3 evidence and the 940afab failure evidence remain preserved;
neither uses a directly interchangeable overall scoring contract.

The facts workflow freshly rebuilds digest-pinned local Valhalla 3.9.1 from the
same archived Manchester bytes, reruns all 20 candidate inspections and publishes
per-case JSON plus Category 1 unit evidence. Its post-fix gate requires no DMN
FAIL, complete cohorts and identical source hashes; unjudged cases stay explicit.
Actual GitHub conclusions must be read for the uploaded SHA before claiming CI
success. This document records local evidence at upload time.

## Remaining limitations and review

This fixes source-tag agreement, not independently verified UK road legality.
No full engine ranking is justified: Valhalla's locate interface still cannot
prove exhaustive missing edges, connectivity or directed turn-pair equivalence.
Carrying corrected access into an edge does not prove complete end-to-end routing
on the UK extract. The new synthetic route regressions prove denied edges cannot
be traversed and opposite permitted directions remain routable in their fixture.

Relations `7844441` and `7844443` remain source-applicability issues;
`7876327` remains access-uncertain; `7844440` has a representable source movement.
No relation is removed or ignored. Native Valhalla pair inspection or the previously
identified BSD-licensed OSRM adapter, contextual access and independent road-law
verification remain separate proposed work. Stop after fresh results for owner
review. Category 2 is not started.
