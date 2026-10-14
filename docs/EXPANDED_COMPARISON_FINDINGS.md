# Expanded comparison discovery and recovery

Initial expanded run: [38640016704](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38640016704),
revision `52f5a3c9b8c8ba77eac1c22643ba32563a72b692`.
The initial scorecard is retained in its Actions artifact. It is superseded for
ranking by the corrected, re-executed input/configuration; do not mix revisions.

## Shared transition-adapter defect: confirmed and reproduced

RoutingKit and pgRouting each returned 8/92 illegal early exits. For every layout,
`only_early_exit` and `compound_only_early_exit` violated the authored only-way
obligation. The root cause was our independently owned
`benchmarks.routingkit_reference.legal`, shared by the pgRouting adapter: it
checked only the final complete restriction sequence, allowing premature escape
before that sequence was assembled. This was an adapter error, not evidence of
RoutingKit or pgRouting library defects.

The correction enforces every matching prefix of each only-way sequence. A
focused test reproduced the permissive behavior before correction; the corrected
transition graph's reachability is checked against independent author truth for
all 92 requests. Native reference engines and the candidate are re-executed on
the corrected shared input contract. Original failures remain in the first run.

## OSRM runner file permissions: confirmed infrastructure failure

OSRM extraction completed, but copying `expanded.osrm.fileIndex` for the CH
configuration failed with Permission denied. The container had created this
file as root with mode 0600. The expanded extractor now runs as the runner's UID
and GID, preserving file permissions while allowing the host copy. Neither
OSRM configuration executed the expanded routes in the initial run; these are
missing executions, not zero-correct engine results.

## GraphHopper boundary precision: confirmed input mismatch

Five requests in layout1213 were rejected as out of bounds because query values
retained floating-point precision beyond the imported seven-decimal OSM bounds.
For example, longitude `0.09770000000000001` exceeded bound `0.0977`.
The author model now rounds all coordinates to seven decimals before both OSM
export and query/trace generation. A focused test reproduced the mismatch before
correction. This changes the map hash; prior artifacts are not interchangeable.

Four other requests (`junction_arm_4`, all layouts) snapped to permitted roads
135-187 metres away from the prohibited-access destination. These remain
unresolved coordinate-versus-exact-node interface evidence, not legality passes
and not proven routing-library failures. The two-metre endpoint gate remains.

## Valhalla driving-side configuration: source-backed cause, rerun required

The initial expanded map used counter-clockwise rings without explicit driving
side. Valhalla returned exit 2 for all five exits of each ring, giving 4/20 correct
numbers although all 20 ring paths were legal and correct. Raw maneuver type 26
contained the incorrect exit count and spoken/text instruction; this was not a
JSON field-selection error.

The reference disabled admin generation but retained `use_admin_db=true`.
In the pinned [3.9.1 graph builder](https://github.com/valhalla/valhalla/blob/3.9.1/src/mjolnir/graphbuilder.cc),
absent admin polygons leave drive_on_right false; setting use_admin_db false
instead takes the flag from each OSM way. The
[pinned parser](https://github.com/valhalla/valhalla/blob/3.9.1/src/mjolnir/pbfgraphparser.cc)
reads the driving_side tag. The same symptom and missing/wrong administrative
driving-side metadata are discussed in [upstream issue 1099](https://github.com/valhalla/valhalla/issues/1099).

The correction explicitly declares driving_side=right on every author way and
generates the reference configuration with use_admin_db=false, appropriate for
synthetic data with no real-country administrative polygons. It retains the
original ring direction and expected exits. The corrected run must verify the
result before claiming recovery. No third-party source was copied or patched.

## Candidate clean-fix diagnostics

DriveMate recovered the complete expected sequence for all 20 clean traces.
Four detour traces each rejected one fix as direction_mismatch at a sharp turn:
the derived bearing from the preceding segment briefly disagreed with the new
segment. This is a conservative streaming observation gate, not a false legal
permission or a lost final road sequence. These per-fix diagnostics remain
visible, separately from external batch sequence scores. No physically
calibrated sensor/controller accuracy claim or threshold relaxation is made.
