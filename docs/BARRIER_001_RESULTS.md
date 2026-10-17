# BARRIER-001 results — bollards and gates on real Greater Manchester roads

17 October 2026. Research engine test only (no Android app).

**What is tested.** Real barriers (bollards, blocks, gates, lift gates…) that sit in
the middle of a car road. Each engine gets the same small map clip, a start just
before the barrier and a finish just after it, so the direct route would cross it.

- **closed** (bollard, block, cycle barrier, or any barrier marked "no" for cars):
  crossing it is a **fail**; a route round it is a **pass**.
- **open** (explicitly open to cars): crossing it is a **pass**; avoiding it is
  over-cautious ("avoided open").
- **unmarked gate** (no access tags) and **restricted** (private, destination…):
  reported only, never counted as pass or fail.
- Every route is also checked against all one-ways, turn bans and other barriers on
  the clip; no-route answers are re-asked on a map 3 times wider; driving up to a
  barrier and turning round there is allowed (it is not crossing it).

Frozen inputs: source map `2a8ef8e1…22acba` (branch `data/turn001-snapshot`), case list
`config/barrier001-cohort.json` (110 barriers, chosen by a fixed rule before any
engine ran), clips on branch `data/barrier001-snapshot`, hashes in
`config/barrier001-prepared.json`. 94 testable (16 skipped: another barrier on the
same stretch), of which 47 closed, 14 open, 25 unmarked gates, 8 restricted.
92 are discriminating (with the barrier removed, DMN's route crosses it).

## Result — BARRIER-001 v1.1

Run [39022934914](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39022934914),
commit `b85e4f2`, all jobs passed. Harness self-check: OSRM with the barrier removed
crosses it in 91 of 92 discriminating cases, so the test does see crossings.

**Judged cases (closed 47 + open 14 = 61), ranked by legal passes:**

| Engine | Pass | Fail (crossed closed barrier) | Avoided open barrier | No route | Off-target |
|---|---|---|---|---|---|
| DMN | **46** | **0** | 0 | 15 | 0 |
| OSRM 5.27.1 | **46** | **0** | 0 | 3 | 12 |
| Valhalla 3.9.1 | 42 | 0 | 0 | 1 | 18 |
| GraphHopper 11.1 | 9 | 0 | 0 | 12 | 40 |

DMN and OSRM tie. No engine crossed a closed barrier and no route broke another rule.

**Reported only (unmarked gates 25 + restricted 8 = 33):**

| Engine | Went through | Went round | No route | Off-target |
|---|---|---|---|---|
| DMN | 30 | 2 | 1 | 0 |
| OSRM | 30 | 1 | 0 | 2 |
| Valhalla | 33 | 0 | 0 | 0 |
| GraphHopper | 13 | 0 | 4 | 16 |

### Reasons, case by case

**DMN.**
- *15 no route at closed barriers:* no engine found a route that passes the full
  check without unmarked gates. At 13, no engine found a passing route at all. At 2 (2092919405 lift gate marked no, 416565753 block), OSRM and Valhalla
  turn round at the barrier and then go **through other gates with no access tags**.
  DMN refuses unmarked gates mid-journey, deliberately. The scoring counts those
  routes as legal because unmarked gates are not rule breaks, so the summary shows
  "no-route though legal route exists 2". That is a limit of the scoring, not a DMN
  fault.
- *Went through 30 unmarked or private gates:* 28 start on an unmarked service road.
  DMN lets a journey begin or end on uncertain roads ("already on it / going there"),
  and that includes a gate on that stretch. 2 finish on a private road beyond its gate.
  This is DMN's existing journey rule, shown here for the owner's decision.

**OSRM.** 12 off-target (start or finish placed on another segment), 3 no route.

**Valhalla.** 18 off-target, 1 no route.

**GraphHopper.** Off-target in 40 of 61 judged cases (as in TURN-001, it often attaches
the start or finish to a different segment), so most of its answers cannot be judged.

### Query times (milliseconds), not ranked (different scopes)

| Engine | What is timed | Median / p95 | Samples |
|---|---|---|---|
| DMN | Read clip, build graph, route (in-process Python, cold) | 106.2 / 618.1 | 94 |
| OSRM | One warm query to a local server | 1.3 / 1.7 | 94 |
| Valhalla | Same | 18.4 / 21.7 | 94 |
| GraphHopper | Same | 83.0 / 99.1 | 94 |

## Earlier run — kept separate

**v1, run [39022261422](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39022261422)
(test fault, not a result).** It counted driving up to a barrier and turning round as
crossing it, so OSRM showed 38 and Valhalla 33 "fails" at closed barriers. All 32
base-clip ones were such turn-rounds. Fixed in v1.1 and re-run once. DMN's v1 counts
were identical to v1.1.

## Proposed improvements (for owner review, not done)

1. Scoring v1.2: report routes that rely on unmarked gates as "legal only through
   unmarked gates", so "no route though a legal route exists" is not inflated.
2. DMN: decide whether a trip that starts on an unmarked service road may pass an
   unmarked or private gate on it (30 cases).
3. DMN blocks the whole road segment next to a closed barrier, so it cannot drive up
   to the barrier and turn round. That costs nothing in this cohort, but it could hide
   a legal turn-round where no other route exists.
