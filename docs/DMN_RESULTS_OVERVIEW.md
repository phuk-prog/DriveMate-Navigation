# Executed research results and rankings

Generated from retained evidence by `python -m tools.research_results`. This is a view of recorded runs, not a new engine execution.

Scores:10 × passed / frozen judged cases; highest first, ties share rank. Historical invented-map analytical controls do not establish real-road superiority. Unsupported/unavailable families are excluded from active tables and remain in the linked source audits. No overall score mixes these cohorts.

Timing unit: milliseconds(ms), not milligrams. Missing measured calculation latency is UNAVAILABLE. Predicted journey time and maneuver duration are not calculation latency.

## GPS-001 output contract

Historical synthetic analytical road layout. Calculation speed was not measured comparably across these engines.

[Full per-case verdicts, versions/configurations, hashes, execution sources and excluded-family audit](../references/gps001-expanded-scorecard-20261015.json).

| Rank | Engine | Pass / judged | Score /10 | Calculation latency |
|---:|---|---:|---:|---|
|1|DMN|6/6|10.000|UNAVAILABLE|
|1|OSRM|6/6|10.000|UNAVAILABLE|
|1|Valhalla|6/6|10.000|UNAVAILABLE|
|4|GraphHopper|2/6|3.333|UNAVAILABLE|

| Case |DMN|OSRM|Valhalla|GraphHopper|
|---|---|---|---|---|
|GPS-001-east-clean|PASS|PASS|PASS|FAIL|
|GPS-001-west-clean|PASS|PASS|PASS|FAIL|
|GPS-001-east-noise|PASS|PASS|PASS|FAIL|
|GPS-001-west-noise|PASS|PASS|PASS|FAIL|
|GPS-001-east-multilink|PASS|PASS|PASS|PASS|
|GPS-001-west-multilink|PASS|PASS|PASS|PASS|

Recorded failures:

- GraphHopper / GPS-001-east-clean: ['missing_required_match']
- GraphHopper / GPS-001-west-clean: ['missing_required_match']
- GraphHopper / GPS-001-east-noise: ['missing_required_match']
- GraphHopper / GPS-001-west-noise: ['missing_required_match']

## ROUTE-001 one-way analytical control

Historical synthetic analytical road layout. Calculation speed was not measured comparably across these engines.

[Full per-case verdicts, versions/configurations, hashes, execution sources and excluded-family audit](../references/route001-expanded-scorecard-20261015.json).

| Rank | Engine | Pass / judged | Score /10 | Calculation latency |
|---:|---|---:|---:|---|
|1|BRouter|4/4|10.000|UNAVAILABLE|
|1|DMN|4/4|10.000|UNAVAILABLE|
|1|GraphHopper|4/4|10.000|UNAVAILABLE|
|1|OSRM|4/4|10.000|UNAVAILABLE|
|1|Valhalla|4/4|10.000|UNAVAILABLE|
|1|openrouteservice|4/4|10.000|UNAVAILABLE|

| Case |BRouter|DMN|GraphHopper|OSRM|Valhalla|openrouteservice|
|---|---|---|---|---|---|---|
|ROUTE-001-east-direct|PASS|PASS|PASS|PASS|PASS|PASS|
|ROUTE-001-west-direct|PASS|PASS|PASS|PASS|PASS|PASS|
|ROUTE-001-bottom-reverse-detour|PASS|PASS|PASS|PASS|PASS|PASS|
|ROUTE-001-top-reverse-detour|PASS|PASS|PASS|PASS|PASS|PASS|

## ROUTE-002 shared static legality controls

Historical synthetic analytical road layout. Calculation speed was not measured comparably across these engines.

[Full per-case verdicts, versions/configurations, hashes, execution sources and excluded-family audit](../references/route002-scorecard-20261016.json).

| Rank | Engine | Pass / judged | Score /10 | Calculation latency |
|---:|---|---:|---:|---|
|1|DMN|5/5|10.000|UNAVAILABLE|
|1|GraphHopper|5/5|10.000|UNAVAILABLE|
|1|OSRM|5/5|10.000|UNAVAILABLE|
|1|Valhalla|5/5|10.000|UNAVAILABLE|
|1|openrouteservice|5/5|10.000|UNAVAILABLE|
|6|BRouter|3/5|6.000|UNAVAILABLE|

