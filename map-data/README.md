# Road-data ingestion

`map_data/osm_xml.py` now implements a **prototype importer** for small local OSM XML extracts. It is deliberately limited to **6 MB** and 30,000 objects; no national map or PBF support exists yet. The tests use a **hand-authored synthetic XML example** which is not a real junction.

~~~sh
python -m map_data --input benchmarks/fixtures/synthetic-osm-junction.xml --region synthetic --snapshot fabricated-v1
~~~

The CLI prints a SHA-256 of the input and attribution; it does not download, publish or copy the original file.

## Local, public-data-only PBF preparation (optional)

For repeatable tests, the publicly documented [Geofabrik Greater Manchester road-data extract](https://download.geofabrik.de/europe/united-kingdom/england/greater-manchester.html) is one possible source. Its standard public extracts omit contributor usernames, user IDs and changeset IDs. Download the **public current .osm.pbf** manually onto your own development machine, never the internal/history extract. Do not add the downloaded file to Git.

Install [Osmium Tool](https://osmcode.org/osmium-tool/). Then run the commands below using **only a public test-area bounding box selected independently of any real journey or person**:

~~~sh
python -m tools.public_osm_extract --input /path/to/public-region.osm.pbf --bbox "MIN_LONGITUDE,MIN_LATITUDE,MAX_LONGITUDE,MAX_LATITUDE" --snapshot public-snapshot-date
# The first command validates the argument structure only.
# Add --execute to process a small subset locally after verifying the source.
~~~

The tool asks Osmium to use `complete_ways` and strip OSM contributor metadata; checks the output again and processes no more than 6 MB of XML. It records aggregate node, edge and turn statistics without saving journeys. Generated files stay in the git-ignored `results/` directory. A small bound is necessary because the importer rejects large files. Because `complete_ways` does not ensure relations are complete, a complex road subset may be **rejected**, not treated as valid navigation data.

**This step has not yet been executed on real UK road data in CI.** Real OSM input may contain road rules the current importer cannot handle. A failed import does not prove roads are inaccessible.

 Do not commit real map extracts, private GPS traces or the imported graph.

## What this initial importer handles

- Directed roads, one-way tags including reverse and roundabouts
- Common vehicle access labels with conservative treatment of ambiguous service roads
- Selected physical barriers and explicit motorcar permissions
- Node-via `restriction=no_*` and `restriction=only_*` turn relations
- Source geometry with haversine lengths, approximate speed estimates (not legal limits)
- Required source/snapshot/region attribution and cryptographic checksum

## What it explicitly refuses or does not yet support

- Conditional vehicle/turn restrictions (clock dependent) and via-way restrictions
- Production road legality, route quality, lanes, surface, vehicle dimensions, height/weight and temporal closures
- Direct PBF ingestion without local Osmium conversion, streaming, complex relation shapes, intricate physical barriers and area routing
- Realistic junction exit enumeration, scalable map tiles, graph overlays and crash-safe regional updates

If a known conditional rule or unhandled turn relation is found, import raises an error rather than silently allowing a questionable manoeuvre. **Other OSM complexities are not fully recognised, so this is not road-ready.** The project requires a separate independent legality oracle and full vehicle-rule importer before live navigation.

This code does **not** assume an `highway=service` exit is legally open for through traffic merely because a routing provider includes it. OSM data remains subject to attribution and applicable ODbL share-alike requirements.
