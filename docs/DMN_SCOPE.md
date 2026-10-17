# DMN working agreement — 15 October 2026

**DMN** abbreviates **DriveMate Navigation**. Use the abbreviation DMN in new research-facing work, scorecards and test labels. Legacy file paths, Git history and engine names remain intact to preserve existing tests and traceability.

## Engine-first design clarification (15 October 2026; confirmed direction)

The owner clarified that the **best complete DriveMate app** is the end goal, but **DMN navigation correctness and engine design lead the research programme**. Do not force DMN to fit existing app architecture. When navigation requirements reveal inadequate graph/map data, map matching, rendering, routing, offline updates or other software, investigate and improve/rebuild those dependencies where evidence justifies it. Follow dependent changes, validate independently, then use the isolated Android testing branch as a compatibility check. Retain production untouched, and do not release an APK.

[Active engine-first proposal](DMN_ENGINE_FIRST_PROGRAMME.md) · [ten-reference test protocol](DMN_TEN_REFERENCE_PROTOCOL.md) · [owner's unsettled test decisions](DMN_DECISION_QUESTIONS.md).

Older milestones and benchmark statements below are a **dated historical snapshot**, not proof that the later real-UK research never ran. Numeric thresholds and exact choice of ten references are pending questions, not confirmed assumptions.

## Goal

Find the best reliable, accurate, efficient, legally redistributable navigation technology **for the existing DriveMate Android phone app**. DMN is the test, research and candidate-component project, **not** a separate standalone app and has **no standalone APK milestone**.

The compiled native C++ routing engine and Python research GPS, guidance and rerouting components are DMN candidates. Do not describe host-level simulations as Android app tests, phone readiness or full navigation passes.

## Development and decision process

1. Use the existing DMN repository and its implemented components as the first candidate; use external engines as real, independent comparison references.
2. Work one navigation category at a time: legal routing and UK turn rules, GPS/map matching, GPS loss and recovery, rerouting, roundabouts, junctions and lanes, instructions, full journeys, performance and phone resources.
3. Exercise normal, unusual, difficult and adversarial scenarios. Include real English OSM road geometry where supported, independent ground truth for legal movements, and held-out fixtures.
4. For *every* category, report cases passed/total, failed, unresolved, unsupported and not-tested. A test omitted or guidance withheld is **not** a pass.
5. Correct the identified fault, rerun the focused case, complete regression suite and held-out cases. Preserve the earlier failing evidence and investigate any regression before approval.
6. Compare external engines on equivalent data and interfaces; report variant/profile/map differences and environmental setup failures. No manufactured scores or claims that one route-speed benchmark proves complete navigation superiority.
7. Select phone components only with evidence for accuracy, legal routing, licensing and ownership, Android offline support, memory, battery, reroute latency and real-device/audio/Bluetooth behaviour. The highest host-speed result does not necessarily win.
8. Ask for explicit approval before modifying **phuk-prog/DriveMate**, the existing Android production app. Nothing in DMN research automatically triggers production builds or releases.

## Latest grounded status

The Wigan full-journey research run [38657109810](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38657109810) used the native compiled C++ candidate with synthetic GPS fixes over real English road geometry: eight of eight native routes returned valid responses, six of eight simulated arrivals were observed, and **zero of eight complete journeys met all acceptance checks**. All eight remained unresolved because of junction-area GPS matching evidence. This is not a live phone/device benchmark. Speed comparisons with OSRM/GraphHopper/Valhalla are separate routing-latency research.

## Privacy and licensing

No private user location history, real personal GPS, proprietary maps or personal imagery may enter this public repository. Public OSM data has independent attribution and ODbL conditions; external code, apps and map providers each need verified redistribution and use rights. We prefer original code and do not copy competitor source just because it is visible.