| Case |DMN|GraphHopper|OSRM|Valhalla|openrouteservice|BRouter|
|---|---|---|---|---|---|---|
|ROUTE-002-prohibited-turn-detour|PASS|PASS|PASS|PASS|PASS|PASS|
|ROUTE-002-fresh-origin-control|PASS|PASS|PASS|PASS|PASS|PASS|
|ROUTE-002-motor-access-bypass|PASS|PASS|PASS|PASS|PASS|PASS|
|ROUTE-002-disconnected-destination|PASS|PASS|PASS|PASS|PASS|FAIL|
|ROUTE-002-prohibited-target|PASS|PASS|PASS|PASS|PASS|FAIL|

Recorded failures:

- BRouter / ROUTE-002-disconnected-destination: ['route_returned_for_unreachable_exact_destination']
- BRouter / ROUTE-002-prohibited-target: ['route_returned_for_unreachable_exact_destination']

## JUNCTION-001 analytical maneuvers

Historical synthetic analytical road layout. Calculation speed was not measured comparably across these engines.

[Full per-case verdicts, versions/configurations, hashes, execution sources and excluded-family audit](../references/junction001-scorecard-20261016.json).

| Rank | Engine | Pass / judged | Score /10 | Calculation latency |
|---:|---|---:|---:|---|
|1|DMN|5/5|10.000|UNAVAILABLE|
|1|GraphHopper|5/5|10.000|UNAVAILABLE|
|1|OSRM|5/5|10.000|UNAVAILABLE|
|1|openrouteservice|5/5|10.000|UNAVAILABLE|
|5|BRouter|4/5|8.000|UNAVAILABLE|
|6|Valhalla|3/5|6.000|UNAVAILABLE|

| Case |DMN|GraphHopper|OSRM|openrouteservice|BRouter|Valhalla|
|---|---|---|---|---|---|---|
|J001-L|PASS|PASS|PASS|PASS|PASS|PASS|
|J001-R|PASS|PASS|PASS|PASS|FAIL|PASS|
|J001-E1|PASS|PASS|PASS|PASS|PASS|FAIL|
|J001-E2|PASS|PASS|PASS|PASS|PASS|PASS|
|J001-E3|PASS|PASS|PASS|PASS|PASS|FAIL|

Recorded failures:

- BRouter / J001-R: ['endpoints_within_2m', 'declared_path_length', 'principal_maneuvers']
- Valhalla / J001-E1: ['principal_maneuvers']
- Valhalla / J001-E3: ['principal_maneuvers']

## Isolated DMN safety controllers

These are single-system analytical controls, with no competitive winner. Full cases and actual execution metadata are linked.

| Test | Passed / actual cases | Scope | Evidence |
|---|---:|---|---|
|GPS-002|16/16|synthetic streaming faults|[cases](../references/gps002-stream-batch-20261015.json)|
|REROUTE-001|16/16|isolated reroute lifecycle; additional controls separate|[cases](../references/reroute001-after-20261016.json)|
|ARRIVAL-001|20/20|isolated arrival controller|[cases](../references/arrival001-after-20261016.json)|
|OFFLINE-001|18/18|host Python offline routes in isolated namespace; not Android|[cases](../references/offline001-after-20261016.json)|

## RESOURCE-001 calculation timing

One DMN family, three algorithm configurations on invented weighted grids. Values below are the retained CI timing-worker measurements, ten warm samples each. Setup is separate. All displayed cases passed analytical route checks. These do not rank different navigation families or predict Android speed.

