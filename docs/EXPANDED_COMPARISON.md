# Expanded navigation comparison protocol

The research branch now executes 92 additional shared routing cases across four
independently authored layouts (173, 419, 887, 1213). The first two are discovery
layouts; the latter two are predeclared held-out layouts. Each has 23 cases:

| Category | Shared cases |
|---|---:|
| Chained no/only via-way restrictions and early exits | 16 |
| Fresh-origin replans inside restricted via roads | 8 |
| Reverse one-way no-route requests | 8 |
| Multi-arm junction with prohibited turn, access and one-way constraints | 20 |
| Asymmetric multilane-tagged roundabout road paths | 20 |
| Compound corridor with chained no/only obligations, access and one-way faults | 20 |
| Total unique routing cases | 92 |

The 20 roundabout exit-number outputs are separate instruction checks on the
same routes. The five engines with trace interfaces also receive 20 identical
coordinate-only clean traces. This expands the prior nine-case baseline;
neither set includes real road observations, recorded drives or personal data.

## Truth and equivalence

`expanded_fixture.py` defines nodes, physical ways, permissions and relations
without importing DriveMate's parser or router. It exports one shared OSM map
and independently enumerates legal simple physical-edge paths. The score tests
legal reachability and destination, accepting every independently allowed path;
it does not impose one vendor's cost/turn preference or claim optimal cost.
Fourteen deliberate corrupt-output controls require a correct baseline and detect
ignored no/only restrictions, reverse travel, a banned junction turn and access.
They validate the judge, not mutations inside competitor binaries.

The four layouts vary road lengths, skew, approach angles, ring node counts and
asymmetry. They retain the same scenario families: held-out geometry is tested,
but wholly unseen restriction types and production-size road networks are not.
Planar crossings that do not share a node are not connected junctions.
All author coordinates are rounded to seven-decimal OSM precision before export
and queries. Counter-clockwise rings explicitly declare driving_side=right.
Valhalla uses these way tags with use_admin_db=false; an absent real-country
administrative database must not silently substitute an incompatible driving side.

Discovery failures and corrections are recorded in [EXPANDED_COMPARISON_FINDINGS.md](EXPANDED_COMPARISON_FINDINGS.md).

GraphHopper, OSRM MLD/CH and Valhalla independently import the authored OSM map.
DriveMate's research importer/router executes the same inputs. RoutingKit CH and
pgRouting compute routes over explicit transition graphs supplied by DriveMate's
importer/adapters. They therefore form a separate algorithm cohort: their scores
do not establish independent access/turn parsing. No vendor implementation or
proprietary data is copied into the candidate. Existing pinned reference runtime
versions/checksums and isolated localhost execution are retained.

Services consume geographic coordinates; algorithm adapters consume exact node
IDs. Returned geometry must start/end within two metres of the authored nodes.
Snapping elsewhere remains unresolved, even if its way IDs look correct.
Native-engine route geometry is independently attributed to author segments;
reversed rings cannot earn passes through a single shared way ID. Geometry
quantization/simplification outside the two-metre bound is unresolved.

Fresh-origin replan tests do not supply prior incoming-road history. Roundabout
exit expectations count independently authored distinct exits on simple rings;
multilane tags do not establish occupied lanes, spiral lane transitions or safe
driver manoeuvres. Those require separately verified lane geometry/evidence.

## Traces and uncertainty

Traces are generated from the independent author model, with identical input
hashes recorded across engines. Complete observed road-sequence outcomes are
reported. DriveMate's coordinate-only matcher streams observations; the external
engines reconstruct batches. Individual rejected clean fixes are also retained
as candidate diagnostics. Batch processing does not expose equivalent live
recovery/controller, instruction freshness or per-fix acceptance evidence, so
those interfaces are not ranked together. There is no measured GPS accuracy in
metres or physically calibrated sensor failure test in this expansion.

## Evidence and ranking

One push triggers the existing six-job `Navigation category comparison`
orchestration. Each engine writes `results/expanded/<engine>/expanded.json` and
retains raw JSON service responses. The artifact `category-scorecard` contains
`EXPANDED_SCORECARD.md` and `expanded_category_results.json`; the workflow summary
and `SCORECARD.md` lead with the expanded results and retain the original baseline.

Every category shows passed/total, failed, unresolved and not supported. Reports
reject different map/protocol/trace hashes, missing cases, duplicate engines,
missing mutation controls and a revision different from the report checkout.
Absent executions are unresolved, never awarded passes. Per-category ranks are
published only for completely resolved matched cohorts, with ties preserved.
Legal/critical failures take precedence over speed; no new speed score is run.
Exact failing IDs, allowed/actual paths, endpoint diagnostics and exit outputs
are retained. A mismatch identifies the violated authored invariant; vendor
internal root cause must still be isolated before attributing a code defect.

An overall navigation-app winner is not supported. Live GPS recovery, spiral
lane occupancy, voice, device efficiency, realistic sensor calibration and
independently verified real-road permissions remain outside this shared test.
No production repository, application, APK, signing or release is involved.
