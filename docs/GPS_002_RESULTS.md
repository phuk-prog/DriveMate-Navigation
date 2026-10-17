# GPS-002: ambiguity, faults, signal gaps and recovery

**DMN passed 16/16 frozen synthetic streaming cases**, with every required event
check passing. No new matcher defect was reproduced and no matching/confidence
policy was changed. This is input-quality/history conformance, not independently
measured real-road accuracy or a competitive navigation ranking.

[Successful execution 38816950211](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38816950211)
at `38933527cb80ff09e0c756bb8717fdd6fe2945e2`, job 116703918285. The local
baseline and CI repeat agree. All 367 unit tests, compile and privacy checks pass.
The reusable workflow's unified_preflight script is absent from this research
repository; that check is unavailable, not passed. Runtime uses Python 3.11 in CI
and repository TemporalRoadMatcher defaults. The fixture declares its engineering
quality/history thresholds before tuning; no provider output supplied truth.

| Frozen case | Required behaviour | Result |
| --- | --- | --- |
| parallel-first | Withhold equal-fit road choice without identifying history | PASS |
| parallel-repeat | Repetition alone must not turn equal fit into confidence | PASS |
| anchor-resolves | Unique fresh feeder anchor permits north-road resolution | PASS |
| speed-spike-recovery | Reject speed spike, retain trusted fix, recover | PASS |
| weak-fix-recovery | Suppress weak-accuracy output, recover on good evidence | PASS |
| bad-burst-expires | Third unresolved sample expires default anchor budget | PASS |
| gap-withholds | Expire old anchor after long no-observation gap | PASS |
| gap-reacquires | Fresh unique evidence reacquires, then resolves continuation | PASS |
| duplicate-recovery | Reject duplicate timestamp without moving trusted fix | PASS |
| out-of-order-recovery | Reject backwards timestamp without moving trusted fix | PASS |
| stale-recovery | Reject delayed packet using reception clock, then recover | PASS |
| future-recovery | Reject packet dated after reception without advancing history | PASS |
| position-jump-recovery | Reject implausible teleport, then recover | PASS |
| missing-heading | Withhold parallel-road resolution without movement heading | PASS |
| zero-speed | Withhold movement-based resolution for stationary observation | PASS |
| reset-isolation | Session reset clears anchor and trusted history | PASS |

PASS requires every event's declared status, expected directed way on positive
controls, no road identity on withheld/rejected output, and unchanged trusted fix
where required. Refusing a match is a pass only where the frozen oracle explicitly
requires refusal. Recovery cases also require subsequent correct positive matches;
a matcher that always abstains fails these controls. A signal gap is a simulation
of missing observations, not an actual tunnel or dead-reckoning test.

Map SHA-256: `e3b376ed40705599fa3c8ad2c9b88e239b24cddb040dc676702fee49ba4c5bb9`.
Oracle SHA-256: `f1e2e87788a953a105d9f6daad30441c037c4a5cac37cfd4d205e6362cd82442`.
[Exact per-event evidence and all-family coverage](../references/gps002-stream-batch-20261015.json).

## Reference applicability and scores

The conformance formula is `10 * passed / 16`; DMN is 16/16 = 10/10. It is the
only judged stream in this stage, so its rank must not be presented as beating
external engines. All twelve families remain visible with per-case reasons.

| Family | GPS-002 interface status | Reason |
| --- | --- | --- |
| OSRM | UNSUPPORTED | Integrated batch Match API lacks equivalent reception-clock/reset/trusted-stream contract |
| Valhalla | UNSUPPORTED | Integrated trace_attributes API lacks that stream contract |
| GraphHopper | UNSUPPORTED | Integrated batch map-matching API lacks that stream contract |
| openrouteservice | UNSUPPORTED | Integrated pointwise snapping lacks that stream contract |
| BRouter | UNSUPPORTED | Integrated routing API does not consume GPS observation streams |
| OsmAnd | NOT_RUN | Executable app/native lifecycle replay harness not implemented |
| Organic Maps | NOT_RUN | Executable app/native lifecycle replay harness not implemented |
| HERE | NOT_RUN | No configured permitted access and equivalent lifecycle interface |
| Mapbox | NOT_RUN | No configured permitted access and equivalent lifecycle interface |
| TomTom | NOT_RUN | No configured permitted access and equivalent lifecycle interface |
| Google Maps | NOT_RUN | No configured permitted access and equivalent lifecycle interface |
| Waze | NOT_RUN | No established permitted automated lifecycle replay interface |

Unsupported describes the currently integrated endpoint for this full streaming
contract, not a claim that the product cannot navigate or handle poor GPS. No
external executable was run for GPS-002; a batch geometry response would not be
valid evidence for reception-clock or session-history expectations. Their actual
GPS-001 geometry and ROUTE-001 routing results remain separate and intact.

## Diagnosis and next bounded stage

This batch reproduced no new DMN fault, so there is no evidence-backed engine fix
to make here. The new implementation is a frozen executable conformance harness,
CI gate and retained per-event evidence. Future failures stop CI and retain their
report instead of being silently counted as passes.

Do not repeat this unchanged batch as a substitute for new work. Next, expand
ROUTE-001 with the other applicable self-hosted references sequentially, then
freeze access/prohibited-turn/disconnected-road cases and rerouting recovery.
OsmAnd/Organic Maps streaming harness work remains separate. The seven UK lost
matches remain unresolved (17 correct / 0 confident wrong / 23 withheld in the
last map replay). No map replay was rerun in this stage. Promotion stays blocked;
there is no Android/device, independently surveyed-road or physical GNSS evidence.
