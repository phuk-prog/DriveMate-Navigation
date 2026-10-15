# DMN — owner decisions recorded on 15 October 2026

**22 of 22 conversational questions answered.** This is the decision record of questions actually spoken; after question 5 their wording diverged from the earlier unconfirmed draft questions. Old suggestions are visible in Git history, but must not be mistaken for owner approvals.

**Purpose:** DriveMate Navigation (DMN) is an engine-first research programme to make the existing DriveMate Android app the strongest possible navigation app. Do not build a second standalone app. Work independently on navigation, and when credible evidence requires better road data, routing graph, matcher, GPS, offline map, renderer or another supporting system, improve/rebuild the dependency and its downstream consequences. Do not force the engine to fit today's app. Use an isolated integration branch later, not production.

## Recorded answers

| # | Decision topic | Owner decision or accepted recommendation |
|---|---|---|
| 1 | Minimum comparator families | Ten minimum, more permitted; twelve references currently proposed, not yet all tested. |
| 2 | Commercial access | Use only free, legally permitted access first; ask before any paid test. |
| 3 | Inaccessible or different-condition comparators | A plus C: retain as Not Tested, and permit separate lawful observational findings without comparable scores. |
| 4 | Test geography | Select complex real UK junctions wherever located, not Manchester-first; keep ordinary controls. |
| 5 | First vehicle | A: ordinary passenger cars first. |
| 6 | Meaning of best routing | Accept priority of legal and safe directions, reliability, then ETA; individual route preference ordering was not specified. |
| 7 | Scores and ranks | Each category out of ten, sorted highest to lowest among comparable systems only. |
| 8 | Execution environment | Use reproducible GPS replays and emulator/GitHub runs now; physical device later. |
| 9 | Rendering | A: freeze renderer as initial control; if navigation evidence requires better map/rendering software, revisit as a dependency. |
| 10 | Offline | Full offline navigation required; existing offline data in another repository is user-reported, not independently validated here. |
| 11 | GPS | Test everything relevant, including multi-source fusion. |
| 12 | Guidance | Lane and roundabout guidance must pass when objectively verifiable; missing reliable lane data is UNKNOWN, not FAIL or PASS. |
| 13 | Arrival | Require correct approach side and usable vehicle entrance from beginning when verifiable. |
| 14 | Display | One concise summary scoreboard by default; retain full individual evidence records underneath. |
| 15 | Illegal/unsafe turn verdict | Investigate and verify legality before declaring a manoeuvre illegal and blocking it; do not assert uncertain manoeuvres are lawful. |
| 16 | U-turn | Allow necessary lawful U-turns including dead ends; lack of options does not legalise prohibited turns. |
| 17 | Source gaps | Investigate and fill missing map data using justified evidence; never fabricate or auto-publish unverified edits. |
| 18 | Unrunnable individual test | Leave test unranked/not tested, and continue the other tests without automatically dropping engine. |
| 19 | Required scenario count | No fixed numerical minimum: representative reasonable sample with difficult cases and controls. |
| 20 | Manual Google/Waze observations | Manual, lawful spot checks for context are acceptable, but are observational and not head-to-head ranks. |
| 21 | Emulator runs | Mix fast focused replays with smaller number of whole end-to-end journeys. |
| 22 | Replacing current app navigation | Aim for DMN to be BETTER than every fairly comparable competitor on each tested issue, not merely on par. No claim of beating unavailable competitors; promotion still requires regression, legality, offline, ownership and rollback evidence, with separate release approval. |

## Scoring, source and delivery rules

Only report numeric scores **out of ten** on independently judged, comparable cases. Show **highest-to-lowest category ranks** and DMN distinctly. Keep correct/judged/planned counts, failures, unknown, untestable, unsupported, not-run, case difficulty and provenance in the underlying records; the requested default presentation is **one concise summary scoreboard**, not deletion of audit details. Missing map or lane truth is UNKNOWN and does not create an automatic fail or pass. An individual case that cannot be run is unranked, not a reason to stop other cases. Do not award high confidence for a trivial, tiny or unrepresentative cohort merely because there is no numerical minimum.

Legality is established from independent reliable evidence where obtainable; provider consensus does not make a turn lawful. A **verified** prohibited turn must fail. Do not classify an unusual turn as illegal without checking. A lawful U-turn can be required at a dead end. Neither missing source material nor necessity overrides an actual legal prohibition.

**Full offline operation** is a target; verify that existing data in the other repository actually supports correct routing, updates, instructions and regional boundaries. Broad GPS-source and fusion tests, correct-side/entrance arrival and verifiable lane and roundabout accuracy are mandatory goals. Freeze the renderer initially as a controlled test condition, but an evidence-based navigation dependency may justify replacing it.

DMN's intended standard is **better than every legitimately comparable reference per issue**, not mere parity. When a reference cannot be tested comparably, label it Not Tested or Observation Only; never claim it was beaten. A release additionally needs independent safety checks, repeated/held-out regression, good resources, licence compliance and rollback, plus explicit production authorisation. Tests run through GitHub and emulators; physical phone testing is deferred.

## Still unspecified, not silently approved

Exact scoring formula and severity weights; precise repeat-counts; all traffic/school-street/conditional rule oracles; route-policy preference ordering; per-category national coverage quotas; concrete allowed licence implementations and paid providers; exact performance/battery thresholds. These are **open technical policy details**, not additional answered questions. Resolve them with evidence and request owner approval if they involve cost, distribution/licensing, safety or major irreversible architecture changes.

**State:** 12 proposed external reference families plus DMN; 14 planned test categories. No new 12-engine comparison or Android tests are claimed by this documentation change. Preserve all historical branches, results, tests and failures. Next engineering action: implement an evidence-backed scorecard, choose diverse complex real UK cases, check runnable engine interfaces, run and rerun fair comparisons, and improve navigation/dependencies without modifying production.
