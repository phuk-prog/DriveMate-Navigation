# DMN priority: determine best navigation for existing DriveMate Android app

This is a **research and comparison plan**, not a standalone phone-app build plan. The [DMN scope](DMN_SCOPE.md) supersedes outdated standalone wording.

1. [x] Inventory and retain actual DMN routing/GPS/guidance research implementations and test data.
2. [x] Store measured passes, failures and unresolved outcomes per check without manufacturing competitor results.
3. [x] Provide evidence-only component selection report for the phone.
4. [ ] Fix/judge Wigan GPS junction and short-link ambiguity without weakening road legality.
5. [ ] Run repeatable hard GPS tests: side-by-side roads, tunnels, errors, corners, recovery, false reroutes.
6. [ ] Test UK restrictions, roundabouts, complex lanes, correct junctions and instruction timing against independent truth.
7. [ ] Compare actual external engines per equivalent navigation category, including held-out routes and complete journeys.
8. [ ] Evaluate mobile offline maps, memory, battery, rerouting, audio/Bluetooth and licensing.
9. [ ] Recommend proven components with evidence, uncertainties, ownership and integration cost.
10. [ ] Obtain approval before integrating components into the **existing** DriveMate Android app.

## Historical detailed engineering checklist

# Development roadmap — evidence before claims

- [x] Create independent repository and synthetic Dijkstra routing/reference test harness.
- [ ] Document and approve a project-wide licence before distributing derivative components.
- [x] Introduce bounded OSM XML importing with provenance hash, basic node-via restrictions, one-way/access checks and synthetic topology tests.
- [x] Add automated public-repository privacy preflight; continue mandatory manual code/data review.
- [x] Add opt-in local public PBF subset conversion with contributor-metadata stripping (no CI downloads, files remain untracked).
- [ ] Implement production-capable OSM PBF importer, conditional/time-dependent rules, vehicle exceptions, complex via-way restrictions, barrier and regional graph verification before any real-world routing.
- [x] Add offline aggregate-only response parsers for OSRM, Valhalla and GraphHopper using synthetic examples (not yet live benchmark adapters).
- [x] Add guarded, public-road-only OSRM MLD runtime smoke: real image, same input extract, no paid API, benchmark clearly marked non-comparable until vehicle policies and timing interfaces are harmonised.
- [x] Prepare Valhalla official-container public-only integration smoke using the same pinned UK extract and privacy/accuracy caveats.
- [x] Add guarded GraphHopper 11.1 standalone Java web-service reference to the shared public-road test framework (exploratory, not directly comparable).
- [ ] Add comparable, independently validated OSRM/Valhalla/GraphHopper benchmarks with audited equivalent motorcar profiles and real road restriction ground truth.
- [ ] Record constraints for commercial reference providers; do not invoke billable or restricted APIs without approval.
- [ ] Measure an independently chosen, public-data-only UK graph on test Android hardware, with no user's route history, device IDs or private journeys.
- [ ] Implement offline graph/region updates and crash-safe rollback.
- [x] Add turn-aware A* with checked geometry; compare its shortest-time output against Dijkstra on synthetic graphs.
- [x] Add opt-in one-time pinned Geofabrik UK road smoke: ephemeral public extraction and Dijkstra/A* parity test; execute only on a commit explicitly marked `[uk-road-smoke]`.
- [ ] Prove A* latency/memory benefits on independently licensed public-road graphs and Android hardware.
- [ ] Add GPS matching, map uncertainty, tunnels and rapid off-route recalculation.
- [ ] Add instruction and junction/lane legality validation, including multi-exit UK roundabouts.
- [ ] Train local/privacy-respecting prediction models and measure benefits on withheld journeys.
- [ ] Implement on-device Android navigation, UX and accessibility; ensure safe offline behaviour.
- [ ] Run emulator, robot and real-device validation before considering integration with DriveMate.

No performance, quality, or legal-road claims are proven by the initial synthetic harness.
