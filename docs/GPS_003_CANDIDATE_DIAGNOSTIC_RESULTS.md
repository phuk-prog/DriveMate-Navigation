# GPS-003 / UK40 — bounded candidate-geometry diagnostic result

**Status: completed and awaiting owner review.** Diagnostic-only GitHub execution: [run 38880782913](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38880782913) at commit `5086fc32e95060f3b19fc965cc88a58da0396020`; [original diagnostic artifact](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38880782913/artifacts/12037441640), [compact log-derived evidence](../references/gps003-candidate-geometry-20261016.json). CI outcome **SUCCESS**, and the standard research checks also succeeded. The ROUTE-004 five-engine baseline was **SKIPPED**, not rerun.

## Scope, truth classification, original results preserved

This was **not** a new navigation acceptance test, not a road-accuracy ranking, and not a live-device test. It inspected only the **two frozen first-fix GPS-003 coordinates** responsible for sixteen repeated failures and the **seven named UK40 historical regression positions**, against the identical pinned Geofabrik public Greater Manchester 2026-09-01 OSM extract. Map archive SHA-256 `b7188b22501b878fddba6e06a90bb44ce6c2d721333e0ca57e10a1a82b568807`; XML SHA-256 `b3a883ae9b7c85072d24afeee7a1079aea00c22264516a0e1e71d49221ad27d5`; original GPS-003 oracle SHA-256 `612f2469facbc4e02fd8233a78d3cb2aa9f1bb40a892efb88e9bf91d116b80b0`. The workflow verified both archive and map hashes before diagnostic execution and independently checked original recorded status/metrics for all nine investigations. It used the same existing matcher code and did **not** change thresholds, safety behavior, oracle, source map, test verdicts or production app.

The earlier frozen GPS-003 baseline stays **8/24 streams passed, 16/24 failed required first-fix availability**, 39 generating-edge matches, 0 confident wrong-road claims, 33 withheld including 12 rejected; all 24 final clear matches were recovered. Historical UK40 stays **17/40 source-map matches, 0 confidently wrong, 23 withheld** versus 24/40 before the regression. Do not count the nine successful diagnostic reproductions as nine corrected navigation cases. Both road truth and GNSS positioning truth remain **PROVISIONAL**; these are map-generated simulated locations. No other engine ran this identical streaming contract and no comparative rank can be assigned.

## A. Exact two GPS-003 first-fix candidate pairs — actual diagnostic output

Each first-fix position was repeated eight times in the original GPS-003 streams. Both require a clear source-matched output but still return `AMBIGUOUS` with reason `nearby_parallel_or_overlapping_roads`.

| Initial position | Intended directed fragment | Competing directed fragment | Intended residual | Competing residual | Competing heading error | Score gap |
|---|---|---|---:|---:|---:|---:|
| GPS-003-B1 | `w:32113418:4:f` | `w:32113418:3:f` | 0.000 m | 7.289 m | 3.069° | 2.128 |
| GPS-003-B2 | `w:32113418:6:f` | `w:32113418:5:f` | 0.000 m | 7.048 m | 6.555° | 2.002 |

**Verified geometric relationship:** in both cases the competitor is the **immediately backward-adjacent segment of the same OSM way 32113418 (Moss Lane)** and has the same travel-direction flag. The intended fragment has **0 m** simulated lateral residual and exact generating heading. Both alternatives are about 7 m away, within the matcher's conservative 12 m competing-segment ambiguity band for the reported 3 m accuracy (despite their scores being worse). The two alternatives are not independent, same-direction parallel roads. Current matcher geometry accepts the alternative as a nearby candidate and **correctly follows its existing rule to abstain**. 

This identifies the **precise ambiguity mechanism**, not an already-safe solution. A 3 m self-reported GPS accuracy and synthetic generator label do not independently guarantee 3 m real GNSS error or validate exact road-segment identity. More observation/physical corroboration is needed before weakening the ambiguity guard, even for same-way adjacent fragments. The direct-to-backward alternative is **not** an immediately permitted forward movement in the imported directed graph; that does not itself prove an illegal real-world manoeuvre or rule out a longer allowed graph connector.

