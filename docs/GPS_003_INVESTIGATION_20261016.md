# GPS-003 and seven UK GPS-matching losses — retained-evidence investigation

**State: investigation completed from existing artifacts; findings await owner review.** No new matcher execution, external reference call, regression test, map download, route change, confidence-policy change, or production action was performed in this investigation. Treat old run verdicts as immutable; this is a read-only analysis and proposed next diagnostic plan. Compare with the permanent [six-rule testing policy](DMN_PERMANENT_TESTING_POLICY.md).

## What is actually tested and compared

**GPS-003** was a DMN-only real-map simulated GPS **stream lifecycle/first-fix availability** test. The pinned Geofabrik Greater Manchester historical OSM archive has SHA-256 `b7188b22501b878fddba6e06a90bb44ce6c2d721333e0ca57e10a1a82b568807`; its actual XML extract/map SHA-256 is `b3a883ae9b7c85072d24afeee7a1079aea00c22264516a0e1e71d49221ad27d5`; frozen oracle SHA-256 `612f2469facbc4e02fd8233a78d3cb2aa9f1bb40a892efb88e9bf91d116b80b0`. Source commit `c6202e406450d6f9fbb8e01c7679193d92522358`; [executed CI run 38869427281](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38869427281) **failed its required clear-match availability acceptance**, not setup. `24` independent stream **runs** contain `72` updates, but those streams reuse three mapped segments of **one** way and only **three distinct initial coordinates**.

**Only DMN executed the identical reception-clock/history/status contract**. Ranking against competitors is **UNAVAILABLE**; do not place OSRM, Valhalla, GraphHopper, openrouteservice or routing engines into a fictitious GPS-003 streaming table. Equivalent external stream-lifecycle harnesses are not established; batch map-matching or point-snapping is not the same task. The next competitive test, if approved, must use a separately frozen **shared real-map position/direction output contract** and label streaming-only checks unranked for engines whose APIs cannot express them.

| Actual test | DMN ★ | External comparable engines | Evidence |
|---|---:|---|---|
| GPS-003 per-stream complete acceptance | **8/24 passed; 16 failed** | **0 executed on this contract** | **PROVISIONAL map-derived edge labels + synthetic analytical fault rules**, not independent GNSS/survey truth |
| Initial mandatory clear road identification | **8/24 matched; 16/24 withheld as AMBIGUOUS** | Unavailable | Exactly two repeated failing initial coordinates, not 16 separate real-road locations |
| Final clear/recovery observation | **24/24 matched** | Unavailable | Source-map generating edge, not live-phone proof |
| Confident wrong-road assignments | **0/72 observed** | Unavailable | Small synthetic signals, cannot prove universal road accuracy |
| All events | **39 matched generating edge; 33 not matched including 12 explicitly rejected** | Unavailable | Safe withheld vs failed required availability are different measurements |

**The per-category provisional completeness outcomes** remain separate from speed/legality. No multi-category/combined overall score is claimed. Source-map identity equals the segment used to generate injected coordinates, not independently verified real-world vehicle location. Median per-update `0.0744115 ms`, nearest-rank p95 `0.153038 ms` over 72 samples; no cross-engine timing rank or Android/device prediction.

## Exact failed cases, expected vs actual

All 16 failures share the **very first 1,000 ms clear fix**: expected MATCH on the selected mapped forward directed edge, actual `AMBIGUOUS` / `nearby_parallel_or_overlapping_roads` / **two candidate edges**, no road claimed. They repeat the same first coordinate eight times on B1 and eight on B2.

| Fault scenario | B1 failed case | B2 failed case | B1 / B2 verdict | B3 verdict | Second-event actual status (B1, B2, B3) |
|---|---|---|---|---|---|
| clear | `GPS-003-B1-clear` | `GPS-003-B2-clear` | FAIL / FAIL | PASS | MATCHED, MATCHED, MATCHED |
| noisy_2m | `GPS-003-B1-noisy_2m` | `GPS-003-B2-noisy_2m` | FAIL / FAIL | PASS | AMBIGUOUS, AMBIGUOUS, MATCHED |
| weak_60m | `GPS-003-B1-weak_60m` | `GPS-003-B2-weak_60m` | FAIL / FAIL | PASS | UNKNOWN, UNKNOWN, UNKNOWN |
| stale | `GPS-003-B1-stale` | `GPS-003-B2-stale` | FAIL / FAIL | PASS | REJECTED, REJECTED, REJECTED |
| future | `GPS-003-B1-future` | `GPS-003-B2-future` | FAIL / FAIL | PASS | REJECTED, REJECTED, REJECTED |
| duplicate | `GPS-003-B1-duplicate` | `GPS-003-B2-duplicate` | FAIL / FAIL | PASS | REJECTED, REJECTED, REJECTED |
| speed_100mps | `GPS-003-B1-speed_100mps` | `GPS-003-B2-speed_100mps` | FAIL / FAIL | PASS | REJECTED, REJECTED, REJECTED |
| gap_31s | `GPS-003-B1-gap_31s` | `GPS-003-B2-gap_31s` | FAIL / FAIL | PASS | MATCHED, MATCHED, MATCHED |

