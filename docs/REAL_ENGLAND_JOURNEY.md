# Wigan real-geometry DriveMate end-to-end journey research

The primary project milestone is completing **DriveMate Navigation**, not
optimising a detached routing speed demo. This phase hooks together the original
compiled C++ routing core and the existing GPS/recovery/roundabout/instruction
journey components on dated **real Greater Manchester OSM road geometry**.

Run in the same `real-england-speed.yml` workflow *after* the dated,
checksum-verified Wigan map has passed importer preflight:

```sh
python -m benchmarks.real_english_journey --input results/real/roads.osm \
  --snapshot 2026-10-13 --cases 8
```

This is **simulated GPS along actual OSM roads**. The map is real; no observed
phone GPS is present and no sound is played. This is deliberately labelled
separately from a physical drive. Routes are chosen deterministically from the
same first eight public-map cases as the speed cohort; zero personal locations
or input sample coordinates are written to artifacts.

The native C++ binary handles routing through the existing
`navigation_core.journey` contract. The `RecoveringGpsJourney` uses the
existing research matcher and history-safe recovery, while
`InstructionScheduler` produces (but does not speak) events. Each case
records acquisition, recognized matching, contradictory matches, route
guidance availability, instruction event counts and arrived/uncertain/failed
outcome. Categories not genuinely exercised are **not_exercised**, not pass.

The CI step records results even if some cases fail or cannot be confirmed,
without converting setup limitations into navigation defects or suppressing
earlier verified speed/regression evidence. Failures must be analysed,
reproduced and corrected with fresh replays.

The following remain **unproven**: live GPS accuracy, independent legal turn
truth for real roads, physical lane placement, complex roundabout exit signs,
spoken instruction quality/timing, full offline map updates, regional map scale
and Android on-device performance. This initial journey cohort measures
native-plus-research integration only.
