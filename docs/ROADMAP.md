# Development roadmap — evidence before claims

- [x] Create independent repository and synthetic Dijkstra routing/reference test harness.
- [ ] Document and approve a project-wide licence before distributing derivative components.
- [x] Introduce bounded OSM XML importing with provenance hash, basic node-via restrictions, one-way/access checks and synthetic topology tests.
- [x] Add automated public-repository privacy preflight; continue mandatory manual code/data review.
- [ ] Implement production-capable OSM PBF importer, conditional/time-dependent rules, vehicle exceptions, complex via-way restrictions, barrier and regional graph verification before any real-world routing.
- [x] Add offline aggregate-only response parsers for OSRM, Valhalla and GraphHopper using synthetic examples (not yet live benchmark adapters).
- [ ] Add same-map measured benchmark adapters for those engines and Android-native references, after verifying licences and acquiring public datasets unrelated to a user.
- [ ] Record constraints for commercial reference providers; do not invoke billable or restricted APIs without approval.
- [ ] Measure an independently chosen, public-data-only UK graph on test Android hardware, with no user's route history, device IDs or private journeys.
- [ ] Implement offline graph/region updates and crash-safe rollback.
- [ ] Compare a fast routing algorithm against the deterministic shortest-path reference.
- [ ] Add GPS matching, map uncertainty, tunnels and rapid off-route recalculation.
- [ ] Add instruction and junction/lane legality validation, including multi-exit UK roundabouts.
- [ ] Train local/privacy-respecting prediction models and measure benefits on withheld journeys.
- [ ] Implement on-device Android navigation, UX and accessibility; ensure safe offline behaviour.
- [ ] Run emulator, robot and real-device validation before considering integration with DriveMate.

No performance, quality, or legal-road claims are proven by the initial synthetic harness.
