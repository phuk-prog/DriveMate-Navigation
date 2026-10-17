# BARRIER-001 frozen inputs

Map clips (OpenStreetMap, © OpenStreetMap contributors, ODbL) for the BARRIER-001
bollard and gate route test. Cut with `osmium extract --strategy complete_ways` from
`gm.osm.pbf` on branch `data/turn001-snapshot` (SHA-256 2a8ef8e1…22acba) around each
barrier in `config/barrier001-cohort.json`. Clip hashes are in
`config/barrier001-prepared.json`. Do not overwrite: a new snapshot needs a new name.
