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

## Evidence-tier interpretation

This next run is intentionally **one bounded public map study** with at most four eligible restrictions. It must report the number of cases considered, which cases were unsupported, the number of forbidden turns checked, how many alternative paths actually exist *inside* each extracted graph, and how many route-not-found outcomes remain unknown due to clipped boundaries. Even if all checks execute, do not award a safety score or claim an independently legal detour without primary turn-law confirmation. Keep the 12-case two-way-only smoke unchanged as a separate baseline.\n
## Executed initial buffered test (GitHub Actions)

[Verified run 38736859050](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38736859050) used pinned Geofabrik Greater Manchester 2026-09-01, produced **142/142 passing Python checks**, selected four public restriction neighborhoods and **checked two mapped prohibited-turn pairs in two importable neighborhoods**. DMN found a graph-permitted alternative in **2/2 tested**. **2/4 neighborhoods were unsupported** with reason `incomplete_neighbor_restriction`; **0** checked neighborhoods returned no route. These results do NOT independently establish real UK traffic legality or a winner over external systems.

**Follow-up repair:** A bounded, at-most-once retry now expands each affected public road clip (up to a 0.014-degree half-width) only when its target road or neighboring restriction data is incomplete. It never ignores unsupported restrictions, promotes missing data to PASS, assumes full-network completeness, or uses personal routes. A later GitHub Actions run must report whether extra cases actually became testable; until then any improvement is **unverified**.

## Measured bounded-expansion rerun (GitHub Actions)

[Run 38737339329](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38737339329) passed **144 Python tests** and retried two incomplete neighborhoods with larger geographical buffers. **Zero additional neighborhoods were recovered**: both became too large for the prototype **6 MB all-objects OSM importer**. The original two cases still exercised **two mapped restricted turns with two graph-permitted detours**, and two remained unsupported, not navigation failures. This is a **map-import capacity** gap.

**Next candidate improvement:** Filter out independently non-drivable OSM objects and unused nodes *before* running the existing strict importer. Retain all motorcar-class roads, access tags, barriers, and all applicable turn restrictions; any missing way, conditional legal rule or remaining resource overrun must still fail closed. The external temporarily extracted XML has a separate bound. Rerun real UK tests to measure whether this actually recovers the two cases.
