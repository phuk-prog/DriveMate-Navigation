# DMN temporal road-transition safety — 15 October 2026

## Verified baseline and failure

Continued the existing research from `planning/dmn-engine-first-comparison-20261015`
at `fac36b04daf5008a01b73c45c1ea97f6f72fe09d`, rather than the older main-branch
prototype. Shell Git networking failed because its configured proxy was
unreachable. The connected GitHub reader supplied the source files; each changed
blob was verified against its Git object hash. The restored complete source tree
matches remote tree `74cf6bf95bfd6d46ad02cd8d2bcb622dd319170f` exactly.
The local snapshot commit is `402588e`; no remote history was rewritten.
All 320 baseline Python tests passed locally.

The directed temporal matcher checked physical displacement between GPS fixes
and whether successive edges shared a legal mapped junction. It did not check
how far the vehicle would need to travel **via that junction**. Two nearby roads
can connect only at a distant hairpin. The new fabricated reproducer has fixes
approximately 18 m apart but a required road transition of approximately
1.8 km in two seconds. The baseline confidently selected the return road.
The first focused run failed 2/3 tests, including recovery after that false match.

## Implemented change

`gps/temporal_matcher.py` now screens each connected successor against the sum
of great-circle distances from the trusted anchor to the shared junction and
from that junction to the new fix. This sum is a lower bound on travel through
that junction even if the roads curve. Both reported position uncertainty radii
reduce the bound. The elapsed time and reported speed come from the trusted
anchor and current fix; unresolved intermediate readings cannot refresh them.

The existing generous reported-speed tolerance is retained (three times the
larger reported speed, with a 20 m/s floor), capped at the fix-quality screen's
90 m/s generic physical limit. When either speed is missing, the generic limit
still applies. These are experimental plausibility parameters, not speed limits.
An impossible transition is withheld as `AMBIGUOUS` with reason
`implausible_road_transition`; it does not replace the trusted anchor.

Extending the existing one-junction screen was sufficient to reproduce and
correct this fault. A graph search or external matcher dependency would add
complexity without being necessary for this bounded case. No source dependency,
map format, native binary or Android production code changed.

## Executed local results

The unchanged baseline implementation was loaded separately from the local
snapshot and exercised on the same observations as the modified implementation.
Only aggregate outcomes were printed.

| Synthetic impossible-transition cohort | Planned | Confident wrong | Withheld |
| --- | ---: | ---: | ---: |
| Before | 11 | 11 | 0 |
| After | 11 | 0 | 11 |

This cohort consists of the original reproducer, a missing-speed case, and nine
additional combinations of fold sizes and speeds. Withholding an impossible
assignment is the intended safety result; it is **not** a correct positive road
identification. Separate controls retain a plausible short transition, recovery
on the original road, and a plausible transition after a weak intermediate fix.

Commands run successfully:

```sh
python -m unittest discover -s tests -p 'test_temporal*.py' -v
python -m unittest discover -s tests -q
python -m compileall -q engine map_data gps benchmarks tools tests
git diff --check
python -m tools.privacy_guard
```

Final complete suite: **326/326 passed**, zero failed. Six new test methods include
the nine additional size/speed combinations. The existing routing, GPS, reference
adapter, benchmark-contract and importer tests are included in that suite.
The privacy guard and manual change review found no personal traces, credentials
or new external data. Rollback is the local baseline snapshot plus removal of
this three-file change.

## Unresolved and not tested

This is synthetic host research. **No new external engines, real UK road replays,
phone sensors or Android sessions were executed.** Existing external-engine
results remain historical and are not new comparative evidence for this fix.
No public-road extracts were available locally, and shell network access was
unavailable. Real UK same-observation replay and fresh external comparison
therefore remain **not tested** for this change; no navigation rank is assigned.

The screen covers the matcher's existing same-edge/one-successor model. It does
not solve multi-edge histories, backward movement on one directed edge, GNSS
error calibration, missing junction topology, lane identity, or independent UK
legal truth. Once history expires, stateless reacquisition retains its existing
limitations. Repeat the pinned public-road temporal cohort before promoting
this candidate beyond local research. Production `phuk-prog/DriveMate` is
unchanged; no APK or release was produced.
