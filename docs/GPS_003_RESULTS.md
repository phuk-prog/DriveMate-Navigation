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

First CI38869088303 at9791160c1137d59f5b577ac653d2966d3299dea0 stopped before
any matcher update: tuple coordinates in the recomputed Python manifest compared
unequal to identical decoded JSON lists. Map/archive checks and preparation had
succeeded. Corrected comparison uses exact canonical serialized manifest bytes;
signals, selection and expectations are unchanged. Added tuple roundtrip and
manifest-tampering controls. Retained gps003-setup-failure-20261016.json; no
navigation failure or pass is assigned to that setup attempt.

## Executed baseline: failing availability, no forced confidence

Run38869427281 atc6202e406450d6f9fbb8e01c7679193d92522358 executed24streams and72
matcher updates on three raw-selected segments. All three belong to the same OSM
way32113418 (segments4,6,9), lengths24.297m,23.494m,34.127m. They are not three
independent roads. Manifest and actual inputs/outcomes are retained in
references/gps003-real-map-20261016.json with exact source/oracle/run hashes.

**8/24 streams pass;16 fail** because their first required clear output is withheld
as AMBIGUOUS with two candidates. This repeats the same first position eight times
on each of base segmentsB1/B2, not16independent initial-position failures. B3 passes
all eight streams. Aggregate72updates:39source-map-correct,0confidently wrong,
33withheld (including12rejected). All24final clear/recovery observations pass.

| Category | Passing streams /3 | Additional checked behaviour |
|---|---:|---|
|Clear|1/3|B1/B2 first fix ambiguous; subsequent fixes match|
|Noisy2m|1/3|No wrong claim; one noisy match and two safe withholds|
|Weak60m|1/3|All three weak observations withhold|
|Stale|1/3|All three stale packets reject and preserve history|
|Future|1/3|All three future packets reject and preserve history|
|Duplicate|1/3|All three duplicates reject and preserve history|
|Impossible speed100m/s|1/3|All three impossible-speed packets reject and preserve history|
|Gap31s|1/3|All six post-gap clear observations match|

Each1/3 stream result includes the initial availability check; passing the middle
fault condition does not erase that initial failure. No failed case was discarded.
No recovery, bad-fix handling or confident wrong-road fault was reproduced here.
The first-position ambiguity is an unresolved availability deficit. A generated
exact point and road identity do not prove a3m-accuracy measurement uniquely
identifies that segment; candidate geometry/independent evidence must be checked
before a safe improvement can be justified. No confidence threshold was loosened.
This is a recorded failing trial, not an app-readiness pass or competitor victory.

Only DMN's stream contract ran. Comparison rank and score remain null; external
batch/routing interfaces do not implement this same clock/history contract.
The owner is clarifying the permanent baseline/table/fix/retest cycle before a
new comparison is selected. Preserve this completed baseline and all earlier
UK17/0/23 evidence. No DMN policy change or navigation retest is claimed.

## Baseline review gate and observed timing

The owner selected stop after baseline for review and comparison using available
applicable engines now. This completed DMN-only stream trial has0external engines
and cannot fill that comparison request; it must not be relabelled a competitive
baseline. The next owner-authorized competitive baseline should use a genuinely
shared real-map position/direction contract across available matching engines,
with explicit exclusions for unsupported stream lifecycle operations. No new
comparison or DMN improvement is executed in this saved baseline.

Seventy-two measured matcher updates on this CI runner: median0.0744115ms,
nearest-rank p95(72samples)0.153038ms, maximum0.214390ms. These single-pass values
are diagnostic in-process timings, not device estimates or a cross-engine ranking.
Full per-update measurements are retained. Proposed next investigation, subject
to review: inspect competing candidate geometry at the two repeated initial
positions before judging whether output can safely be restored. No fix is verified.


## Read-only review of the two repeated GPS-003 first-fix failures (2026-10-16)

[GPS-003 and seven UK GPS-matching losses — retained-evidence investigation](GPS_003_INVESTIGATION_20261016.md)
documents all sixteen frozen first-reading availability failures as two repeated
ambiguous Moss Lane coordinates, separates deliberate noise/quality abstentions
from genuine required-output failures, and reviews the seven distinct older
backward-adjacent cases. No GPS safety behavior, frozen acceptance, run or source
truth was changed. Proposes a bounded candidate-geometry diagnostic only after
owner authorization. **STOP FOR OWNER REVIEW.**