| Case | Configuration | Median ms | p95 ms | Graph build ms | Additional preparation ms |
|---|---|---:|---:|---:|---:|
|RESOURCE-001-16-diagonal|Dijkstra|2.026037|2.047083|1.818581|0.000000|
|RESOURCE-001-16-diagonal|A*-prepared|2.137589|2.245210|1.689378|0.720297|
|RESOURCE-001-16-diagonal|A*-raw|2.879438|3.000089|1.673814|0.000000|
|RESOURCE-001-16-reverse|Dijkstra|1.989963|2.198149|1.818581|0.000000|
|RESOURCE-001-16-reverse|A*-prepared|2.120833|2.193031|1.689378|0.720297|
|RESOURCE-001-16-reverse|A*-raw|2.888231|2.934260|1.673814|0.000000|
|RESOURCE-001-16-row|A*-prepared|0.086033|0.093380|1.689378|0.720297|
|RESOURCE-001-16-row|A*-raw|0.810492|0.813848|1.673814|0.000000|
|RESOURCE-001-16-row|Dijkstra|1.368523|1.602398|1.818581|0.000000|
|RESOURCE-001-32-diagonal|Dijkstra|8.747585|11.724033|5.543905|0.000000|
|RESOURCE-001-32-diagonal|A*-prepared|11.052879|13.833699|5.715132|2.948942|
|RESOURCE-001-32-diagonal|A*-raw|13.647867|16.653990|5.605167|0.000000|
|RESOURCE-001-32-reverse|Dijkstra|8.752035|8.869552|5.543905|0.000000|
|RESOURCE-001-32-reverse|A*-prepared|10.683877|11.956872|5.715132|2.948942|
|RESOURCE-001-32-reverse|A*-raw|14.030169|23.320875|5.605167|0.000000|
|RESOURCE-001-32-row|A*-prepared|0.183074|0.191977|5.715132|2.948942|
|RESOURCE-001-32-row|A*-raw|3.125361|3.155142|5.605167|0.000000|
|RESOURCE-001-32-row|Dijkstra|6.391528|6.688268|5.543905|0.000000|
|RESOURCE-001-8-diagonal|Dijkstra|0.421501|0.435963|0.378085|0.000000|
|RESOURCE-001-8-diagonal|A*-prepared|0.427514|0.462552|0.377085|0.189454|
|RESOURCE-001-8-diagonal|A*-raw|0.594910|0.614439|0.358266|0.000000|
|RESOURCE-001-8-reverse|Dijkstra|0.417670|0.447610|0.378085|0.000000|
|RESOURCE-001-8-reverse|A*-prepared|0.418551|0.433238|0.377085|0.189454|
|RESOURCE-001-8-reverse|A*-raw|0.587353|0.605977|0.358266|0.000000|
|RESOURCE-001-8-row|A*-prepared|0.042053|0.048633|0.377085|0.189454|
|RESOURCE-001-8-row|A*-raw|0.207270|0.267150|0.358266|0.000000|
|RESOURCE-001-8-row|Dijkstra|0.262243|0.277054|0.378085|0.000000|

Within each identical case, rows are ordered by measured median. These are configurations of one family, not extra engines. With10 samples, nearest-rank p95 is the largest sample; do not treat it as a stable population estimate. [Raw samples, CPU/runtime, memory scopes, versions and CI](../references/resource001-ci-20261016.json).

## Real-map reference output probes

Itinero and Routino each passed3/3 frozen endpoint/output cases. No path-law or GNSS-quality verdict is implied. Each Routino time includes a new CLI process; Itinero did not retain a comparable per-request latency, so there is no cross-engine speed rank.

| Request | Routino first ms | Routino confirmation ms | Max endpoint error m | Itinero calculation ms |
|---|---:|---:|---:|---|
|REF-006-001|1.679871|1.661987|2.253772|UNAVAILABLE|
|REF-006-002|1.366780|1.426876|0.033186|UNAVAILABLE|
|REF-006-003|1.313624|1.279746|0.033186|UNAVAILABLE|

[Routino exact commands/configuration/output and CI](../references/ref007-routino-confirmation-20261016.json); [Itinero exact evidence](../references/ref006-itinero-confirmation-20261016.json). The endpoint contract matches; speed scopes do not. No overall winner is assigned.

## Unresolved and incomplete evidence

- UK40-case replay:17 source-map-correct,0 confidently wrong,23 withheld; seven lost matches remain unresolved. [Diagnostics](../references/gps001-uk-topology-20261015.json).
- REAL-ONEWAY-001:zero eligible one-way ways in fixed extract; zero route calculations, no pass/rank. [Inventory](../references/real-oneway-inventory-20261016.json).
- Seven historical external routing families are not a ten-engine common real-map/GPS cohort.
- App, emulator/native lifecycle, physical GNSS, independent road-law and sustained target-device claims remain unverified.

## GPS-003 real-map stream results

