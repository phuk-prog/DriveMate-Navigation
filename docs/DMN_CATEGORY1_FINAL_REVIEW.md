# DriveMate Navigation — Category 1 consolidated research closeout
**17 October 2026 · Navigation engine/map graph only · NO APP/APK · NOT A UK ROAD-LAW CERTIFICATE**

This completes the **registration-free, executable research closeout** of
Category 1 on a separate branch. It does **not** claim every road restriction
or every external graph feature is independently verified.

## Exact executed evidence

The CI [Category 1 final scorecard 39029966922](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39029966922)
**PASSED** and published reproducible JSON and Markdown. It verified every
input count, immutable cohort/source SHA, multi-engine result and
non-comparability limitation against the original archived job summaries
without paying for or repeating completed six-region runs.

| Independent test contract | Engine | Passed / judged cases | Failures and withheld |
|---|---|---:|---|
| MAP-001 six-region original-way source audit | DMN ★ | 79/120 | 41 SAFE_WITHHELD (various ambiguous or contextual access); 980 directed source-segment checks |
| MAP-001 native OSM car-access common subset | DMN ★ | 78/78 | 0 failures on 714 identical directed segments |
| MAP-001 native OSM car-access common subset | Valhalla 3.9.1 | 78/78 | 0 failures on those same 714 segments |
| TURN-001 v1.3 real Greater Manchester route-turn restriction check | DMN ★ | 131/142 | 0 prohibited manoeuvres, 5 safe no-routes, 6 mapped closed endpoints |
| TURN-001 v1.3 same 142 cases | Valhalla 3.9.1 | 112/142 | 9 prohibited target moves, 3 other-rule-invalid PASS candidates, 18 off-target |
| TURN-001 v1.3 same 142 cases | OSRM 5.27.1 | 111/142 | 3 prohibited moves, 2 other-rule-invalid candidates, 13 off-target, 13 no-routes |
| TURN-001 v1.3 same 142 cases | GraphHopper 11.1 | 66/142 | 68 finalised off-target, 7 no-routes; 1 additional-rule-invalid PASS candidate |
| BARRIER-001 v1.2, closed/open barriers only | DMN ★ | 46/61 | 0 illegal crossings, 15 safe no-routes |
| BARRIER-001 v1.2, same 61 judged cases | OSRM 5.27.1 | 46/61 | 0 illegal crossings, 12 off-target |
| BARRIER-001 v1.2, same 61 judged cases | Valhalla 3.9.1 | 42/61 | 0 illegal crossings, 18 off-target |
| BARRIER-001 v1.2, same 61 judged cases | GraphHopper 11.1 | 9/61 | 0 illegal crossings, 40 off-target |

**MAP v2/v3 contracts are different.** The original v2 measured
107 PASS, 8 SAFE_WITHHELD, 5 NOT_JUDGED out of 120, and the v3 source
scorecard counted 109 PASS, 9 SAFE_WITHHELD, 2 NOT_JUDGED.
The **newer source closure** measures a more conservative 79 PASS and
41 SAFE_WITHHELD under the exact directed road-access agreement contract.
Do not depict 107→109→79 as driving-quality degradation or improvement:
they are different scoring contracts and/or source snapshots.

**Partial rankings only.** DMN ties Valhalla 78/78 for the native
binary car-access cohort. For turn-restriction *route output* among four
engines, rank DMN > Valhalla > OSRM > GraphHopper by legal passing routes
under the frozen **OSM-derived** oracle. For judged bollard/gate *route
output*, DMN and OSRM tie on legal passes, ahead of Valhalla and
GraphHopper. These measures are not a single full-category engine
ranking, and their execution timing scopes are not comparable.

All source-map agreement remains **PROVISIONAL** unless independently
dated and geographically matched to authoritative current road-law
documents. Only two of eleven inspected physical node-barrier cases had
matched closed native node AutoCost mask indicators. Structural native
masks do not fully evaluate permissible arrivals, departures, conditional
orders, exemptions or physical turnaround safety. The v3 archive also
covers 26 source restrictions and nine barrier-related ways; those
diagnostics are not proof of full native legal-graph parity.

## GraphHopper investigation — tested and closed as a negative finding

The historical 142-case archived base-clip diagnosis showed GraphHopper
67 UNRESOLVED_SNAP outcomes (**68 after original wide-clip finalisation**).
On 54 of the 67, a same-case DMN PASS path was an exact-segment
reference. GraphHopper's path differed at the start alone 41 times, at
the destination alone 11 times, and at both ends twice.

GraphHopper publicly documents that `heading` adds a preference with
an adjustable penalty, not a categorical snap-to-edge guarantee:
https://github.com/graphhopper/graphhopper/blob/master/docs/web/api-doc.md

