# DMN GPS next diagnostic: distinguishing physical source segments

**Why:** on the last common 12-case public UK GPS experiment, all engines' matched near-road outputs were recorded as having other OSM *directed* roads within 10 m. That historical result included reverse directions on the same two-way segment and junction-adjacent links. It did **not** establish physical parallel roads, incorrect carriageways, or a navigational superiority ranking.

## New independent diagnostic categories
- `near_with_opposite_direction_of_same_segment`: mapped reverse edge with the same two OSM node endpoints. It is NOT a second road. A snapped coordinate alone still cannot prove which direction the vehicle traveled.
- `near_with_connected_junction_segments`: a different unique graph segment sharing an endpoint with the generating segment; at/near a junction it can be expected.
- `near_with_disjoint_graph_segments`: a different unique segment within 10 m but not sharing graph endpoint. **Not yet proof of a separate physical roadway**, because map segmentation/layers/provenance require separate verification.
- Keep the existing raw `near_but_alternative_directed_roads_within_10m` count for backwards comparability. Categories are non-exclusive and MUST NOT be added to make a pass percentage.

This decomposition uses ONLY publicly generated OSM node/edge IDs; it never consults the known generating edge to change DMN decisions. The observations are not independent road truth and source-level reverse edges cannot prove travel direction. Do not promote the experimental multi-hypothesis matcher: the [latest pinned OSRM run](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38771616932) measured **6/12 correct / 0 confidently wrong / 6 withheld** for that experiment versus the established temporal matcher's **8/12 correct / 0 confidently wrong / 4 withheld**. It rescued **0** prior withheld and lost **2** previous correct. This was a **comparative research result**, not proof of real GPS positioning.

## Acceptance sequence
1. Run unit regressions for reverse road, connecting segment, disconnected overlapping carriageway and aggregate denominators.
2. Re-run pinned local OSRM matching once on the same public UK four-fix cases, using the enhanced common geometry report. Check all categories and keep unsupported or unknown as such.
3. Review the count of genuinely graph-disjoint alternatives on each matcher; only then choose a direction-aware temporal algorithm change supported by test cases. Any resulting code must beat the established matcher **without increasing confident wrong-road assignments**.
4. Expand to hard held-out real UK dual carriageways, slip roads and underpasses. Use independent signs/restriction evidence for legal-movement scoring. Never infer physical lanes/layer from coincident point coordinates alone.

No production app modification, APK, private GPS, paid API or unsupported competitor access.
