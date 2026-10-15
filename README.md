# DMN — DriveMate Navigation

> **15 October 2026: engine-first programme under owner review.** The current proposal is [DMN engine-first programme](docs/DMN_ENGINE_FIRST_PROGRAMME.md), with the [ten-reference test protocol](docs/DMN_TEN_REFERENCE_PROTOCOL.md), [22 decision questions](docs/DMN_DECISION_QUESTIONS.md), and a [machine-readable not-run coverage inventory](config/dmn-engine-first-programme.json). The long README sections below document the **original initial prototype**, not the latest research results or settled new test thresholds. In particular, old claims that *no external engines or real UK road tests have ever run* have been superseded by later isolated-branch benchmarks; see the linked programme and original CI evidence. Do not use those historical statements as the active plan. No standalone app is being created.


**This repository is the DMN navigation research and comparison programme for the existing DriveMate Android phone app; it is not a standalone DMN app project.**

We compare our independent candidate routing/GPS/guidance implementations against other real engines, diagnose errors, rerun tests and select the best technically and legally suitable approach for the existing app. Android integration is a later approval-based stage, not implied by a host benchmark.

See [DMN working agreement](docs/DMN_SCOPE.md). The current development and measured evidence is on the isolated research branches, not yet consolidated into this default branch.

---

# DriveMate Navigation

**Status: independent research prototype — not an Android navigation app or approved production routing engine.**

This project is an independently developed navigation architecture and validation laboratory. It is separate from any existing Android application: nothing here updates another app or generates an APK.

## Goal

Create the best practical **offline-first, Android-efficient, adaptable** navigation system by evaluating and (where compatible) legally reusing existing open-source components, developing superior components where tests support it, and comparing the results with independent reference engines.

**Do not mistake agreement between routing providers for proof of legal road access.** Route legality, lanes and roundabout exits require evidence from authoritative road data or independently verified observations. Changes to legal access must not be learned from GPS traces alone.

## What works now

- A small **original, deterministic Python routing core** with directed edges, explicit road-access states, forbidden turns, an incoming-edge-aware rerouting entry point and deterministic shortest-time searches.
- A **synthetic road-network fixture**, automated routing regression tests and a lightweight benchmark reporter.
- An independent **turn-aware A*** candidate that uses geographic heuristics only with validated geometry and falls back safely otherwise. It is compared against the deterministic Dijkstra baseline on fabricated networks.
- An opt-in **public OSM PBF-to-XML subset preparation tool** that runs locally using Osmium, strips contributor metadata and only writes to ignored `results/`; large map files are never committed or downloaded by GitHub CI.
- A **bounded OpenStreetMap XML importer** for small extracts, with provenance checksum, one-way travel, restricted turns and conservative uncertain access handling; unsupported conditional rules or via-way relations cause import to fail. This importer is **not yet suitable for real-world navigation**.
- A benchmark comparison contract that **refuses to rank runs** from nonmatching map/profile/device/scenario configurations.
- Local, offline output adapters for OSRM, Valhalla and GraphHopper that retain **only aggregate time and distance**; these do not run external engines or imply any real provider benchmark has taken place.
- A repository-wide **privacy preflight**, executed automatically in CI, that rejects suspicious files and likely credential/location-data exposures. Manual review is still mandatory.
- A reference-engine registry identifying engines to evaluate; **no actual competing engines have been executed or measured yet**.
- A low-cost GitHub Actions workflow that runs source checks, unit tests and a synthetic benchmark. **No APK, device tests, maps, services or paid APIs**.

**Not implemented yet:** any independently validated real-road routing result, large/production OpenStreetMap PBF ingestion, mobile-native execution, map matching, UI, directions, voice, lane guidance, traffic, incremental regional map updates, adaptive model deployment, or live navigation.

## Run locally

Requires Python 3.11+ with no third-party packages.

~~~sh
python -m unittest discover -s tests -v
python -m benchmarks.run --repeat 30
python -m benchmarks.search_comparison --size 14 --repeat 8
python -m map_data --input benchmarks/fixtures/synthetic-osm-junction.xml --region synthetic --snapshot fabricated-v1
~~~

The benchmarks print experimental latency figures for **fabricated** networks. Those are not evidence of real-world navigation speed, route safety or accuracy.

## Project layout

- `engine/`: original, licence-independent routing prototype.
- `map-data/`: road-data policy and format documentation.
- `map_data/`: bounded OSM XML importer prototype (6 MB maximum; not a UK regional import).
- `tools/public_osm_extract.py`: manual, local preparation of very small, contributor-anonymised public-road samples (needs Osmium Tool and a public PBF obtained separately).
- `gps/`: planned positioning and map matching.
- `guidance/`: planned UK turn, roundabout and lane instruction verification.
- `learning/`: planned privacy-respecting learning and evidence gates.
- `benchmarks/`: reproducible fixtures, reference-engine registry and measurements.
- `references/`: references, integration and licence decisions (no copied vendor code).
- `tests/`: correctness and regression tests.
- `android/`: future native on-device proof-of-concept.
- `docs/`: architecture, safety, privacy, licences and milestones.

Read [public-data policy](docs/PUBLIC_DATA_POLICY.md), [architecture](docs/ARCHITECTURE.md), [validation](docs/VALIDATION.md), [licensing and privacy](docs/LICENSING_AND_PRIVACY.md), and [roadmap](docs/ROADMAP.md) before adding components.

## Rules for this public repository

Never commit any personal data, actual driving traces, home/work positions, vehicle identifiers, secrets, private application details or proprietary maps. Use synthetic fixtures and publicly licensed non-personal road data only. Passing automated privacy scans does not replace human review.

Public repository visibility **does not** mean this code has an open-source licence. There is currently **no project-wide code licence**: licensing must be decided explicitly before third-party code is imported or this project is distributed to others.

No automatic dependency downloads or builds of other engines. Compare them only with permitted data and APIs; use the same map snapshot when possible and disclose when not.

This research repository does not modify any existing Android app; integration would require a separate decision and complete on-device/regression validation.
