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
