# TURN-001-NO-ROUTE-5 — focused road-graph investigation

17 October 2026. **Category 1 engine research only.** No change to the driving
engine, map, scoring contract, Android application, or any historical result.

## Evidence and limits

- Archived four-engine baseline: [TURN-001 v1.3, run 39019749346](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39019749346);
  original results in [TURN_001_RESULTS.md](TURN_001_RESULTS.md). These are **not**
  fresh reference-engine reruns.
- New **independent search implementation on the same OSM map, not an
  independently sourced road-law oracle**: [focused Actions run
  39027815145](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39027815145).
  The `diagnose` job passed. Machine-readable 5-case summary, including
  exact way tags, coordinates, snap endpoints, state counts and graph-audit
  limitations, is retained in that run's
  `turn001-no-route5-diagnostic` artifact.
- The diagnostic loads the five original case clips and separately explores
  directed road arcs with (1) one-way only, (2) one-way plus via-node bans
  while ignoring access restrictions, (3) mapped car access plus via-node
  bans, and (4) scenario 3 without just the target relation. This is a
  breadth-first state search over (previous node, current node, way), **not
  DMN's route algorithm**.
- Frozen hashes: source
  `2a8ef8e1f2533cb009b1ce248a6bf4eaabdd47e03979e64e24cd844f3b22acba`,
  case cohort
  `f2949a8a9aab40b7f62bc658cf92778f440ab5cdcc7ffcc755e21dc1b83c391c`,
  prepared case descriptions
  `8500d8f3d9cf99660fcc3267ad422134fce87cbb946fe25f6940763546707bf3`.
  The script also SHA-checks each individual clip before examining it.

## Five exact cases — new result

| OSM relation | Target rule | Roads/setting from frozen OSM | All drivable-class roads, one-ways only | Same with mapped via-node turn rules | Ordinary car-access plus rules | Without target rule |
|---|---|---|---|---|---|---|
| `10558420` | no_straight_on | Devonshire Street → Devonshire Street (53.5048025, -2.2567149) | Reachable | **No route** | No route | Reachable |
| `13613008` | only_u_turn | Talbot Road → Talbot Road (53.4525815, -2.2995611) | Reachable | **No route** | No route | Reachable |
| `16644804` | only_left_turn | Unnamed service road → unnamed service road (53.6023943, -2.1703982) | Reachable | **No route** | No route | Reachable |
| `4853555` | no_straight_on | Chesterfield Close → unnamed service road (53.4849465, -2.3631244) | Reachable | **No route** | No route | Reachable |
| `7615778` | no_straight_on | Unnamed service road → **private-access** service road (53.4826549, -2.2254736) | Reachable | **No route** | Destination excluded | Destination excluded |

**Meaning:** all five endpoint pairs are connected by an OSM-directed route
when restrictions are ignored; on these **base clips**, none has an
alternative respecting the applicable nonconditional via-node bans, even
if access controls are relaxed. The other four become reachable on the
stricter OSM graph with their tested relation removed. In `7615778`,
the destination is itself tagged `access=private`; removing only the
ban cannot make that road available to a generic publicly routed car.

The original DMN baseline tried the cases on wider (3x) clips as well and
reported no route for all five. The new graph diagnostic ran on the
**base clips only**, so it is *not* a new independent wide-area proof.

### Historical four-engine evidence on these exact cases

- **10558420:** OSRM and Valhalla took the banned straight-on move;
  GraphHopper found no route.
- **13613008:** Valhalla breached the only-U-turn restriction; OSRM
  reached a different road segment, and GraphHopper had no route.
- **16644804:** OSRM found no route; Valhalla and GraphHopper ended on
  different road segments.
- **4853555:** OSRM and Valhalla finished on different road segments;
  GraphHopper found no route.
- **7615778:** all three competitors finished short/on a different
  segment; the requested destination road has a private-access tag.

**Not an engine ranking.** These five were selected precisely because
DMN had no route; this is a diagnostic subset, not an unbiased competitive
cohort. Refer to the full 142-case TURN-001 v1.3 results for rankings.
No external engine was re-run in the new analysis.

## Issues and validation still needed

1. **External legal truth is unknown (all five).** Confirm the current
   signs, carriageway, permissible manoeuvres and effective TRO/highway
   restrictions through dated local highway authority records, legal
   imagery and independent corroboration. OSM and engine consensus do
   **not** establish what is lawful on the road.
2. **Endpoint permission at 7615778.** The mapped destination has
   `access=private`. A route may be permitted to an authorised driver,
   but this cannot be assumed for general public routing. Keep access
   conditional/unknown until verified.
3. **Physical U-turn at 13613008.** A relation saying
   `only_u_turn` does not prove a safe physical turnaround of any vehicle
   at the junction. Verify signs, junction layout, vehicle dimensions
   and nearby restrictions.
4. **Analytical scope:** graph diagnostic does not enforce via-way or
   conditional restrictions, real-world barriers, unknown gate rights,
   or physical turnaround clearance. For `7615778`, it counted four
   complex nearby relations as unjudged. A **no-route** in the relaxed
   graph is still strong map-topology evidence but cannot prove there
   is no lawful real-world route beyond the clipped extract.
5. **Do not weaken DMN turn or access checks to make any of these pass.**
   If independent evidence establishes a lawful alternative, create a
   named, frozen case correction and rerun DMN plus *all applicable
   installed competitors* over the complete affected comparable cohort
   and affected regressions. Preserve every existing result.

## Current conclusion

**5/5 remain NOT_INDEPENDENTLY_VERIFIED.** The frozen graph analysis
supports withholding a speculative route; it has not established five
DMN faults or proven five physically impossible journeys. One case has
an additionally mapped private-access endpoint. The remaining step is
external, site-specific lawful access/road-sign verification, not a blind
routing-engine adjustment.