## B. Seven older UK40 backward-adjacent candidates — exact actual diagnostic output

| Case | Intended directed fragment | Backward competing fragment | Competing residual | Competing heading error | Bounded graph connector |
|---|---|---|---:|---:|---:|
| TGP-006 | `w:32113418:18:r` | `w:32113418:19:r` | 6.263 m | 0.009° | 46.644 m |
| TGP-008 | `w:32113418:18:f` | `w:32113418:17:f` | 6.263 m | 0.329° | 42.398 m |
| TGP-013 | `w:32113418:21:r` | `w:32113418:22:r` | 5.923 m | 5.614° | 41.822 m |
| TGP-015 | `w:32113418:21:f` | `w:32113418:20:f` | 5.923 m | 3.600° | 53.270 m |
| TGP-016 | `w:32113418:26:r` | `w:32113418:27:r` | 5.931 m | 0.276° | 77.791 m |
| TGP-019 | `w:32113418:26:f` | `w:32113418:25:f` | 5.931 m | 3.001° | 45.974 m |
| TGP-039 | `w:32113418:40:r` | `w:32113418:41:r` | 7.427 m | 7.511° | 62.392 m |

All seven reproduced the historical `AMBIGUOUS` result and previously captured distances, headings and connectivity. All are **same-way, same-direction, backward-adjacent** fragments. Their alternatives are **5.923–7.427 m** from the synthetic target, with small heading differences. Reachability via a **41.822–77.791 m** mapped connector is not proof a vehicle physically or lawfully travelled backward. Neither an edge label nor a short position residual is enough to relax anti-wrong-road/anti-U-turn protections.

**Coverage limitation:** the two GPS-003 first fixes and these seven UK40 cases all involve fragments of the **same OSM way**, not nine independent roads. They cannot establish general accuracy across complex city junctions, tunnels, roundabouts, dual carriageways or other Manchester streets.

## C. Independent issue register — do not mix with passing diagnostics

| Priority | Issue | Observed / unverified | Recommended decision |
|---|---|---|---|
| 1 | GPS003-FIRST-ANCHOR | **Verified**: initial fix at B1 and B2 has two mapped candidates and yields an unavailable required match, repeated 16 stream executions | Consider evidence-backed continuous-road/fragment handling; **no automatic matcher change** |
| 1 | UK40-BACKWARD-FRAGMENT | **Verified**: all seven older coverage losses arise from backward-adjacent same-way alternatives, despite a zero-error generating fragment | Maintain progress/turn legality guards; separately justify any topology/history rule |
| 1 | ROAD-TRUTH | **Unverified**: actual surveyed positions, road signage/traffic orders, permitted movements and realistic GNSS noise | Obtain independent, dated evidence; retain uncertain truth as unknown |
| 2 | TEST-DIVERSITY | **Verified**: all nine examined points lie on a single mapped OSM way; source-map labels are correlated | Freeze independent UK road cases and adversarial backward-progress counterexamples before accepting improvement |
| 2 | MATCHER-POLICY-RISK | **Unverified safety**: removing all nearby backward fragments might produce confident wrong-road positions at junctions and closely overlapping roads | Compare safe competing hypotheses/trajectory evidence before proposing a narrow, reversible behavioral fix |
| 3 | COMPARABLE-ENGINES | **0** external engines implement this executed temporal receipt-clock contract in retained evidence | If approved later, design a **separate** shared static position/direction baseline; do not fabricate a score for unsupported engines |

## D. Recommendation and STOP gate

**No fix is yet authorized.** The next justified step is to design a candidate solution and additional adversarial/independently corroborated tests **for owner approval**, not simply loosen distance or confidence thresholds. Any later approved behavior change must then run the unchanged frozen GPS-003 and UK40 regressions plus safety controls, and freshly rerun **all applicable competitor engines** on separately frozen comparable category tests under [the permanent policy](DMN_PERMANENT_TESTING_POLICY.md). Never promote the result as independently verified live navigation safety.

**STOP for owner review before any navigation fix, extra experimental cohort, or new workflow run.** No production DriveMate changes, merge or release.
