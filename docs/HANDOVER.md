# Handover (keep short; newest first)

## 2026-10-17 — TURN-001 focused four-engine diagnosis
- Branch `codex/turn001-live-dmn-20261017`; committed harness SHA `3dd8d25`.
- Seven DMN problem cases freshly rerun: exact legal passes OSRM 2, Valhalla 2, GraphHopper 1, DMN 0; prohibited failures DMN/GH 0, OSRM 1, Valhalla 2.
- Evidence-backed DMN gaps: `14285234` reachability/endpoint and `16686773` no-motorcar-edge import rejection. No behavior change.
- Stop for owner review before fixing; any approved fix needs the full frozen affected cohort and all applicable engines freshly rerun.

## 2026-10-17 — TURN-001 live-head DMN baseline
- Branch `codex/turn001-live-dmn-20261017`, based on PR #4 head `a7ab710`.
- DMN: 129 PASS / 0 prohibited / 6 safe no-route / 6 OSM-barred endpoints / 1 map rejection across 142 testable cases; 159.8 ms median, 628.5 ms p95 local import+route.
- No live-SHA competitor ranking: public run 39019749346 used `0668fce`; artifact/API access returned 403. No behavior change.
- Next owner-reviewed action: obtain a fresh same-SHA four-engine summary, then compare the seven DMN coverage cases before proposing a fix.

## 2026-10-17 — Category 1, TURN-001 turn-restriction comparison
- Branch `codex/dmn-gps001-ranked-trial-20261015` (PR #4). Harness contract
  TURN-001 v1.3: real-journey test (direction of travel given to every engine,
  partial first/last segments kept, whole-route audit of all one-ways and
  restrictions, no-route re-asked on a 3x wider clip, OSRM control run).
- DMN change: `shortest_route(..., endpoint_uncertain_access=True)` lets an
  uncertain road be the start/finish of a journey, never a through route.
- Frozen inputs: branch `data/turn001-snapshot` (OSM, ODbL; hashes checked).
- Get results: run workflow "TURN-001 four-engine turn-restriction comparison"
  (`.github/workflows/turn001.yml`, manual or PR). Read its job summary only.
- Early local DMN result (not final evidence): 130/142 legal routes, 6 endpoints
  OSM closes to cars (correctly refused), 6 no route even on the wider clip.
- Next: read the CI summary; check any DMN no-route where another engine has a
  legal route; write docs/TURN_001_RESULTS.md; then node-barrier route test.
