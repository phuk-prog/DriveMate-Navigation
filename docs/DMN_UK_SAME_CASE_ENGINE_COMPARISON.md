# DMN pinned UK route-case comparison, 15 October 2026

The [25 audited map-only route-choice records](../references/uk-route-preference-map-cases-20261015.json) represent 25 distinct fastest/shortest paths from 144 sampled journey pairs in three supported real Greater Manchester OSM-neighborhood road graphs, not independently verified UK lawful journeys.

A new opt-in `[uk-case-osrm-smoke]` Actions step loads the **same pinned Geofabrik 2026-09-01 Greater Manchester OSM PBF** into local OSRM MLD 5.27.1 (pinned car.lua) and into DMN's strict bounded importer. It then deterministically regenerates all 25 cases and queries OSRM once per pair at exactly the DMN map vertices. A 15-metre endpoint snap threshold tracks gross map-match differences. The exact archived 25 DMN paths, costs, IDs, and study denominators must still match the previously audited record, and the external results must contain exactly 25 corresponding case IDs.

**All comparator outcomes are provisional.** Matching endpoint snaps do not establish identical first/last vehicle edges, equal access/turn rules, equivalent routing cost models, independent UK road law, correct arrival side, real traffic or driver-visible superiority. The recorded rows contain only hashed case IDs and aggregate distances/times/snap distances; no coordinates, source OSM object IDs, personal journeys or GPS traces. Missing/unroutable, endpoint-mismatched and noncomparable cases must be counted, never turned into wins. Only the opt-in smoke uses the external container; research/production branches remain independent.

Following a successful full-job run, remove the PR-title opt-in marker and retain the Actions report as evidence. Next external engines should use the exact same pinned map-era cases with explicit `NOT_COMPARABLE` when data/profile/access differ; do not award /10 scores before independent legality and maneuver truth.

## GitHub Actions opt-in trigger

On the `pull_request` synchronization event, `github.event.head_commit.message` is not populated. Enable the one-time OSRM study by adding `[uk-case-osrm-smoke]` to **draft PR #1's title** before the next research-branch push; GitHub must then execute the paired engine step rather than merely passing unit CI. Verify from the step conclusion and artifact contents, not green workflow status alone. Remove the marker immediately after capturing the result. Maintain the 25-case checksum and use `NOT_COMPARABLE` when any route or snap is not a fair match.

## First execution, source-backed measurements

[Actions run 38798997437](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38798997437) passed **306 Python unit tests** and completed a real local OSRM MLD run on all **25/25 pinned DMN map-only cases**, with **25/25** endpoints snapped within 15 metres, no OSRM NoRoute or NoSegment outcomes, and all archive fingerprints reproduced. Aggregate comparison evidence artifact: `dmn-uk-25-mapcase-osrm-paired-evidence`, ID **12003008396**. The opt-in draft PR title marker was removed.

The actual source-matched cases show five sizable DMN-fastest-map-distance vs OSRM car.lua-distance gaps worth investigating: four around **253 m** and one around **85 m**, with both endpoints matching. Their anonymized case IDs and rounded gap magnitudes are:

- `dmn-mapcase-20142904c879eddde89ba850`: OSRM approximately 253.183 m shorter.
- `dmn-mapcase-9837949746c78e783e307c35`: OSRM approximately 253.170 m shorter.
- `dmn-mapcase-ded34a7dbf3aa4711ea909d0`: OSRM approximately 253.091 m shorter.
- `dmn-mapcase-ed2d1bc1ff679e28e5c80c53`: OSRM approximately 253.079 m shorter.
- `dmn-mapcase-295d57396b784f578e59e668`: OSRM approximately 85.226 m shorter.

These gaps **do not identify a winner or a DMN failure**: DMN's prototype model may forbid/avoid a movement that OSRM's broader/different car profile permits, and the bounded buffer or geometry cost may account for another difference. Reconstruct their exact directed approaches privately from the pinned public data; independently check signed restrictions/official TROs, road geometry, sources and arrival movement. Do not widen access or remove turn restrictions simply to shrink the gap. The comparator now triages materially divergent routes in priority order, without asserting legal superiority.

## Exact directed interior path investigation

A follow-up local OSRM option requests `annotations=nodes` for the same 25 UK cases, keeping original OSM node IDs ephemeral inside the research process. These OSRM node sequences are compared to the *same exact directed node pairs* in DMN's conservatively imported graph. The diagnostic separates: interior fully mapped and turn-compatible; mapped prohibited turn conflict; incomplete/non-drivable graph segments; or unsupported annotations. Parallel directed ways are handled as alternatives, not silently merged.

The persisted JSON contains only sanitized counters and case hashes, never original OSM IDs or route geometry. Even if an interior node chain matches, it does **not** certify the entrance/exit approach, roundabout lanes, current UK signage/TROs, vehicle arrival-side, live traffic, or general engine superiority. The priority remains investigating the five observed large distance gaps before any routing modifications.