8/24 streams pass across3 map-derived base segments;72 simulated GPS updates. Counts:{'correct': 39, 'confident_wrong': 0, 'withheld': 33, 'rejected': 12}. Map agreement and analytical fault expectations, not independent GNSS or legal truth. No competitive rank.

| Stream | Outcome | Per-event actual status | Per-event calculation ms |
|---|---|---|---|
|GPS-003-B1-clear|FAIL|AMBIGUOUS, MATCHED, MATCHED|0.206008, 0.108172, 0.153038|
|GPS-003-B1-noisy_2m|FAIL|AMBIGUOUS, AMBIGUOUS, MATCHED|0.112698, 0.089353, 0.075753|
|GPS-003-B1-weak_60m|FAIL|AMBIGUOUS, UNKNOWN, MATCHED|0.079318, 0.011277, 0.092298|
|GPS-003-B1-stale|FAIL|AMBIGUOUS, REJECTED, MATCHED|0.078407, 0.004267, 0.077005|
|GPS-003-B1-future|FAIL|AMBIGUOUS, REJECTED, MATCHED|0.076364, 0.003285, 0.075774|
|GPS-003-B1-duplicate|FAIL|AMBIGUOUS, REJECTED, MATCHED|0.075533, 0.003455, 0.074842|
|GPS-003-B1-speed_100mps|FAIL|AMBIGUOUS, REJECTED, MATCHED|0.079339, 0.003405, 0.074451|
|GPS-003-B1-gap_31s|FAIL|AMBIGUOUS, MATCHED, MATCHED|0.074221, 0.074331, 0.146719|
|GPS-003-B2-clear|FAIL|AMBIGUOUS, MATCHED, MATCHED|0.083816, 0.073430, 0.142603|
|GPS-003-B2-noisy_2m|FAIL|AMBIGUOUS, AMBIGUOUS, MATCHED|0.075683, 0.085198, 0.072178|
|GPS-003-B2-weak_60m|FAIL|AMBIGUOUS, UNKNOWN, MATCHED|0.074862, 0.004827, 0.096484|
|GPS-003-B2-stale|FAIL|AMBIGUOUS, REJECTED, MATCHED|0.073330, 0.003185, 0.072929|
|GPS-003-B2-future|FAIL|AMBIGUOUS, REJECTED, MATCHED|0.073910, 0.003385, 0.074131|
|GPS-003-B2-duplicate|FAIL|AMBIGUOUS, REJECTED, MATCHED|0.074372, 0.003174, 0.072899|
|GPS-003-B2-speed_100mps|FAIL|AMBIGUOUS, REJECTED, MATCHED|0.073820, 0.003224, 0.073450|
|GPS-003-B2-gap_31s|FAIL|AMBIGUOUS, MATCHED, MATCHED|0.073330, 0.072278, 0.160670|
|GPS-003-B3-clear|PASS|MATCHED, MATCHED, MATCHED|0.071697, 0.142834, 0.146760|
|GPS-003-B3-noisy_2m|PASS|MATCHED, MATCHED, MATCHED|0.070865, 0.141541, 0.150845|
|GPS-003-B3-weak_60m|PASS|MATCHED, UNKNOWN, MATCHED|0.071036, 0.004517, 0.141562|
|GPS-003-B3-stale|PASS|MATCHED, REJECTED, MATCHED|0.070836, 0.003175, 0.142463|
|GPS-003-B3-future|PASS|MATCHED, REJECTED, MATCHED|0.070285, 0.003145, 0.139348|
|GPS-003-B3-duplicate|PASS|MATCHED, REJECTED, MATCHED|0.071407, 0.003636, 0.139208|
|GPS-003-B3-speed_100mps|PASS|MATCHED, REJECTED, MATCHED|0.071136, 0.003194, 0.214390|
|GPS-003-B3-gap_31s|PASS|MATCHED, MATCHED, MATCHED|0.083404, 0.078107, 0.139048|

[Every frozen signal, expected/actual edge, check, failure reason, source/oracle hash and CI](../references/gps003-real-map-20261016.json). Single-update wall times are diagnostic, not cross-engine benchmarks.

## Whole-app programme

See [whole-app validation programme](APP_VALIDATION_PROGRAMME.md). App test discovery is not execution. Private app inventory stays outside this public repository. New versions/configurations must be retested; old results do not transfer automatically.
