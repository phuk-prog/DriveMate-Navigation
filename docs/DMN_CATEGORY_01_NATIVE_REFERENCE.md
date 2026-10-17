# Category 1: native reference graph inspection

Owner continuation authorizes proper reference installation and evidence-backed
DMN improvements within Category 1. This stage implements read-only measurement
only, based on `3c8e8d2`. No engine source or routing settings are patched.

## Fair setup and bounded execution

Use the existing digest-pinned Valhalla 3.9.1 image and archived Manchester OSM
bytes SHA-256 `34438baa7a28c55958cd5ba7ac3909a551c51197911963364d27a26eefe8973a`.
The original 20 ways remain frozen. DMN and Valhalla execute freshly on those
bytes. The existing locate and applicability probes remain, with native evidence
added in the same workflow, not another reference build.

The official image copies its installed library and headers into the runner.
Install compiler/development dependencies in that reference container and compile
`tools/reference/valhalla_graph_probe.cc` against the installed library. No
Valhalla rebuild or behavioural change. Enumerate all road hierarchy levels, exclude shortcuts and require consistent
permissions across any duplicate source observations. The exporter bounds tiles, edges and shape
sizes, fails on incomplete reads, and exposes actual directed graph IDs,
start/end nodes, way identity, directed shapes, motorcar access bits, simple
restriction masks, local indexes and complex/access-restriction indicators.
Tile SHA-256 hashes must stay unchanged across inspection.

OSM remains attributed to OpenStreetMap contributors under ODbL; Valhalla is an
MIT-licensed reference. This independently authored API reader stays in research
tools, never DMN runtime. It does not change the competitor to make it pass.

## Frozen comparison contract

`benchmarks/map001_native_reference.py` expands native shapes only when every
point maps uniquely to a consecutive, monotonic source-way node sequence.
Ambiguous geometry, missing source-segment observations or conflicting duplicate
permissions are UNSUPPORTED, not competitor faults. Native directed edges can
span multiple source segments; raw native edge counts are not DMN quality scores.

For the unchanged binary source-access subset, compare all expected oriented
source segments and extra car-allowed directions. An observed car bit contradicting
explicit source permission is a discrepancy candidate. Contextual/private/
destination and unknown service access remain NOT_JUDGED for both engines.
A partial ranking, if supported by successful native execution, covers only this
identical directed-access cohort. It cannot establish a full Category 1 winner,
independent current UK road legality or a speed ranking.

The exporter also records connected native arrival/departure pairs for relations
7844440, 7844441, 7844443 and 7876327. A simple restriction bit is interpreted
using the departure's native local index only. A native mask is not a complete
AutoCost answer: generic U-turn pruning, destination permission, conditional,
complex, exclusion and dynamic policies can also affect legality. Those full
turn decisions stay UNSUPPORTED rather than being scored from a mask alone.

## Verification and known execution limits

Eight new synthetic test methods cover correct/incorrect directed access,
missing/incomplete enumeration, contextual exclusions, ambiguous/backtracking
geometry, duplicate conflicts and connected-pair mask indexing. Local results:
109/109 Category 1 tests and 603/603 full regression methods pass; compile,
privacy and whitespace checks pass. These fixtures are not UK-road proof.
Native C++ compilation and real reference enumeration are UNAVAILABLE locally
(no Docker runtime); GitHub execution is required. A green Python unit suite is
not evidence that native compilation succeeded. Preserve every CI setup failure
and retry only after its cause is investigated.

Pinned API evidence:
- https://github.com/valhalla/valhalla/blob/3.9.1/docker/Dockerfile
- https://github.com/valhalla/valhalla/blob/3.9.1/docker/Dockerfile-scripted
- https://github.com/valhalla/valhalla/blob/3.9.1/valhalla/baldr/graphreader.h
- https://github.com/valhalla/valhalla/blob/3.9.1/valhalla/baldr/directededge.h
- https://github.com/valhalla/valhalla/blob/3.9.1/src/sif/autocost.cc

No Android app/APK, Category 2, merge or production change. Results and any
remaining discrepancies must be reported for review before category advancement.

## Preserved setup failure and correction

Run https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38961774507
on 8f44f01 passed Python controls and fresh engine probes but failed native linking.
The installed library's pkg-config requirements lacked Spatialite, GEOS and
OpenSSL development metadata. A command substitution failure then left the
compiler without library flags. Add libspatialite-dev, libgeos-dev, libssl-dev;
resolve flags in a separate fail-fast shell assignment before compilation.
No engine failure or native comparison verdict is inferred from this setup error.
Original logs/artifacts and previous commit are preserved. Rerun the same frozen
cohort after this installation correction; do not change acceptance or input.

Second preserved setup run:
https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38961978148
on a670865 resolved missing metadata and confirmed installed version 3.9.1, then
failed because recursive static pkg-config flags referenced an absent
`libprotokit.a`. Use normal shared dependency linkage and explicitly request
Valhalla's private dependency packages instead of recursively requesting their
static archives. This only adjusts the standalone reader's linker flags; no
engine binary, source, profile or map is modified. Retain both failures as
installation/measurement-tool issues, not competitor navigation faults.

## Native execution and hierarchy coverage correction

Run https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38962312453
on 373a222 compiled and executed the reader successfully. Tile hashes stayed
unchanged. It enumerated 894 directed edges on local level 2; the common binary
subset was 7 ways / 60 segments, with both engines passing all 7. Five selected
ways had no local-level native observations: 115559329, 154986397, 155729945,
548694371, 550963219. These were correctly reported UNSUPPORTED, not engine FAIL.
Valhalla hierarchy construction promotes edges by road classification, so level
2 alone is not exhaustive for this cohort. Expand enumeration to all road levels
0/1/2; still reject shortcuts, ambiguous alignment and conflicting observations.
Preserve that first successful partial result rather than overwriting it.

The native local-level output already exposes the connected pair for Cross Street
relation 7844440: arrival graph 8495877946, departure graph 8697204538, via graph
node 3194277690; arrival mask 6, departure local index 1, explicit prohibition
bit set. Both edges expose car access. This is structural mask evidence, not a
claim that all AutoCost turn semantics are evaluated. Other target relation
pairs require the expanded hierarchy inspection. Frozen expectations and source
bytes stay unchanged.
