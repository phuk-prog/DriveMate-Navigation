# DMN phone component decision report

GitHub CI now runs `python -m benchmarks.dmn_phone_decision` to produce
`results/real-england/dmn-phone-decision.json`.

This report is **not an APK certification**. It only summarises measured evidence for considering which components might eventually suit the **existing DriveMate Android app**.

- Native routing: genuinely passed route checks vs cases attempted, not a GPS/legal-lane score.
- GPS, rerouting, junctions, roundabouts, instruction events and arrival: separate outcomes for pass, fail, unresolved, not-exercised and exercised-but-unverified, with the precise attempted denominator.
- Reference routing speed: only complete valid same-run HTTP results, separate from phone performance and verified UK legal-road quality.
- Phone implementation decision: **pending evidence and user approval** until legal turns, GPS truth, rerouting, complex junctions, real roundabouts, lanes, voice/Bluetooth, Android device speed/memory/battery, offline maps, licences and integration are verified.

If the original workflow failed before creating input evidence, the report says **not tested** and cannot manufacture a green result.

Current follow-up focus: investigate GPS junction ambiguity and short destination links, keeping the last eight real-road cases as regression cases and adding independent holdouts.


## 15 October 2026 — GPS junction confidence correction

DMN's existing GPS matcher deliberately retains its last **observed directed
road** while another candidate is within the positional uncertainty at a
shared junction. The new `Match.junction_held` flag makes that bounded
hysteresis **explicit**. Both the basic GPS adapter and the recovery controller
now suppress new navigation guidance while such an uncertain hold exists,
without discarding the current native-routed session or assuming that the
driver chose a turn. After an unambiguous observed transition guidance can
resume. The original legality checks still prevent a forbidden manoeuvre.
An unrelated parallel service road remains ambiguous, not an authorised
transition.

The real-Wigan replay now counts junction holds, and it fails the safety gate
if any spoken instruction is made available during one. The existing short
destination ambiguity cases remain **unresolved**; this change cannot turn a
5.4-metre ambiguous segment into a falsely proven arrival.

This is a conservative research improvement and must not be treated as a
verified on-phone GPS, navigation or Bluetooth fix without the required device
and independently grounded UK road tests.

The first regression run exposed a status compatibility regression: shared-node
uncertainty was labelled `guidance_unavailable`, hiding the existing
`junction_position_uncertain` instruction result. `Planner.targets` now
preserves the **specific** uncertainty status while still suppressing speech.
The existing independent instruction-timing regression is not changed.


## Separate original and held-out real-road Wigan journeys

After establishing the junction-position guidance gate (483 regression methods
passing; 226 identified real-geometry junction holds; **zero instruction
events during those holds**), the routine now runs **8 original cases** plus
**8 additional held-out routes** from the same dated Wigan road extract.
The original eight endpoint pairs and case identifiers remain fixed, even
though the sampler normally changes its stride as the requested total grows.

The report preserves a separate `cohort_scorecard` for the original and
held-out subsets and reports each component's pass/fail/unresolved status.
No route is omitted because it is short, ambiguous, legally challenging,
or contains an unexpected GPS behaviour. If eight distinct additional
public-road cases cannot be selected, the test is **unresolved/error**,
not a substitute for synthetic geometry.

This does not provide independent *real-life* GPS truth or phone validation.
Neither a native response pass nor merely withholding speech constitutes
a verified lane, roundabout or turn-instruction pass.


## Holdout revealed classification bug — use actual fix confidence, not road length

In first 16-route real Wigan replay (run 38696751702), the existing
eight remained unresolved. The additional held-out eight produced 2 arrival
confirmations, 6 non-arrivals and two nominal failures on 8.42-metre final
segments. Both nominal failures had *three consecutive final ambiguous
match results and no confirmed correct-road GPS sample*. They were
misclassified as failures solely because the earlier **8 m** threshold
applied to the original short-road cases but not to 8.42 m.

The classification now asks for **three consecutive unresolved final
map matches with no accepted final-road fix**, without any arbitrary
road-length gate. It reports `destination_geometry_ambiguous_without_confirmed_arrival`,
not a successful arrival. Genuine far-from-junction wrong-road matches,
route discontinuities, unsafe speech, and unexplained non-arrivals
remain failures. We preserve the earlier first-run labels as historical
evidence; future runs use the corrected method.

Importantly, **no navigation position, legal access, roundabout or GPS
algorithm has been relaxed to obtain a green score**. These roads still
need independent evidence before phone integration.
