# GPS and map matching — research prototype

`gps/fix_quality.py` now screens fix validity, age, coordinate jumps, uncertainty, and reported speed spikes. `gps/matcher.py` is the first **self-contained, directed-edge road-matching prototype**, using only imported public OSM road segments and simulated GPS observations.

It distinguishes **MATCHED**, **AMBIGUOUS**, **UNKNOWN** and **REJECTED**; checks traveling heading on directed links, excludes prohibited/unknown-access roads, and tests stationary parallel carriageways and weak fixes. Its per-edge geometry is a straight segment between two OSM nodes, not a lane geometry or measured car trajectory. Thresholds are preliminary and not statutory. Prior-edge continuity never overrides an opposing heading or uncertain fix.

First test tiers: standalone unit contract tests, synthetic fixture harness and an opt-in [public UK road geometry GPS smoke](../benchmarks/public_gps_matching.py). The latter injects controlled 3 m errors, missing heading, poor accuracy, speed spikes and stale readings over **real map geometry**. The same map is used to define its test truth, so it **does not** prove actual GNSS accuracy, sensor fusion, verified lane/carriageway assignment in the real world, tunnels, OSM ground truth, or end-to-end rerouting/arrival. No phone data or private routes should be added to the public repository.
