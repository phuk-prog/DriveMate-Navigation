GitHub-hosted comparison setup is documented in [GITHUB_CATEGORY_COMPARISON.md](docs/GITHUB_CATEGORY_COMPARISON.md).

# DriveMate Navigation

**Status: reconciled independent research prototype — not an Android navigation app or approved production routing engine.**

This project is an independently developed navigation architecture and validation laboratory. It is separate from any existing Android application: nothing here updates another app or generates an APK.

## Goal

Create the best practical **offline-first, Android-efficient, adaptable** navigation system by evaluating and (where compatible) legally reusing existing open-source components, developing superior components where tests support it, and comparing the results with independent reference engines.

**Do not mistake agreement between routing providers for proof of legal road access.** Route legality, lanes and roundabout exits require evidence from authoritative road data or independently verified observations. Changes to legal access must not be learned from GPS traces alone.

## What works now

- Original directed routing with no/only/via-road legality, partial-road positions, bounded weekly/time-aware routing and explicit unknown-access flags.
- Static lane evidence, junction directions and bounded roundabout exit context.
- Bounded geographic GPS matching, signal-loss recovery with possible-history consensus, and clocked instruction events.
- Whole-drive synthetic replays, original independent path oracles, and a category-scoring contract that keeps untested categories unscored.
- Actual isolated GraphHopper same-map routing and clean batch-path comparisons. These are limited results, not a general navigation ranking.
- GitHub-hosted pinned OSRM, Valhalla and GraphHopper benchmark setup on an isolated research branch. Results and runtime failures are retained as artifacts.
- Public source privacy checks. Only independently authored synthetic fixtures are used by the new benchmark.

**Still pending:** calibrated sensors, realistic named-place/device/road validation, production-size maps, Android/audio/Bluetooth integration, complex lane/junction coverage, traffic/updates/learning, and comparable results across all ten external systems. No APK is built or released here.

## Reconciled navigation core

The navigation-only reconciliation connects this repository’s bounded importer to the original multi-road routing and trusted-road journey components in `navigation_core/`. See [reconciliation details](docs/RECONCILIATION.md). Build the portable host core once before running the complete suite:

~~~sh
bash navigation_core/native/build.sh
~~~

This remains a host research prototype. Raw GPS matching, junction guidance and Android navigation are still pending.

Whole-drive simulations and the ten-reference execution matrix are documented in [WHOLE_DRIVE_TEN_SYSTEMS.md](docs/WHOLE_DRIVE_TEN_SYSTEMS.md).

Instruction generation/timing and adversarial event tests are documented in [INSTRUCTION_TIMING_STAGE.md](docs/INSTRUCTION_TIMING_STAGE.md).

Bounded GPS loss/recovery and harder synthetic tests are documented in [GPS_RECOVERY_STAGE.md](docs/GPS_RECOVERY_STAGE.md).

Bounded GPS matching and integrated synthetic journeys are documented in [GPS_MATCHING_STAGE.md](docs/GPS_MATCHING_STAGE.md).

Static lane evidence and junction guidance are documented in [LANE_JUNCTION_STAGE.md](docs/LANE_JUNCTION_STAGE.md).

Live roundabout context and the unknown-data routing policy are documented in [LIVE_ROUNDABOUT_STAGE.md](docs/LIVE_ROUNDABOUT_STAGE.md).

Roundabout exit identification is documented in [ROUNDABOUT_STAGE.md](docs/ROUNDABOUT_STAGE.md).

Clock-aware trusted-road journey rerouting is documented in [TIMED_JOURNEY_STAGE.md](docs/TIMED_JOURNEY_STAGE.md).

The current local reconciliation and conditional-restriction evidence is in [CONDITIONAL_RESTRICTIONS.md](docs/CONDITIONAL_RESTRICTIONS.md). This workspace is not uploaded to GitHub.

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
- `gps/`: bounded GPS quality checks, directed segment matching and trusted-journey integration.
- `guidance/`: bounded UK instruction formatting, timing, freshness and delivery events.
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

Reference downloads/builds are limited to explicitly authorised benchmark jobs with recorded versions and checksums. Compare only with permitted data and APIs, using the same map snapshot where possible and declaring differences. Reference source/binaries are not included in the candidate.

This research repository does not modify any existing Android app; integration would require a separate decision and complete on-device/regression validation.
