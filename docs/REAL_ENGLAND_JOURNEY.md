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


## First Wigan integration replay: faults and fixture repair

The initial fresh run 38655911826 executed eight native-powered simulated
journeys on the pinned OSM Wigan extract. It returned zero full passes:
five failed and three unresolved. Two of those reached the destination
but also observed directed-road mismatches; three failed to confirm arrival;
three were interrupted by a >20 m gap **in the generated test samples**.
Those three interruptions are benchmark setup errors, not GPS failures.

The generator now inserts continuous route samples at **no more than 6 m**
along each real segment, even when an OSM way segment is long. It records
a matched alternate directed road near the approached junction as
`unverified`, not a proved matcher defect or a pass. A convincing mismatch
at least 8 m away from either segment endpoint remains a mismatch failure.
Both outcomes remain counted; there is no algorithm permission change or
silent exclusion of offending routes.

Run the same eight cases again and use the emitted per-case evidence to
identify actual native/GPS/guidance failures before implementing any fix.


## Focus the follow-up: actual journey faults rather than speed setup

The revised run (38656252832) recorded seven non-arrivals and one arrival
with junction ambiguity, with **zero mismatches far from road junctions**.
These outcomes demand investigation; they are not proof that real road
navigation works, and do not justify disabling lane/turn safety checks.

New diagnostic fields disclose only the candidate's **final relative
segment fraction, match/recovery status, final-road flag, and instruction
state**. They do not store raw GPS fixes or latitude/longitude.

To conserve CI time, subsequent journey changes run under the isolated
`real-england-journey.yml` workflow, which builds the same compiled
C++ router and verifies the same dated real-road map, but no longer starts
all external benchmark services. The existing real-road **speed**
workflow is now manual-only. The journey workflow deliberately goes
red when genuine journey cases fail or are unresolved, while its
artifacts upload on failure for root-cause analysis.


## Verified root cause and guarded correction

The focused run 38656569621 exposed a genuine state-machine defect:
on the final road, a fix at the exact destination fraction triggered the
correct `destination_uncertain` quality guard. But the controller wrongly
treated that guard as a GPS loss, discarded the active tracking session,
and on later good fixes attempted recovery *past* the destination.
On a one-way road this could yield `no_route` or never-arriving output.

The correction **does not declare an uncertain fix as arrival**. It
withholds guidance for the uncertain frame while preserving the last
trusted matched fix and the existing native-routed journey. A subsequent
fresh directional fix beyond the target can now confirm arrival through
the original session's route and legality checks. An actual GPS timeout
still enters normal loss/recovery. Regression tests separately check
rejected premature arrival, trusted-state preservation, confirmed
forward crossing and timeout behavior. Only the actual next CI journey
replay can confirm whether remaining Wigan failures are resolved.
