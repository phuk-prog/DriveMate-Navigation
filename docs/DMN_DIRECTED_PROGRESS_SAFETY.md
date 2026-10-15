# DMN directed-progress safety — 15 October 2026

Continues the [junction-transition safety fix](DMN_TEMPORAL_TRANSITION_SAFETY.md)
from local commit `f6cdb6f`. The remote research branch was rechecked through the
GitHub connector and remained at `fac36b04daf5008a01b73c45c1ea97f6f72fe09d`.
Shell Git still could not reach its configured proxy. No remote write occurred.

## Reproduced fault and root cause

The matcher treated staying on the same directed edge as automatically
consistent with history. On a fabricated straight road, it confidently accepted
a 40 m backward displacement over four seconds with a forward bearing. That
displacement passed the existing unsigned speed checks. The same gap occurred
with missing speed and across six additional road orientations.

The initial seven test methods produced nine assertion failures, including
six orientation subtests. Existing forward and jitter controls passed.
This was a direction-consistency fault, not evidence of an independently
established illegal manoeuvre or of which physical road a real driver occupied.

## Implemented change

For a same-edge candidate, project displacement from the trusted anchor onto
the edge's directed straight segment, using one fixed local coordinate frame.
If progress is negative by more than the sum of both horizontal accuracy radii,
withhold the assignment as `AMBIGUOUS`, reason `backward_directed_progress`.
Keep the trusted anchor so a subsequent consistent fix can recover.

Small backward jitter within the reported error budget and purely lateral
jitter retain their previous behaviour. Missing speed and a stationary speed
report cannot waive the positional contradiction. An intermediate weak fix
cannot replace the trusted progress anchor. This extends the existing bounded
matcher; no graph search, new dependency or sensor model was needed.

## Executed local evidence

An unchanged copy of the previous implementation was loaded from `f6cdb6f`
and run alongside the new implementation on identical synthetic observations.
The dedicated cohort contains the original eastbound case, a missing-speed
case and six other compass directions:

| Contradictory directed histories | Planned | Confidently accepted | Withheld |
| --- | ---: | ---: | ---: |
| Before | 8 | 8 | 0 |
| After | 8 | 0 | 8 |

Withholding is a safety outcome, **not a correct positive road identification**.
The eleven new test methods also cover forward recovery, lateral jitter,
combined uncertainty, just-inside/outside error budgets, stationary reports
and a weak intervening observation. All existing folded-junction cases remain
in the full regression suite.

Executed successfully:

```sh
python -m unittest discover -s tests -p test_temporal_directed_progress.py -v
python -m unittest discover -s tests -q
python -m compileall -q engine map_data gps benchmarks tools tests
git diff --check
python -m tools.privacy_guard
```

Full Python suite: **337 passed, zero failed**. Privacy scan and manual review
found no new personal data, credentials, third-party code or map downloads.
Rollback is the three-file change relative to `f6cdb6f`.

## Limits and next validation

All new observations and roads are synthetic. New real UK replay, external-engine
comparisons, Android/device tests and independent legal checks are **not tested**.
No navigation rank, road-readiness claim or production promotion follows.

The check uses the matcher's existing straight-segment approximation and reported
accuracy, not calibrated GNSS error bounds. Curved polylines, longitude wrap,
multi-edge loops, cumulative small jitter and histories beyond anchor expiry
remain unresolved. A driver could actually reverse or complete an unobserved
loop: withholding contradictory history does not establish illegal driving.
Stateless reacquisition after history expires retains its existing limits.

Next, run the pinned real UK temporal replay and common final-fix geometry
cohort with the accumulated safety changes, retaining all withheld and unsupported
outcomes. Production `phuk-prog/DriveMate` is unchanged; no APK or release was made.
