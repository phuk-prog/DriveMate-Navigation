# TURN-001 five cases — official-source evidence audit (17 October 2026)

**Scope:** Category 1 research evidence only. No changes to navigation, road
restrictions, access policy, source map, benchmark verdicts, Android or APK.
Follow-up to [the five-case graph diagnostic](https://github.com/phuk-prog/DriveMate-Navigation/pull/7)
and [TURN-001 v1.3](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39019749346).

## Independent sources found

1. [Department for Transport D-TRO guidance](https://www.gov.uk/guidance/digital-traffic-regulation-orders-d-tro-service).
   D-TRO provides machine-readable road-restriction extracts for navigation;
   importantly, a **D-TRO is not the legal order itself**. Using the service
   costs nothing but a consumer needs to register. **No service account,
   token or case-level D-TRO record was accessed in this review.**
2. [D-TRO terms](https://d-tro.dft.gov.uk/terms_and_conditions):
   D-TRO **data** is published under the Open Government Licence v3.0,
   including attribution. The licence for the portal's software/content is
   separate. [DfT v4 data-model guidance](https://d-tro.dft.gov.uk/data-model-user-guide/v4.0.0/a_tour_of_the_data_model.html)
   notes that published non-point vertices may be shifted 0.5–0.75 metres,
   so do **not** use D-TRO geometry alone for lane-precise map matching.
   The official [DfT D-TRO GitHub](https://github.com/department-for-transport-public/D-TRO)
   states production data specification v4.0.0 is live and candidate
   v5.0.0 documentation was released on 1 October 2026. Avoid using a
   v3.4.1-only parser based on older documentation.
3. [Manchester City Council proposed TRO notices](https://www.manchester.gov.uk/online-directories/consultations-and-surveys-directories/traffic-regulation-order-notices).
   This directory is only an **entry point**; it does not itself verify
   the five case-specific turns or their current operation.
4. [Trafford Council TRO guidance and register](https://www.trafford.gov.uk/streets-roads-and-transport/roads-highways-and-pavements/road-closures-regulations-and-permits/traffic-regulation-orders-tros).
   An order needs a final making notice to be in force; the general
   register page is not proof that an exact Talbot Road manoeuvre is legal.
5. [Salford City Council traffic-order archive](https://www.salford.gov.uk/parking-roads-and-travel/roads/traffic-orders/).
   The [2019 Chesterfield Close area order notice](https://www.salford.gov.uk/parking-roads-and-travel/roads/traffic-orders/chesterfield-close-area/)
   describes proposed **20mph and no-waiting** changes and links to those
   plans, **not** a no-straight-on restriction. It may help locate a
   council file, but is **not evidence for or against** OSM relation 4853555.
6. [Rochdale Borough Council proposed permanent restrictions](https://www.rochdale.gov.uk/roadworks-repairs-restrictions/proposed-permanent-restrictions-highways-traffic-regulation-orders).
   A potential jurisdictional starting point for relation 16644804,
   subject to identifying the exact road authority. General council
   notices cannot be upgraded to site-specific truth.

## Current five-case casebook

All source leads and coordinates are recorded in
[`config/turn001-official-evidence.json`](../config/turn001-official-evidence.json).
Exact frozen OSM relation IDs and case-specific statuses:

| Relation | Reported junction | What remains to independently confirm | Status |
|---|---|---|---|
| 10558420 | Devonshire Street (53.5048025, -2.2567149) | Exact final TRO and sign controlling straight-ahead vehicle movement, jurisdiction and geometry | **UNVERIFIED** |
| 13613008 | Talbot Road (53.4525815, -2.2995611) | Whether an only-U-turn instruction genuinely exists, sign effectiveness, permitted vehicle manoeuvre and available turning room | **UNVERIFIED** |
| 16644804 | Unnamed service-road junction (53.6023943, -2.1703982) | Highway ownership/access and exact left-only turn control; check which authority holds records | **UNVERIFIED** |
| 4853555 | Chesterfield Close (53.4849465, -2.3631244) | Specific straight-ahead ban; 2019 speed/waiting order is **not** that proof | **UNVERIFIED** |
| 7615778 | Unnamed service road (53.4826549, -2.2254736) | Genuine legal ban, current signs, ownership, and permissions for a destination tagged `access=private` in OSM | **UNVERIFIED** |

**Result: 0/5 independently verified.** This is a completed source-audit
milestone, not a five-case road-law clearance and not five proven navigation
engine faults. No engine was benchmarked or modified as part of this review.

## Correct next evidence steps

For each site, obtain the **actual operative legal order** or an authoritative
statement of the applicable movement, including plan, effective dates, exemptions
and possible revocation, from the confirmed highway authority. Corroborate with
dated, lawfully sourced junction signage and carriageway geometry. Record the
driver/vehicle access conditions and explicit route approach.

Where D-TRO is available, compare it to the final legal document and sign evidence;
record source revision and geometry offsets. Do not use an empty D-TRO search as
proof that no restriction exists, because publishing may be incomplete and
digital extracts are not the legal text. Do not scrape proprietary imagery or
use unlicensed routes/data.

**Do not alter DMN's behaviour** because a council directory, an OSM tag,
a route engine, or an unauthenticated map image seems plausible. If evidence
conflicts, mark CONFLICTED and hold any route-rule change. A confirmed
correction needs owner approval plus a freshly executed frozen common-cohort
comparison across DMN and all available applicable competitor engines.

## Evidence-integrity regression

`python3 -m tools.turn001_official_evidence_guard --self-test` checks
the five fixed case IDs, credible source references, case statuses and
the rule that VERIFIED needs dated, geometry-matched **two-source**
corroboration including the exact operative order and site signage.
It also verifies that an evidence file cannot itself authorize an
engine-driving-policy change.

The guard is **not a legal verification engine**; it is a regression
against accidental promotion of unverified restrictions to road truth.
