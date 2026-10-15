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
