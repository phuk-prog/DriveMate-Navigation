# DMN driver-configurable routing preferences — approved 15 October 2026

**Owner direction:** implement all discussed route choices as driver-selectable options when the existing Android application is built. The recommended default is intelligent/balanced behavior, not a permanent restriction on drivers choosing fastest, shortest, fixed countdown or aggressive rerouting.

## Implemented now — research-only reusable decision contract

- `engine/driver_policy.py`: original, isolated policy types for route preference, alternative threshold, closure override, adaptive or fixed countdown, driver accept/reject and safe automatic switching. Decision helpers are deterministic and testable.
- `config/driver-navigation-settings.json`: machine-readable controls and defaults to bind to a later **DriveMate settings screen**. Round-trip settings serialization and options are unit tested.
- `tests/test_driver_policy.py`: default settings, every driver mode, verified legal-route filtering, predictions, adaptive/fixed sensitivity, 3–7 second countdown, accept/reject, no-response automatic action, stale evidence, safe maneuver revalidation, cooldown, bad settings and closure scenarios.

**Recommended defaults:**
- Route: **balanced** (driver can choose fastest or shortest).
- Reroute offer: **intelligent** (driver can choose always faster or closure only). **Always faster** strictly means predicted travel-time improvement even if the driver separately prefers shortest routes; a shorter but slower alternative must never be called faster.
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

## Next implemented stage — bounded real route candidate search (research only)

The new original `engine/route_alternatives.py` calculates actual allowed directed paths using three independent objective modes (fastest estimated travel time, shortest distance, balanced time/distance with **explicit externally supplied** complex turns). It returns the mode-optimal paths plus bounded one-edge detour alternatives and deduplicates identical paths. All proposed route IDs include the source map snapshot ID; temporary per-edge delay estimates may affect fastest and balanced but not shortest distance. Established Dijkstra and A* remain unchanged as independent timing/control baselines.

**Safety:** allowed OSM graph edges and an OSM-legal turn do not establish independent UK legality. `GeneratedRoute.as_unverified_option()` explicitly sets both legal truth and source freshness to false. The selection gate consequently withholds these until a separate authoritative/corroborated verifier supplies evidence. There is no hidden auto-approval of a generated route. Turn restrictions, prohibited and unknown access, incoming-edge context and blockages apply to EVERY route objective; no driver preference can override them. Underlying delay estimates must be nonnegative, finite and supplied rather than automatically inferred from competitor output.

New `tests/test_route_alternatives.py` covers genuine fastest/shortest/balanced differences, fixed user preferences, graph legality, incomplete evidence, traffic delays, bad inputs, deterministic map-scoped IDs, and bounded distinct detours. The opt-in `benchmarks/public_uk_probe.py` now checks the three objectives on actual public UK map graph scenarios and separately states that this remains map-semantic, NOT signed legal-road truth. It is not a live traffic feed, final Android route controller, or complete k-shortest enumeration. In particular no published comparison score or safe driving certification follows from synthetic graph tests.

## Opt-in public UK road experiment

A single GitHub Actions `[uk-road-smoke]` opt-in will execute the public UK Geofabrik road subset test with `generate_route_candidates` enabled for each identical existing DMN route pair. It verifies route-profile computation, cost consistency with the existing independent Dijkstra baseline, and no bypass of imported mapped restrictions. This same-source experiment **does not** independently verify road signs, lanes, lawful route validity or live traffic, and cannot rank external apps. The existing historical public map snapshot is used solely for reproducibility; current physical road layout still requires dated official/corroborated evidence.

## Hard-case discovery follow-up

The first [real Greater Manchester eight-route smoke](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38781548543) was green: eight route pairs agreed with the established fastest-route cost, mapped rules were preserved, but **zero of eight simple road pairs produced distinct routes**. This is *coverage insufficiency*, not evidence that preferences are equivalent. Its bounded extract contained **zero mapped prohibited-turn pairs**, so it did NOT test difficult real turn restrictions or prove legality.

The new `benchmarks/public_route_preferences.py` walks bounded non-personal road-graph-connected public nodes and probes up to 96 longer origin/destination pairs for actual fastest-vs-shortest path diversity, while preserving the existing eight-route baseline. It reports distinct path counts and `INSUFFICIENT` if no useful contrast is found. It does not auto-select an unverified route, claim field legality or score consumer navigation apps. Any next heavy opt-in is one at a time.

### Targeted second opt-in

After the initial eight easy cases lacked path diversity, a revised scanner now explores up to 96 bounded, map-derived longer public-road route pairs and reports whether shortest and fastest actually differ. Run the official pinned Greater Manchester opt-in once. A green GitHub Actions job only establishes that the study executed; its `route_preference_discriminating_coverage` field determines whether it supplies useful diversity evidence, and the study remains NOT a legal truth oracle.
