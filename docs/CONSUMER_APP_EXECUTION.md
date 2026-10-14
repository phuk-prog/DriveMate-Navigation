# Consumer navigation comparison execution

Scope: compare DriveMate against the agreed ten-app lineup using the same
verified UK public-road journeys. The lineup is a benchmark selection, not a
claim that market-share research established an exact top ten.

Categories, executed separately:

1. Positioning on straight roads, corners, parallel roads and slip roads.
2. Positioning quality rejection, GPS loss and recovery.
3. Route legality, one-way roads, access and prohibited turns.
4. Reroute detection, time until a usable new route, and false reroutes.
5. Junction and roundabout instructions and exit counts.
6. Lane guidance correctness and confidence. Road matching is not proof of
   identifying the occupied lane; lane-position ground truth is required.
7. Instruction timing, ordering, duplicate delivery and stale instructions.
8. Full journey, arrival, offline operation and resource use.

Systems: DriveMate, Google Maps, Waze, Apple Maps, HERE WeGo, TomTom,
Sygic, OsmAnd, Organic Maps, Magic Earth, MapFactor Navigator.

Run currently executable DriveMate checks:

    python3 -m tools.run_navigation_categories
    python3 -m tools.run_navigation_categories --category positioning

The runner executes every selected check, retains separate logs, continues
after a failed check, and exits unsuccessfully if any check fails or times out.
Its wall time measures the validation workload, not phone rerouting latency.
The existing synthetic fixtures are not verified real UK journeys.

Fresh execution on 2026-10-14 from base revision
38f484135db55bff3d383010b66902c6e6751c68:

- Regression: 386 tests ran successfully; one was skipped.
- Positioning projection: 4,800 cases, zero failures.
- Roundabout GPS journeys: four passed.
- Recovery: 1,536 cases, zero failures; 768 recovered, 768 withheld.
- Instruction timing: 2,304 scenarios, zero failures.
- Whole drive: 16 passed, zero failures.

These are synthetic DriveMate results. No consumer-app scores are inferred.

Provisioning completed locally: Android command-line tools, platform-tools,
emulator and Android 35 Google APIs x86_64 image. Hardware acceleration check
failed because KVM/CPU virtualization support is unavailable. Software-mode
startup is a feasibility probe, not a fair latency benchmark.

Organic Maps official release 2026.09.29-32-android was downloaded and its
SHA-256 matched the digest published with the GitHub release asset:
d7dbdfc3cbfdbcce6d437f11147f2cd15384c03052d2b4594fd8c1c7777dd497.
Download and installation readiness are not navigation test results.

Scores require repeatable app observations on the same route/GPS input,
independently verified expected behaviour, declared app/map versions and
settings, and comparable hardware/network conditions. Consumer maps may have
different snapshots; disclose these differences rather than claiming identical
datasets. Record live traffic separately from deterministic replay. Untested
categories remain unscored, and partial coverage cannot establish an overall
ranking. Improve DriveMate from observed defects, then retest against held-out
cases as well as the original failing case.
