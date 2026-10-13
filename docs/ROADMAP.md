# Development roadmap — evidence before claims

- [x] Create independent repository and synthetic Dijkstra routing/reference test harness.
- [ ] Document and approve a project-wide licence before distributing derivative components.
- [ ] Implement an OSM importer with licence/provenance manifest, conditional access rules and independently tested topology.
- [ ] Add same-map benchmark adapters for Valhalla, OSRM MLD, GraphHopper and suitable Android-native references, after verifying their licences.
- [ ] Record constraints for commercial reference providers; do not invoke billable or restricted APIs without approval.
- [ ] Measure a Greater Manchester graph on actual Android device hardware.
- [ ] Implement offline graph/region updates and crash-safe rollback.
- [ ] Compare a fast routing algorithm against the deterministic shortest-path reference.
- [ ] Add GPS matching, map uncertainty, tunnels and rapid off-route recalculation.
- [ ] Add instruction and junction/lane legality validation, including multi-exit UK roundabouts.
- [ ] Train local/privacy-respecting prediction models and measure benefits on withheld journeys.
- [ ] Implement on-device Android navigation, UX and accessibility; ensure safe offline behaviour.
- [ ] Run emulator, robot and real-device validation before considering integration with DriveMate.

No performance, quality, or legal-road claims are proven by the initial synthetic harness.
