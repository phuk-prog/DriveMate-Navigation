# MAP-001 v3 — owner-approved test-system correction

**Scope:** Category 1 of 21, engine research only. No DMN runtime/importer, GPS,
Android, APK or production repository changes. Original v1 and v2 artifacts remain
unaltered.

**Historical v2:** 107 source-agreement cases, eight safely withheld, five
unjudged. Manchester 155729945 and 246124643 rejected relation context; Carlisle
23467606/1101726808 and Glasgow 4627827 had a missing referenced relation member.

**New v3 contract:** Freeze the same 120 selected *OSM way IDs* from the v2
manifest. Fetch bounded OSM source, then fetch missing relation-member ways and
their nodes with capped official OSM way/full requests. Archive the exact six
resulting OSM XML bytes together with their SHA-256 hashes. Score directed
geometry/access and restriction expectations, including **both missing and
unexpected prohibited turns**. The closure manifest records resolution failure
instead of silently dropping data.

**Important limitations:**
- v3 is a *new* OSM source snapshot, NOT byte-identical to v2. Missing/changed
  historical tags and any legal road changes are not DMN before/after gains.
- Bbox reads plus subsequent official way/full reads are NOT an atomic OSM
  timestamp. The checksums establish deterministic reuse of the combined v3
  inputs; they do not establish whole-area simultaneous-map consistency.
- Node-via simple restriction logic is still narrow; via-way, conditional
  time-aware or ambiguous vehicle-mode cases remain unknown/withheld.
- One MAP-001 v3 run is permitted following owner approval; no automatic retries.
  CI and its artifact are the actual execution evidence. Failed probes stay failed.
- Valhalla MIT /locate metadata is an experimental **graph-candidate OSM way-ID
  visibility probe**, not a full directed graph or movement-restriction adapter.
  Do NOT rank Valhalla against DMN on complete Category 1 graph fidelity just
  because the /locate probe works. It is an explicitly narrower, independently
  reported interface qualification.
- OpenStreetMap source licensed ODbL (© OpenStreetMap contributors).
  Do not republish OSM data without attribution and compliance.

**Required outcome:** report raw passes/fails/withheld/unjudged, exact cases,
which missing way members were recovered, unresolved import details, any additional
prohibited-turn errors, the Valhalla metadata probe's actual coverage and
remaining graph-comparison blockers. Never pretend source consensus is legal truth.
Stop for owner review before any DMN behaviour change or Category 2.
