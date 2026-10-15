# GPS and map matching — research prototype

`gps/fix_quality.py` now screens fix validity, age, coordinate jumps, uncertainty, and reported speed spikes. `gps/matcher.py` is the first **self-contained, directed-edge road-matching prototype**, using only imported public OSM road segments and simulated GPS observations.

It distinguishes **MATCHED**, **AMBIGUOUS**, **UNKNOWN** and **REJECTED**; checks traveling heading on directed links, excludes prohibited/unknown-access roads, and tests stationary parallel carriageways and weak fixes. Its per-edge geometry is a straight segment between two OSM nodes, not a lane geometry or measured car trajectory. Thresholds are preliminary and not statutory. Prior-edge continuity never overrides an opposing heading or uncertain fix.

First test tiers: standalone unit contract tests, synthetic fixture harness and an opt-in [public UK road geometry GPS smoke](../benchmarks/public_gps_matching.py). The latter injects controlled 3 m errors, missing heading, poor accuracy, speed spikes and stale readings over **real map geometry**. The same map is used to define its test truth, so it **does not** prove actual GNSS accuracy, sensor fusion, verified lane/carriageway assignment in the real world, tunnels, OSM ground truth, or end-to-end rerouting/arrival. No phone data or private routes should be added to the public repository.

## Multi-fix temporal prototype

`gps/temporal_matcher.py` is a conservative **separate replaceable navigation module**. It stores only the last valid fix, a fresh anchored directed road and limited unresolved count; no personal GPS data is written. Only one graph-legal, geometrically and heading-plausible next road can turn an ambiguous single-fix into a confident candidate. Multiple candidate legal roads, disconnected jumps, expired anchors, weak position or stopped/headingless observations remain unconfident. There is **no live GNSS, IMU fusion, dead reckoning or Android journey engine** in this prototype. Test with `python -m unittest tests.test_temporal_matcher tests.test_public_temporal_gps` plus whole CI.
