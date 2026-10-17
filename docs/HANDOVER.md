# Handover (keep short; newest first)

## 2026-10-17 — approved Category 1 completion, green integrated retest
- Owner approved remaining Category 1 engine/map graph work together; no
  registration, no Android/app/APK and no Category 2 execution.
- Research branch `codex/dmn-category1-completion-20261017`, draft PR #10 (unmerged).
- [MAP-001 v3 six-region graph evidence](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39018620653)
  retained; native partial DMN=Valhalla 78/78 ways, 714 common segments.
- [GraphHopper heading trial](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39029550716)
  PASS: 0/9 wrong-endpoint cases corrected, 3/3 unchanged controls PASS;
  no arbitrary competitor changes.
- [Frozen overall Category 1 scorecard](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39029966922)
  PASS; source, turn, barrier separately ranked and signed-law gaps withheld.
- [Fresh combined-branch BARRIER v1.2 four-engine retest](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39029643326)
  six jobs PASS, exact same results as before (DMN=OSRM 46).
- [Full research safety regression](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39030191491)
  PASS after fixing public OSM coordinate-key false alarm **without**
  weakening privacy checks.
- Results and remaining unverified facts: [Category 1 final report](DMN_CATEGORY1_FINAL_REVIEW.md).
  Category 1 research finish is not independently verified UK-road law
  or a full cross-engine graph certificate.


## 2026-10-17 — no-registration policy and TURN-001 reference endpoint audit
- Owner: do not sign up for research sources; leave inaccessible legal
  evidence DIAGNOSED/UNVERIFIED and move to registration-free tasks. Shared
  [rule](DMN_NO_REGISTRATION_RULE.md) indexed in the REGISTER read-first map.
- TURN-001 five missing-route cases: completed map-based diagnosis, NOT
  independent legal proof; do not pursue D-TRO consumer registration.
- [Run 39028874337](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39028874337)
  successfully analysed existing 142-case v1.3 engine artifacts only.
  GraphHopper 67 raw base-clip off-target, 54 with DMN exact-anchored
  comparison: 41 start-only mismatch, 11 finish-only, 2 both; see
  [endpoint report](TURN_001_ENDPOINT_AUDIT.md). Original final total 68
  remains unchanged. No engine code changed or expensive competitor reruns.
- Next: determine cause of mismatch from small, already accessible
  GraphHopper geometry/adapters; no Category 2 or Android app changes.


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
