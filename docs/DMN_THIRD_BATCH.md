# Third DMN batch — buffered real UK OSM turn-detour testing

The previous restriction structural test found 12 mapped prohibited incoming/outgoing movements, but used only the two subject OSM ways. The resulting 11 no-route decisions were **UNKNOWN**, because an alternative could exist just outside that tiny graph.

This batch introduces a **separate, more realistic, bounded road-neighborhood experiment**:

1. Download the pinned, publicly licensed Greater Manchester OSM snapshot in an opt-in GitHub Actions job, strip attribution metadata without committing map files or user coordinates.
2. Select up to four deterministic real OSM **node-via restriction cases**, centered on public source nodes; then extract a bounded network of complete public-road ways near each junction using Osmium.
3. Preserve all applicable node-via restrictions known to the source. If the source lacks a way, has unsupported via-way, conditional tags, or the importer is over its safe size bound, report that neighborhood **UNSUPPORTED/UNKNOWN** rather than erase the restriction or pretend a successful detour.
4. Route from a restricted incoming road to the target of the prohibited outgoing road, starting with the incoming-edge context. Record **detours found on the bounded network**, absent paths separately, and compilation/unsupported reasons. A no-route within a clipped area is **not** proof that no legal UK detour exists. No synthetic road results count as real-world truth.
5. Preserve totals and source hash in a short GitHub artifact, with neither personal location data nor raw route geometry. Do not compute numerical DMN versus external scores without independent turn-law verification and fair cross-engine evidence.

The separate `gps/fix_quality.py` input-quality checks continue as unit/contract tests. **GPS map matching, true device speed, variable speed limits, lane arrows, and arrival remain NOT TESTED** in this run. This experiment focuses on one verifiable missing layer: wider public road alternatives around real mapped restrictions.

Main command: `python -m benchmarks.uk_neighborhood_detours --pbf results/public.osm.pbf --restriction-source results/public-restrictions.osm --snapshot geofabrik-260901 --limit 4`. It requires the Osmium CLI and the source restricted to explicitly public, nonpersonal OSM. The GitHub workflow runs it only using the special `[neighborhood-detour-smoke]` opt-in marker. Neither production DriveMate nor APK generation is modified.
