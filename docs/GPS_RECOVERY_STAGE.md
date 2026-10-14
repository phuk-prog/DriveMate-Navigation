# Bounded GPS loss and recovery

Original local navigation research. No GitHub push, workflow, Android change or
APK was made. Earlier routing/junction reference observations remain historical;
there is no new external GPS matcher, device or real-road comparison in this stage.

## Implemented behaviour

`gps.recovery.RecoveringGpsJourney` provides acquisition, tracking, loss,
confirmation and recovery around the existing directed GPS matcher and trusted
journey engine. It shares the prepared spatial index; it does not redraw maps or
log personal fixes. Use `observe(fix, receipt_epoch)`, `poll(receipt_epoch)` during
silence, and clocked `junctions(now)` / `roundabouts(now)` lookups.

- Startup and recovery need at least three consistent fresh fixes spanning at
  least two seconds, each no more than three seconds apart and no worse than
  15 m reported accuracy. Confirmation may cross contiguous short road segments.
- Three seconds without fresh accepted positioning suppresses guidance. Rejected
  fixes retain the last trusted snapshot and do not advance routing or arrival.
- Recovery checks directed physical reachability from the last trusted position
  under a bounded motion allowance. Backwards one-way teleportation and recovery
  to disconnected parallel/crossing roads fail this check.
- Unobserved paths are retained as possible inbound suffixes, not declared actual
  travel. Future routes must agree across all retained variants. Disagreement
  produces a fresh `history_uncertain` location with no published route/advice.
- Known one-way/access/turn restrictions remain enforced for future routing.
  Unknown access remains permitted and flagged; missing lane data never closes
  roads. Historical physical path enumeration intentionally includes possible
  past banned turns: assuming an unseen trip was legal could incorrectly discard
  the very history that triggers a future via-road ban. Inclusion is not permission
  to make that turn and is not a claim that it happened.
- All pending confirmation fixes are untrusted for guidance. When actual observed
  road suffixes become equivalent, variants merge only if their roundabout ledgers
  also agree. Matching recent road histories alone cannot erase earlier disputed
  exit counts. Advice is withheld when those ledgers differ.
- Recovery inside a roundabout discards unknown historical entry/exit numbering;
  it does not fabricate the original entry. Future fully observed entries can
  establish new context. Guidance clears after exit; observed arrival still works.
- Route/backend failures leave every trusted matching/session variant intact.
  Pending fixes and silence trigger no route searches; confirmed recovery uses
  at most one bounded route calculation per retained variant.

## Bounds and limitations

The existing local geometry, age, heading, accuracy and motion thresholds remain
prototype policy choices, not calibrated real-device safety guarantees. Gaps over
300 seconds, more than 16 possible variants, or exhausted search resources leave
recovery explicitly incomplete. The search bounds expanded states, retained states
and queued states to 4,096 by default; it never accepts a partial history set after
exhaustion. Variant count includes distinct roundabout ledgers.

Reachability uses an upper travel-distance bound and deliberately over-approximates
possible histories. It does not prove the actual path or legality of an unseen
trip. A common shortest route must agree across variants; finding a different
common alternate route is not implemented. Some physically recoverable situations
therefore withhold guidance conservatively. Three mutually consistent but biased
fixes are not a guarantee of the correct road. Elevation/bridge identification,
sensor fusion and realistic sensor-error calibration remain pending.

Passing the destination while GPS is lost does not fabricate arrival. Destination
uncertainty and exact endpoint confirmation limits from the GPS matching stage
remain. Indeterminate stationary direction on bidirectional geometry remains
withheld until sufficient fresh directional evidence is available.

## Verification

| Evidence | Result |
| --- | --- |
| Full regression suite | 334 test methods passed |
| New recovery test methods | 49 passed |
| Hard synthetic recovery sweep | 1,536 cases; zero failures |
| Deliberately recoverable sweep cases | 768 resumed with a common valid plan |
| Deliberately unsafe/indeterminate sweep cases | 768 correctly withheld |
| Sweep observations | 13,056 authored synthetic fix observations |
| Independent exhaustive history oracle | 216 cases; zero differences |
| GPS-loss roundabout replay | Entry number withheld after uncertain recovery; observed exit/arrival passed |
| Prior GPS projection sweep | 4,800 cases passed again in full regression |
| Prior complete GPS roundabout journeys | Four passed again in full regression |
| Source compilation | Passed |

The independent history oracle enumerates complete directed paths, including
cycles, for authored fixture fractions and distance budgets. It is separate from
the implementation's state-based shortest-distance search. The hard sweep varies
latitude, road angle, gap length, bad-fix pattern, repeated failures and target
road class. Fault names (tunnel, urban bounce, tree cover) describe synthetic
injection patterns, not real places or validated physical sensor models.

Targeted tests also cover indoors startup, stopped traffic lights, alternating
parallel fixes, wrong-way observations, restricted future turns, multi-road
history disagreement, timed bans, compiled-window expiry, burst timestamps,
resource exhaustion, startup across short segments, backend failure in a later
variant, stale snapshots and uncertain destination arrival.

Current evidence: `results/recovery_full_suite.log`,
`results/gps_recovery_expanded.json`, `results/recovery_test_register.csv`,
`results/recovery_source_manifest.json`, `results/recovery_source_privacy.json`.
Test-method counts and parameterized cases are distinct counts. Expanded evidence
was exported from the full-suite run, without repeating the identical sweep.

## Reproduce

```sh
python3 -m unittest discover -s tests -p test_gps_recovery.py -v
python3 -m unittest discover -s tests -v
python3 -m benchmarks.gps_recovery_validation
```

Next: instruction generation/timing integrated with GPS freshness, uncertainty,
rerouting, roundabouts and close successive junctions, followed by broader whole
drive checks. Real locations, device/road tests and actual competitor matching
comparisons remain separate work; no winner or readiness claim is invented.
