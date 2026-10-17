# TURN-001 frozen input (data only)

Pinned inputs for the TURN-001 turn-restriction comparison so CI repeats the
exact frozen test. Not code; never merged into a code branch.

- `gm.osm.pbf`: Greater Manchester cut of openstreetmap.fr `north_west.osm.pbf`,
  replication sequence 7332146 (2026-10-17T02:11:56Z); sha256 must equal
  `source_sha256` in `config/turn001-cohort.json`.
- `turn001-cases.tar.xz`: `prepared.json` plus each case clip (`cases/<id>/clip.osm`, `.pbf`).

Map data © OpenStreetMap contributors, available under the Open Database
License (ODbL) 1.0: https://www.openstreetmap.org/copyright