B1, B2 and B3 are **Moss Lane**, OSM way `32113418`, segments 4, 6 and 9 respectively, lengths `24.297` m, `23.494` m and `34.127` m. The first reading is 30% along each mapped segment at 3 m declared accuracy, 10 m/s synthetic speed and directed segment bearing. B1 and B2 have **two plausible candidates**, B3 **one**. In the clear stream, B1 and B2's second (40%) and third (50%) observations match the intended segment. Every case's final clear observation matches.

**Every other expected fault/availability behavior in the saved evidence passed its own relevant event check:** three weak-accuracy events withheld, 12 stale/future/duplicate/implausible-speed packets rejected with unchanged accepted-fix history, noisy samples never claimed a wrong segment, gap reacquisitions matched, and all 24 final recovery observations matched. The 33 non-matches break down exactly as **16 first-fix ambiguity + 2 noisy ambiguity + 3 deliberately weak-fix abstentions + 12 input rejections**. This explains the 16/24 *stream* failures; it does **not** excuse the required initial-output failures.

## Supported algorithmic cause and what remains unknown

The first fix in each stream starts with `TemporalRoadMatcher` **without any trusted anchor**. Its update delegates to `DirectedRoadMatcher.match()`, which calls `_candidates()`. The current candidate policy, before considering continuity, filters by nearby road geometry and heading, scores lateral/heading errors, and withholds whenever another plausible nearby edge is within `max(12 m, 2 × reported accuracy)` or its score is insufficiently separated. At a 3 m reported accuracy the candidate search radius itself is 8 m. These are heuristic research thresholds, not measured GNSS calibration.

**Confirmed from logs and code:** on two Moss Lane initial fixes, *two* eligible edges survive and trigger the ambiguity guard; absence of an anchor means the temporal matcher cannot safely use history yet. The same fixed positions were repeated across eight fault streams. This is the proximate reason for the failing required-output contract, not bad GPS rejection, a failed rerouting algorithm or a matcher crash.

**Not confirmed:** the saved GPS-003 rows record **candidate count**, not both candidate **edge IDs, projection distances, headings, graph connectivity or permitted movements**. We therefore cannot conclude the runner-up is an adjacent bend on the same road rather than a genuinely competing side/parallel segment. `DirectedRoadMatcher._straight_same_way()` suppresses only *contiguous, exactly collinear same-way links*; the design deliberately retains uncertainty at bends/branches. It is a **plausible testable explanation**, not a verified bug and not approval to relax confidence or force a match. Also, because the frozen oracle requires the **exact generating directed fragment**, a proposed continuous-road vs fragment distinction must be evaluated on a new labelled test rather than retroactively changing old scores.

## Separate historical UK regression — seven lost matches

A **different** real-map analytical GPS replay retains **17/40 source-map-correct, 0 confidently wrong, 23 withheld**, versus **24/40 correct, 0 confidently wrong, 16 withheld** in the earlier baseline. The seven specifically lost matches are:
`TGP-006`, `TGP-008`, `TGP-013`, `TGP-015`, `TGP-016`, `TGP-019`, `TGP-039`.
These are not GPS-003 stream failures, cannot be added to 16, and were not freshly executed in this investigation.

Unlike GPS-003, the separate [retained UK topology diagnostic](../references/gps001-uk-topology-20261015.json) **does identify** the alternatives. In each of the seven cases, the expected direct candidate has zero generating-point projection residual and competes with a **backward-adjacent, same-OSM-way, same-direction** fragment. The competing fragment is only approximately **5.92–7.43 m** from the generated observation with a small angular disagreement. Although the bounded graph connector can reach it, that connection is **41.82–77.79 m**, and mere graph reachability does not establish a real car made that movement.