The author-approved [twelve frozen-case trial](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39029550716)
ran GraphHopper 11.1 with the SAME waypoints, route request and engine
configuration except increasing `heading_penalty` to 86,400 seconds.
The job **PASSED** with no query/setup failures:
- Six previously wrong starting-segment cases: **0** turned into legal
  exact-edge passes.
- Three previously wrong destination-segment cases: **0** corrected.
- Three already correct controls: **3/3** remained correct.

**Decision:** this trial does not justify an adapter change. Do not
artificially reroute a reference, override its OSM attachments or
downgrade the exact-edge oracle to make a score green.
Root cause (native edge snapping vs partial geometry decoding) remains
**DIAGNOSED / NOT INDEPENDENTLY PROVEN**. Original benchmark results
are preserved; no fresh full TURN-001 ranking is claimed from this
12-case subset.

## Category 1 exact outstanding issue register

| Priority | Exact issue | Evidence | Disposition |
|---|---|---|---|
| High | Five no-route turn cases 10558420, 13613008, 16644804, 4853555, 7615778 | Graph search using archived frozen OSM; no full-legal-route comparator | **DIAGNOSED; independent legal existence unverified** |
| High | Destination `access=private` at 7615778 | Frozen OSM way tag | Withhold public-car permission; do not automatically authorize |
| High | Unknown/private gate trip endpoints (30 cases; 28 originating on unknown service road, 2 ending beyond private gate) | BARRIER-001 v1.2 OSM cohort | Retain UNKNOWN and the existing conservative destination/start policy; no free public passage established |
| High | Two apparent BARRIER-001 missed alternatives at 2092919405 and 416565753 | Both competitors' routes cross OTHER unmarked gates | **Zero known-access legal alternatives**; do not tune DMN to comparator guess |
| High | Full native graph turn/physical-barrier parity | 26 source restrictions, 9 barrier ways, 11 barrier nodes; only 2 closed node AutoCost indicators matched | **NOT_EQUIVALENT**; no fictitious full Category 1 winner |
| Medium | GraphHopper 54 comparable exact-edge misses | TURN-001 archive, 12-case strong-heading trial | **DIAGNOSED, proposed parameter fix rejected by measured results** |
| Medium | Closed-barrier stub approach and turnaround | BARRIER cohort showed no legal case lost under scoring | Await dated real geometry/access and feasible turnaround; never presume legal/possible |
| Medium | Conditional vehicle/purpose/time access | MAP-001 v3 and conservative importer; simple syntax parses are not road-rights | **SAFE_WITHHELD**; no unrestricted routing inferred |
| Medium | Current authoritative road signs/TROs | Official DfT/public councils, D-TRO registration requirement | **Owner rule: do not register; leave unverified** |
| Medium | Full equivalent internal graphs for OSRM/GraphHopper and proprietary products | Those adapters expose partial route outputs, not the full common legal graph | **UNSUPPORTED**, not zero-quality scores |

None of these unverified facts has been promoted to engine legality or
an actual driving instruction. No confirmed new DMN unsafe violation
was found in the judged frozen source cases; this is not proof against
unobserved UK-road failures.

## Completed work and approval boundaries

- Existing directional-access importer fix and MAP-001 v3 graph/Valhalla
  native investigations are already in the parent research branch and
  remain unmodified by this closeout.
- Integrated the **previously executed BARRIER-001 v1.2 scoring code**
  and its review, plus the earlier five no-route and official-source
  investigation documents, without duplicating their historical runs.
- New [GraphHopper 12-case CI](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39029550716)
  and [final evidence validation CI](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39029966922)
  both PASS; combine only where each category keeps independent totals.
- Integrated-branch fresh
  [BARRIER-001 four-engine run 39029643326](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39029643326)
  validates the copied v1.2 scorer against all original frozen clips;
  **PASSED all 6 jobs** on revision `138be2a`; exact same 110 frozen/94
  testable/92 discriminating and DMN 46 legal passes/0 illegal
  barrier crossings as the earlier v1.2 run. GraphHopper 9, OSRM 46
  and Valhalla 42, all zero observed closed-barrier crossings.
- The separate draft PR branches have not been merged to production or
  Android. No registrations, paid provider, personal GPS, Android build,
  APK release or Category 2 test.
- Category 1 research is **executed and independently reported** on
  available, legally usable inputs. It remains **NOT independently
  UK-law verified** or fully internally graph-equivalent across
  all desired competitors.

The research completion is a **review gate**, not permission to start
Category 2. Remaining tasks that depend on unavailable registration or
external public-road proof remain marked diagnosed, not PASS.
