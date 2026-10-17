# Handover (keep short; newest first)

## 2026-10-17 — TURN-001 five no-route junctions: focused diagnostic
- Own branch: `codex/chatgpt-turn001-no-route5-20261017`; read-only diagnostic in
  `tools/turn001_no_route5_diagnostic.py`.
- [Run 39027815145](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39027815145):
  one focused job PASS, pinned clips/hashes verified. All 5 have a direct
  route if turn rules are ignored, none has a via-node-rule-compliant route
  within the base clip. Four recover when the tested relation is removed;
  7615778 has a private-access destination.
- [Five-case report](TURN_001_NO_ROUTE5_RESULTS.md); no engine modifications or
  fresh competitive claim. Work item held pending independent dated
  signage/TRO/access evidence; no inferred real-world legal conclusions.


## 2026-10-17 (later still) — work register + BARRIER-001 baseline
- Shared register for all AIs: `python3 -m tools.work_status --fetch` (done / in progress /
  next, read-first list, `where <topic>`); rule at top of AGENTS.md.
- BARRIER-001 v1.1 baseline: [docs/BARRIER_001_RESULTS.md](BARRIER_001_RESULTS.md), run
  39022934914. Closed barriers: DMN 46 pass (ties OSRM), 0 crossed by any engine.
- Stopped for owner review; proposed improvements listed in the results file.
- REGISTER.md (one page every AI reads first) + pointer files for Codex, Claude, Gemini,
  Copilot, Cursor; PR #5 puts it on main (tests green, waiting for the owner to merge).

## 2026-10-17 (later) — TURN-001 results written
- Branch `claude/dmn-turn-restriction-debug-mhw7cw` (from the codex branch; not pushed there).
- Results: [docs/TURN_001_RESULTS.md](TURN_001_RESULTS.md). Fresh run 39019749346:
  DMN 131 pass / 0 fail / 5 no route / 0 off-target / 6 closed start-finish.
- DMN fix `0668fce`: an untagged service road that an only_* ban sends cars onto is open
  to cars (case 14285234); start allowance for uncertain roads ends on a normal road.
- None of DMN's 5 remaining no-routes has a full-rule-check route from another engine.
- Next: route-level bollard and gate test (not started).

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
