# DriveMate Navigation

**Status: independent research prototype — not an Android navigation app or approved production routing engine.**

This project is an independently developed navigation architecture and validation laboratory. It is deliberately separate from `phuk-prog/DriveMate`: nothing here updates the existing Android application or generates an APK.

## Goal

Create the best practical **offline-first, Android-efficient, adaptable** navigation system by evaluating and (where compatible) legally reusing existing open-source components, developing superior components where tests support it, and comparing the results with independent reference engines.

**Do not mistake agreement between routing providers for proof of legal road access.** Route legality, lanes and roundabout exits require evidence from authoritative road data or independently verified observations. Changes to legal access must not be learned from GPS traces alone.

## What works now

- A small **original, deterministic Python routing core** with directed edges, explicit road-access states, forbidden turns, an incoming-edge-aware rerouting entry point and deterministic shortest-time searches.
- A **synthetic road-network fixture**, automated routing regression tests and a lightweight benchmark reporter.
- A reference-engine registry identifying engines to evaluate; **no reference adapters or competitor performance results exist yet**.
- A low-cost GitHub Actions workflow that runs source checks, unit tests and a synthetic benchmark. **No APK, device tests, maps, services or paid APIs**.

**Not implemented yet:** actual OpenStreetMap import, mobile-native execution, map matching, UI, directions, voice, lane guidance, traffic, incremental regional map updates, adaptive model deployment, or live navigation.

## Run locally

Requires Python 3.11+ with no third-party packages.

~~~sh
python -m unittest discover -s tests -v
python -m benchmarks.run --repeat 30
~~~

The benchmark prints experimental latency figures for a tiny **fabricated** network. Those are not evidence of real-world navigation speed, route safety or accuracy.

## Project layout

- `engine/`: original, licence-independent routing prototype.
- `map-data/`: planned road imports, versioned graph preparation, regional maps.
- `gps/`: planned positioning and map matching.
- `guidance/`: planned UK turn, roundabout and lane instruction verification.
- `learning/`: planned privacy-respecting learning and evidence gates.
- `benchmarks/`: reproducible fixtures, reference-engine registry and measurements.
- `references/`: references, integration and licence decisions (no copied vendor code).
- `tests/`: correctness and regression tests.
- `android/`: future native on-device proof-of-concept.
- `docs/`: architecture, safety, privacy, licences and milestones.

Read [architecture](docs/ARCHITECTURE.md), [validation](docs/VALIDATION.md), [licensing and privacy](docs/LICENSING_AND_PRIVACY.md), and [roadmap](docs/ROADMAP.md) before adding components.

## Rules for this public repository

Never commit real driving traces, home/work positions, vehicle identifiers, secrets, proprietary maps, API responses without redistribution rights or copyrighted third-party source unless its licence and provenance have been reviewed. Use anonymised and synthetic fixtures for public tests.

Public repository visibility **does not** mean this code has an open-source licence. There is currently **no project-wide code licence**: licensing must be decided explicitly before third-party code is imported or this project is distributed to others.

No automatic dependency downloads or builds of other engines. Compare them only with permitted data and APIs; use the same map snapshot when possible and disclose when not.

This repository does not replace the established `DriveMate` app until an explicit integration decision and complete on-device/regression validation.
