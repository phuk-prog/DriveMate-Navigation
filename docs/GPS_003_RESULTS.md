# GPS-003: real-map accuracy, faults and recovery

## Frozen before matcher execution

Real pinned Geofabrik Manchester260901 road data, OSM contributors/ODbL. Archive
SHA256 b7188b22501b878fddba6e06a90bb44ce6c2d721333e0ca57e10a1a82b568807;
XML SHA256 b3a883ae9b7c85072d24afeee7a1079aea00c22264516a0e1e71d49221ad27d5.
Bbox remains -2.270000,53.350000,-2.260000,53.360000, complete ways. No personal
traces or invented road layouts. Only observations/receipt clocks are simulated.

Select the first three eligible raw XML segments by numeric way/segment before
importer/matcher execution. Eligible residential/unclassified/tertiary segments
are20..250m long, with ordinary public access/no conditional tags, and supported
direction. Multiple segments may belong to one street; report that honestly.
Do not choose segments by whether DMN matches them. Fewer than three stops setup.
The full case/signal manifest is written before import/matching, hash-bound and
recomputed unchanged before execution. No failed case may be discarded.

Each base segment gets eight independent streams, three observations each:

| Stream | Middle observation | Required behaviour |
|---|---|---|
|Clear|3m reported accuracy,10m/s, geometric heading|All three generating directed segment matches required|
|Noisy|2m east offset,5m accuracy|Correct segment or withholding; final clear match required|
|Weak|60m reported accuracy|No road claim; final clear match required|
|Stale|Timestamp2000, receipt13001ms|Reject, preserve accepted history; recovery at15000ms|
|Future|Timestamp9000, receipt3000ms|Reject, preserve accepted history; recovery at5000ms|
|Duplicate|Timestamp1000 after accepted1000ms|Reject, preserve accepted history; recovery at5000ms|
|Impossible speed|100m/s reported speed|Reject, preserve accepted history; recovery at5000ms|
|Gap|31s without any intermediate update|Clear reacquisition at32000ms and following34000ms required|

Normal times1000/3000/5000ms, locations30/40/50percent along each directed segment.
Initial clear match is required in every stream. Twenty-four streams,72updates,
three base segments: not24independent roads. Withholding required clear output
is availability FAIL; a claim on a different segment is separately recorded as
source-map label disagreement. No all-withheld implementation can pass.

Oracle split: fault/history checks are synthetic analytical engineering contracts;
generating-edge labels are source-map agreement, NOT independently surveyed road
truth, legal traffic direction, physical RF performance or phone accuracy.
The31s gap verifies reacquisition after no calls, not active-guidance suppression
during silence. Accelerated clocks are not a wall-clock soak. No integrated app,
arrival/instruction, emulator or Android lifecycle proof is claimed.

DMN runs alone. External batch matching/snapping/routing interfaces are not an
equivalent receipt-clock/history lifecycle contract; no external execution or
comparative rank/score is claimed. Per-family reasons remain in the capability
and prior GPS-002 interface audit. Native lifecycle alternatives remain work.
Exact versions, map/oracle/source hashes, per-event results/reasons and raw
perf_counter_ns measurements are retained. Single-update times are milliseconds
when displayed, not stable cross-engine speed rankings.

## Pre-execution verification

Three analytical scoring controls reject wrong-road claims, unavailable required
clear output and rejected-fix history poisoning. Canonical unified preflight script
is absent (UNAVAILABLE). Full local suite/compile/privacy/whitespace must pass
before upload. Real-map execution pending CI; no score or pass is presumed.
Preserve UK17/0/23 and all seven unresolved earlier cases unchanged.
