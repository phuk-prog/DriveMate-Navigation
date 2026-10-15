# Numbered navigation trials

The owner requested twelve external references plus DMN, exact case verdicts,
descending ranks, independent judgement, error diagnosis, improvements and
retesting. Begin with **GPS-001**, a deliberately small controlled correctness
trial. The previous UK map-generated geometry proxy remains separate.

## GPS-001 frozen acceptance

Six fixed scripted trajectories use an invented closed one-way road network.
Their expected positions and east/west direction are declared in
`benchmarks/fixtures/synthetic-gps-001.json` before changing the matcher. They
are not inferred from a DMN graph, a competing engine, or provider consensus.
This is an independent **analytical synthetic oracle**, not independently
surveyed UK road/GNSS evidence. The two fixture SHA-256 hashes bind each run.

Each case must return all four observations, each within 5 m of its declared
position, progressing in its declared direction. The six cases are east/west
clean movement, east/west lateral noise, and east/west movement across multiple
short graph links. For these unambiguous clean-input cases an abstention fails
the explicitly required-output check; it is reported as `missing_required_match`,
never as a confident wrong-road assignment. Partial responses cannot be aligned
by guessing their original indices. HTTP or setup errors are not engine verdicts.

All three checks must pass for a case to pass. The scoped synthetic score is
`10 * passed cases / 6`; sort descending and give equal scores equal ranks.
No averaging with other categories, timing or unavailable providers. This is a
finite functional contract, not an overall navigation-quality ranking. The
batch matching vs streaming interface distinction remains visible.

Every scoreboard includes the existing twelve external families and DMN.
OsmAnd, Organic Maps, BRouter and openrouteservice currently lack an integrated
permitted adapter for this GPS test; no claim that these products cannot navigate
is made. HERE, Mapbox, TomTom and Google lack configured permitted credentials
and same-fixture interfaces; no paid calls are authorised. Waze has no permitted
automated replay interface. All nine remain UNRANKED/NOT RUN with reasons. Adding
adapters is a separate capability task; names are never substituted by mocks.

## Execute

```sh
python -m benchmarks.navigation_trial --engine DMN --output results/gps001-DMN.json
python -m benchmarks.navigation_trial --reports results/gps001-DMN.json --output results/gps001-scorecard.json
```

The bounded `[gps-001]` research PR workflow executes version-pinned actual
OSRM, Valhalla and GraphHopper sequentially (`max-parallel: 1`) against the
identical invented road fixture and observation JSON. Engine results include
each case's checks, errors, missing observations and exact failure reasons.
No provider result counts as executed until its job and artifact are checked.

Preserve the original failing DMN run before implementing a fix. Retest the
same cases, safety regressions and separately authored counterexamples. A case
viewed during diagnosis is not claimed as a blind holdout, even if its original
fixture split says `held_out`. Independent real-world legality, physical-road
identity, GNSS calibration and device navigation still require other evidence.
Never claim universal superiority; use better tested references to identify
specific deficits and aim to exceed them on harder, independently justified tests.

## Resume after UK topology investigation

The bounded diagnostic run 38810752808 at
`f17131dd2ea35b80b94657177074fbbd706aaa6a` identifies backward-adjacent alternatives
in all seven lost matches; it does not safely resolve them. Full evidence is in
`references/gps001-uk-topology-20261015.json`. Keep the 40-case coverage tradeoff
and promotion block open. Do not repeat this unchanged diagnostic automatically.
The next unblocked stage is GPS ambiguity/fault/recovery: freeze explicit
analytical cases and required abstention/recovery expectations before tuning,
then execute applicable permitted references sequentially and preserve interface
limitations per case. No surveyed UK truth has been obtained.

## Additional runnable reference: openrouteservice

The owner requested execution of previously unrun references or alternatives.
GPS-001 now has a self-hosted openrouteservice 10.1.0 **pointwise snapping**
adapter. Acceptance and fixture hashes remain frozen; no engine tuning or DMN
policy change is authorised by a missing result. This endpoint returns positions
in input order, with explicit null slots; a partial response is never aligned by
guessing. The same six position/output/progression checks apply. Observed
coordinate progression is not proof that ORS inferred legal driving direction;
this endpoint has no temporal inference. Do not extrapolate its score to that.

The bounded `[ors-gps001]` CI job uses the official v10.1.0 JAR, SHA-256
`46b83b353eaf8830a1b53cad91d027e00547cd9a00e86efddd64a45335bfb8e1`, Java 25,
the same invented map, driving-car, radius 20 m, no elevation, disabled tiny-network
pruning and no CH/LM/core preparation. No hosted API calls or keys. Startup or HTTP
errors are unavailable execution, never case failures or passes. Source contract:
https://github.com/GIScience/openrouteservice/blob/v10.1.0/ors-api/src/main/java/org/heigit/ors/api/controllers/SnappingAPI.java

BRouter can be self-hosted for routing, which needs its own frozen route contract;
OsmAnd and Organic Maps need executable app/native harnesses. Their GPS-001
adapter gaps remain work, not evidence of poor navigation. Commercial/Waze access
restrictions remain unchanged. The original twelve-family roster is preserved.