| Lost case | Generating-edge residual m | Backward alternative residual m | Heading difference ° | Bounded connector m |
|---|---:|---:|---:|---:|
| TGP-006 | 0.0 | 6.2627 | 0.0095 | 46.644 |
| TGP-008 | 0.0 | 6.2627 | 0.3294 | 42.398 |
| TGP-013 | 0.0 | 5.9229 | 5.6139 | 41.822 |
| TGP-015 | 0.0 | 5.9229 | 3.5995 | 53.270 |
| TGP-016 | 0.0 | 5.9307 | 0.2765 | 77.791 |
| TGP-019 | 0.0 | 5.9307 | 3.0012 | 45.974 |
| TGP-039 | 0.0 | 7.4274 | 7.5108 | 62.392 |

The temporal matcher intentionally does **not** select one reachable edge from two solely because the source-generated position is on it; doing so could invent an unsafe return manoeuvre. Old code in `_direct_fragment_before_bend` permits a carefully constrained *forward* continuation, but these alternatives are backward-adjacent. Both performance/availability and confident-wrong-road safety must be evaluated in a genuine new test before changing behavior. Source-map generating labels and topological connectors are **not** proof of independent surveyed legal truth.

## Separate issue register — verified observations vs uncertain root causes

| Priority | ID | Issue | Evidence category | Next proof needed |
|---|---|---|---|---|
| 1 | GPS003-FIRST-FIX-AVAILABILITY | **16/24 frozen streams fail** a required first clear match at B1/B2 | **Verified failure of frozen output contract**, but road-level truth provisional | Recover both candidate IDs and projections at the two retained exact positions, inspect map and lawful geometry without tuning |
| 1 | UK40-BACKWARD-ADJACENT | **Seven** older same-way backward-adjacent ambiguous matches | **Verified source-map coverage regression**, cause/intent remain provisional | Trace both candidate histories, feasible directed progress and separate legal evidence; retain anti-U-turn protections |
| 2 | GPS003-ORACLE-BREADTH | All three candidate segments are from **one Moss Lane OSM way** and repeatedly injected coordinates | **Test coverage limitation**, not 24 independent places | Choose more independent real UK roads after separately freezing next test; include bends/side-by-side roads and other hard locations |
| 2 | GPS003-CANDIDATE-EVIDENCE | Competing GPS-003 candidate IDs/geometry are missing from saved event output | **Observability gap** | Bounded diagnostic-only evidence collection under owner's authorization; retain originals |
| 3 | GPS003-COMPETITOR-CONTRACT | **0 external engines** ran the identical stream contract | **Comparison gap**, not poor external performance | Authorize separate shared real-map matching/direction cohort across available permitted engines; retain per-engine API exclusions |
| 3 | GPS003-ROAD-TRUTH | No independent GNSS surveyed position or official lane/turn/road-law confirmation | **UNVERIFIED truth**, no live-road accuracy claim | Source/date-aware third-party evidence, contradiction log and independent ground-truth coverage |

## Proposal for owner approval — investigate before any modification

**First, approve a bounded diagnostic-only stage**, which reads the **same pinned map** and the **same frozen observations** and records the actual candidate edge IDs, 0–8 m lateral distance, headings, scores, original way ID/segment/direction, overlap, connectivity and turn legality for just the B1/B2 initial positions and seven named historical UK cases. Use existing hashes/data and cache; no threshold changes, forced matching, altered score/oracle or production app updates. A diagnostic-only fresh execution is **not** itself a newly ranked competitor baseline; keep its scope explicit. Confirm competing roadway facts with independent evidence if available.

**Only after examining that report** should the owner separately decide whether to (a) improve safe fragment-equivalence handling, (b) improve temporal confirmation without wrong-way assignments, (c) retain abstentions when ambiguity is legitimate, or (d) revise future independently verified acceptance labels. Any authorized behavior change must keep existing 24 GPS-003 streams and 40 UK cases unchanged, include safety counterexamples, and **freshly rerun DMN and all applicable external references on any shared comparable frozen cohort** under the permanent policy. No historical external result may substitute for this fresh post-fix retest.

**STOP here for owner review.** No matcher fixes, tests, CI workflow runs or independent-road verification have been performed as part of this documentation investigation.

## Source pointers

- [GPS-003 original failed execution and artifacts](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38869427281)
- [GPS-003 frozen per-event record](../references/gps003-real-map-20261016.json), [GPS-003 original contract](GPS_003_RESULTS.md)
- [UK topology report, seven links](../references/gps001-uk-topology-20261015.json), [UK historical case changes](GPS_001_RESULTS.md)
- Source logic: [candidate policy](../gps/matcher.py), [anchor and topology policy](../gps/temporal_matcher.py), [frozen manifest/execution](../benchmarks/real_map_gps_recovery.py)
