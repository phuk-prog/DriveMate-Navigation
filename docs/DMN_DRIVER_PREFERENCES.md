# DMN driver-configurable routing preferences — approved 15 October 2026

**Owner direction:** implement all discussed route choices as driver-selectable options when the existing Android application is built. The recommended default is intelligent/balanced behavior, not a permanent restriction on drivers choosing fastest, shortest, fixed countdown or aggressive rerouting.

## Implemented now — research-only reusable decision contract

- `engine/driver_policy.py`: original, isolated policy types for route preference, alternative threshold, closure override, adaptive or fixed countdown, driver accept/reject and safe automatic switching. Decision helpers are deterministic and testable.
- `config/driver-navigation-settings.json`: machine-readable controls and defaults to bind to a later **DriveMate settings screen**. Round-trip settings serialization and options are unit tested.
- `tests/test_driver_policy.py`: default settings, every driver mode, verified legal-route filtering, predictions, adaptive/fixed sensitivity, 3–7 second countdown, accept/reject, no-response automatic action, stale evidence, safe maneuver revalidation, cooldown, bad settings and closure scenarios.

**Recommended defaults:**
- Route: **balanced** (driver can choose fastest or shortest).
- Reroute offer: **intelligent** (driver can choose always faster or closure only).
- Threshold: **adaptive** (driver can select any saving or fixed improvement, default fixed threshold 180 seconds).
- Countdown: **adaptive 3–7 seconds** (normally 5; fixed interval option). Offer the best verified alternate, let the driver accept or reject, switch automatically on timeout **only if still safe and verified**.
- Reduce needless complex maneuvers: **on** (driver may prefer speed instead).
- Automatic switching without response: **on**, user-switchable off for drivers who prefer explicit acceptance.

**NEVER selectable:** illegal turns or access, unverified lane assignment, ignoring genuine closures, bypassing stale/conflicting evidence checks, unsafe last-second rerouting, and claiming independent legal truth without evidence.

## What is NOT yet implemented

This policy selects from externally supplied eligible route options; it does NOT discover alternatives, fetch official road orders or traffic, run a live countdown, verify road legality, calculate safe lane changes, or operate an Android settings screen. The two caller-supplied flags `independently_verified_legal` and `evidence_current` are contractual requirements, NOT verified facts merely because Python accepted them. The Android app needs a production quality legal/road-evidence pipeline and navigation controller. A controller MUST re-check route candidate identity, evidence freshness, safe movement and driver response at switch time, and must provide the offer UI and voice notification without distracting the driver.

The objective and adaptivity constants are **provisional tuning parameters**, not a validated safety or ETA rating. Evaluate with real UK road geometry and independently dated legal evidence and lawful competitor comparisons. Keep every missing/contradictory fact UNKNOWN and every competitor interface WITHOUT legal access NOT TESTED. Do not publish comparative scores from synthetic policy fixtures. Retain prior test evidence and rank only independently judged, equivalent cases.

## Integration checklist (later, not production now)
1. Add preferences storage on the existing DriveMate isolated testing branch, with accessible selectors, simple descriptions and an option to restore defaults. Do not use driver personal data in public research.
2. Connect the driver settings to candidate generation and preferences policy (not merely cosmetic toggles); show expected time saved and route differences; allow accept or reject; honor rejection cooldown.
3. Tie the countdown to an actual navigation session and safe maneuver feasibility, cancel when road evidence, GPS confidence or route candidate changes; safely keep route on unknown.
4. Test preference changes mid-drive, offline, app restart, closed road, high-speed motorway, closely spaced junctions, unknown lanes and bad GPS; benchmark against lawful accessible providers where genuinely equivalent.
5. The mandatory Android navigation robot, replays, regression, license audit and release gate must all pass before proposing an APK; keep `phuk-prog/DriveMate` production untouched.

This document records a NEW follow-up owner decision about Q9–12 rather than overwriting the earlier separate 22-question record.
