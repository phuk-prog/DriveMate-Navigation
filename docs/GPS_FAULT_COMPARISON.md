# Matched batch trace-fault protocol

This stage adds 80 independently authored synthetic perturbations to the existing
shared map, with 20 same-protocol clean controls per supported batch engine.
It reuses the current pinned localhost runtimes in one comparison orchestration.

| What the check tests | Cases |
|---|---:|
| Alternating spatial coordinate error with magnitude 2 metres | 20 |
| One northward 40-metre outlier with unchanged declared accuracy | 20 |
| Three interior fixes missing from one authored physical segment | 20 |
| Combined error, outlier and missing fixes | 20 |
| Total unique fault cases | 80 |

Forty cases use discovery layouts and forty use the predeclared held-out layouts.
The underlying road sequence comes from the author model, never a candidate or
competitor routing result. The gap selection independently verifies both clean
control anchors and removed underlying points lie on one physical segment;
it does not remove a whole junction and pretend the unseen path is certain.
No personal data, proprietary map or measured sensor recording is used.

## Equivalent measured cohort

GraphHopper, OSRM MLD, OSRM CH and Valhalla expose complete batch reconstruction
interfaces. Each receives identical seven-decimal coordinates and a declared
3-metre accuracy, with no clock supplied. Coordinate errors/outliers intentionally
violate that declared accuracy in the fault cases. This is a controlled stress
input, not a calibrated physical GPS noise model. Similar parameter names do not
guarantee identical internal probabilistic models or search policies.

Adapters use the official interfaces: GraphHopper `/match` accepts GPX with
`gps_accuracy=3` (track points have no timestamps); OSRM `/match` receives
`radiuses=3` per observation; Valhalla `/trace_route` receives
`trace_options.gps_accuracy=3` and `use_timestamps=false`. Details:
[GraphHopper 11.1 resource](https://github.com/graphhopper/graphhopper/blob/11.1/web-bundle/src/main/java/com/graphhopper/resources/MapMatchingResource.java),
[OSRM 5.27.1 API](https://github.com/Project-OSRM/osrm-backend/blob/v5.27.1/docs/http.md),
[Valhalla matching API](https://valhalla.github.io/valhalla/api/map-matching/api-reference/).
The complete raw JSON response is retained for every control and fault request.

Common input hashes are computed from the canonical coordinate/accuracy/no-clock
contract. Reports validate them against the author-generated source, not merely
against other engines' hashes. They also require exact code revision/map hashes,
all expected cases, 20 clean controls and four corruption-detection controls.

A case earns a pass only for the complete underlying road sequence, decoded
against independently authored directed physical segments. An explicit no-match
or split result fails complete reconstruction when the same-protocol clean
control passes. Unknown geometry, malformed output and transport/runtime errors
remain unresolved. If a clean control does not pass, its fault results are
unresolved because the effect of the fault cannot be isolated. This is not a
timing, recovery-delay, real-world accuracy or whole-navigation benchmark.

## Candidate diagnostics and recovery probes

DriveMate currently exposes a streaming matcher and a bounded recovery journey;
these are not equivalent batch APIs. Their results stay out of batch ranks.
The simple matcher processes all 80 fault inputs with its existing clocked
3-metre fix policy, retaining rejected-fix diagnostics and accepted sequences.
RoutingKit and pgRouting have no equivalent trace interface and are marked not
supported for these categories.

The native recovery controller additionally runs all 80 fault traces and 20
paired clean controls across four layouts. These 100 candidate-only probes record accepted
roads, guidance availability and whether a rejected fix changed the trusted
snapshot. They are unresolved when the native runtime is unavailable. They do
not create competitor recovery-controller results or physically realistic lane
guidance. Large unseen junction gaps, coherent sensor bias, parallel-road
disambiguation, calibration, device/voice integration and real-road truth remain
outside this controlled batch.

## Reporting

The existing `category-scorecard` artifact now includes `GPS_FAULT_SCORECARD.md`
and `gps_fault_category_results.json` alongside the routing ledger. Every fault
category shows passed/total, failed, unresolved and not supported, with exact
case IDs, underlying/returned roads and issue classification. Batch ranks require
complete resolved coverage of the four matching interfaces. The 92-route ledger
and its critical legal failures remain separate and take precedence over GPS or
speed conclusions. No overall navigation winner is inferred.

## First execution findings

The first [fault run](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38644168874)
at revision `d05368baeb810117ed699a81a0d2bb946d05b2e9` recorded passing clean
controls for all four batch configurations. Fault outcomes were 80/80 for each
OSRM configuration, 70/80 for Valhalla and 64/80 for GraphHopper. These results
describe this controlled reconstruction task, not safe navigation rankings.

GraphHopper's sixteen failures were explicit broken-sequence errors after the
large outlier. Valhalla's ten responses contained a primary partial path and
remaining paths under alternates. That is its documented discontinuity format,
not evidence that it silently discarded all remaining points. The requirement
here is one continuous reconstruction; joining disconnected fragments would
invent missing evidence. The parser now explicitly rejects this split format,
including a tested case where the first fragment alone contains the expected
road IDs. Counts in the captured response replay are unchanged; exact issue
classification becomes split/rejected rather than mismatched primary sequence.

The simple candidate matcher recovered 79/80 sequences, missing the last exit
road in layout419/asymmetric_ring_exit_5/compound. All eight paired native
recovery-controller probes passed, including that case, with no trusted-snapshot
advances on rejected fixes. No production GPS thresholds or permissions were
relaxed. Those eight controller probes remain candidate-only evidence.

## Broader controller verification

The controller coverage now includes all four spatial fault families on all 20
author paths, plus one paired clean control per path: 100 cases, 50 discovery and
50 held out. Report validation requires every case and its exact clocked input
hash. This expands verification; it does not relax matcher checks or establish
competitor controller comparability. Earlier eight-probe results above are
historical evidence, not proof of the expanded suite.
