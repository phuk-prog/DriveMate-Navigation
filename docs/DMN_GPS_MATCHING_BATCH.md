# DMN GPS road-matching — fourth research test batch

Goal: introduce the first **small independently replaceable** map-matching component, beyond the already-running GNSS fix-quality filter. The experiment uses deterministic, nonpersonal injected GPS errors on **pinned public UK OpenStreetMap geometry**, rather than synthetic roads or private GPS logs. The test ground truth is generated from the *same* OSM map and is not independently surveyed.

### Components and behavior

- Directed-road candidate selection respecting vehicle access; compares midpoint projection and movement bearing.
- Reports MATCHED, AMBIGUOUS, UNKNOWN or REJECTED; never silently claims exact location when two parallel roads remain plausible.
- Screens stale/duplicate readings, jump and speed spikes via the earlier `gps/fix_quality.py`.
- Measures clean geometry-derived replay and offsets as separate cohorts; adversarial weak/old/implausible fixes must not produce confident matches.
- Keeps configuration boundaries isolated so a better matcher, IMU or HMM/particle filter can replace it after evidence supports improvement.

### Planned real UK measurement

One opt-in `[gps-match-smoke]` run on a small dated Geofabrik Greater Manchester public extract. For at most 30 accessible directed edges, inject 3 controlled valid fixes each plus 3 bad-signal scenarios, and separately report **correct confident edge**, **wrong confident edge**, **ambiguous**, **unknown**, **bad fixes safely withheld** and denominators. Do not make up a navigation score out of ten based on self-generated geometry truth. Print counts, save a small aggregate artifact and keep raw roads/fixes out of GitHub.

### Unmeasured or pending

True GPS/IMU field error, genuine parallel/stacked road driving, Android sensor integration, evolving trajectory history, route-constrained matching, lane-level position, sign-legality evidence, real speed limits, arrival/turn instruction timing, offline entire drive and comparison against external navigation engines. Review new findings under [the adaptive testing loop](DMN_ADAPTIVE_TESTING.md). Production app and APK remain untouched.

## Initial safety regression detected by CI

The first unit run exposed a **stationary dual-carriageway overconfidence** error: a nominal fix on one mapped link was accepted even though its opposite parallel neighbor lay only around 7 m away. The initial branch CI run failed 1 of 159 unit cases and properly blocked the public-map stage. The matcher was corrected to treat multiple nearby plausible directed links as **AMBIGUOUS** without useful movement/heading. [Subsequent green CI run 38738827465](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38738827465) confirms the correction at unit level; the public UK road replay is a separate opt-in measurement and must be reported only after running.

## First real UK geometry-derived GPS results (15 October)

[GitHub Actions run 38738954488](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38738954488) succeeded: **159 Python unit/contract tests**, public source `geofabrik-260901` SHA-256 `b3a883ae9b7c85072d24afeee7a1079aea00c22264516a0e1e71d49221ad27d5`, 2,023 vertices and 1,202 directed edges. It examined **30 distinct mapped edges × 3 simulated good readings = 90/90 correctly assigned directed edges**, zero confident wrong matches, plus **90/90 weak, stale or spike readings withheld**. There were no ambiguous results among those first deliberately straightforward moving fix cases. **No true phone GPS measurement, independent position oracle, sensor fusion or external competitors**. The high pass fraction is not a real-field accuracy score.

The next committed extension adds explicit bidirectional road overlap, stopped/heading-less ambiguity, two closely parallel same-direction roads, and a clean fix after a rejected speed-spike, all with separate counts. It specifically avoids confident assertions when equally credible close directed roads share the same heading. The public UK rerun should establish the new denominators; previous clean results remain a separate benchmark.
