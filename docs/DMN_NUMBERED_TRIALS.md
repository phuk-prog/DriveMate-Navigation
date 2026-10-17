# Numbered navigation trials

## INTEGRATED-001 engine-only journey baseline (17 October 2026)

DMN passes 3/3 frozen synthetic component-integration journeys: clean route/
match/guidance/arrival, corroborated wrong-turn replacement, and a prohibited-
turn detour. The oracle was frozen at `aa99395`; execution source is `d12af5c`.
All twelve external families retain per-case UNSUPPORTED or NOT_RUN reasons;
there is no competitive ranking. This is an engine-only analytical baseline,
not Android, physical GNSS, UK road truth or app readiness. Exact results are in
`references/integrated001-dmn-20261017.json` and
`references/integrated001-scorecard-20261017.json`; see
`docs/INTEGRATED_001_RESULTS.md` for limitations.

## INTEGRATED-002 roundabout and GPS-confidence baseline (17 October 2026)

DMN passes 3/3 synthetic integrated cases: third-exit routing/guidance, weak-GPS
guidance/arrival withholding and stale-GPS rejection. The preserved first setup
attempt was 2/3 because its frozen case omitted instruction distance; completing
that input at 50 m retained the original `APPROACH` expectation. No engine policy
changed. All external families remain unranked with interface reasons. See
`docs/INTEGRATED_002_RESULTS.md` and `references/integrated002-*.json`.

## INTEGRATED-003 offline route-context baseline (17 October 2026)

DMN passes 3/3 synthetic integration cases for valid package replacement,
corrupt-update retention and new-route binding. Old route identities visibly
stop matching after a valid map replacement; this is detection evidence, not
automatic controller cancellation or Android storage proof. External families
remain unranked with explicit interface reasons. See
`docs/INTEGRATED_003_RESULTS.md` and `references/integrated003-*.json`.

**Owner-approved prospective policy (16 October 2026):**
[DMN_PERMANENT_TESTING_POLICY.md](DMN_PERMANENT_TESTING_POLICY.md) supersedes
any earlier recommendations here about universal score-first rankings, running
only DMN on post-fix retests, or automatically improving without review. Future
tests rank each category by actual measured units; full and partial cohorts,
and verified and provisional source truth, remain separate. After explicit
approval of an improvement, newly run DMN **and every available applicable
competitor** on the complete affected comparable frozen set. Earlier entries
below are historical test records and are **not** retroactively rescored or
re-executed by this documentation change.

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

Executed outcome: run 38814980108 at `e80e54a9b4ea3195dede7bcba727c3c65ad8f156`
completed all six ORS requests: four PASS, two UNSUPPORTED (explicit ORS 8010
outside-graph-bounds rejection). Full-cohort score remains unassigned; see the
expanded scorecard and GPS_001_RESULTS.md. A scorecard regression test now ensures
unsupported cases cannot receive a full score. Next additional original-roster
reference work is a separately frozen routing contract for self-hosted BRouter,
which may also enable ORS routing comparisons. Do not substitute snapping for
ambiguity, fault, temporal-recovery or legal-driving checks.

## ROUTE-001 frozen acceptance: BRouter integration stage

Four explicitly declared synthetic routes use a translated invented one-way
rectangular cycle. Bottom runs east, right north, top west, left south. Two
requests travel directly east/west; two request the opposite direction and must
follow the full permitted detour. Each simple directed path is unique. Expectations
are in `benchmarks/fixtures/synthetic-route-001.json`, fixed before BRouter
execution or matcher tuning. This is an analytical synthetic oracle, not
independent surveyed road or legal truth. GPS-001 rankings stay separate.

Require both endpoints within 2 m, all returned vertices and quarter/mid/three-quarter
segment samples within 2 m of the declared path, monotonically forward path
progress (0.5 m numerical tolerance) and path length within 5 m of expectation.
No ETA or performance ranking. Synthetic score: `10 * passed / 4`, ties share
rank. All twelve external families plus DMN retain per-case execution status.
Only BRouter and DMN are scheduled in this bounded integration stage; existing
OSRM/Valhalla/GraphHopper/ORS route adapters still need integration with this new
contract, so no cross-category GPS score is substituted for routing execution.

BRouter uses the official 1.7.10 release ZIP (SHA-256
`023fec3ba997758e8cd7ab9e1bae52e962af3f00b57683e3de86b84ffad01532`), Java 17,
car-vario defaults. Map builder stages follow upstream MapcreatorTest/OsmFastCutter,
PosUnifier and WayLinker using our invented PBF, no elevation data or downloads.
Missing filter profiles come from source commit
`4d2639af77ea5ed9c30d3e400764eb6f9e8522da`. Record JAR, profile, lookup and generated
segment hashes, exact run SHA and CI URL. Startup/import/HTTP errors remain
unavailable execution; no mocked or inferred route may count as a pass.

ROUTE-001 executed successfully in run 38815930888 at
`f8e7cc3d4e5bb07b82ca9a7cbbba88ee7eac420d`: DMN 4/4, BRouter 4/4, tied
10/10 on the frozen synthetic one-way cohort only. See ROUTE_001_RESULTS.md and
references/route001-brouter-20261015.json. Do not repeat this unchanged integration
run automatically. Complete remaining applicable reference adapters and harder
legal/access cases in bounded stages; preserve the independent GPS ambiguity and
UK coverage work rather than treating this small tie as road readiness.

## GPS-002 frozen batch: stream ambiguity, faults, gaps and recovery

Sixteen analytical synthetic cases and per-event expectations are declared in
`benchmarks/fixtures/synthetic-gps-002.json` before tuning; a separate invented
feeder joins only the northern of two parallel one-way roads. Road topology is
hand-declared, while clock/quality expectations come from explicit engineering
limits: anchor age 20 seconds, at most two unresolved samples, fix age 10 seconds,
physical plausibility screen 90 m/s, weak accuracy above 35 m. These limits are
contracts under test, not independently calibrated GNSS or road/legal truth.

Cases cover equally plausible first/repeated observations; a fresh feeder anchor;
single bad-speed and weak-accuracy recovery; burst expiry; long-gap withholding
and reacquisition; duplicate, out-of-order, stale and future timestamps; an
impossible jump; unavailable heading; stationary ambiguity; and session reset.
Require every declared event status, the expected directed way for positive
controls, no edge claim on withheld/rejected outputs, and unchanged trusted fix
where a packet is rejected. Every assertion must pass for its case to pass.
Score = `10 * passed / 16`; do not mix with GPS-001 or routing scores.

This is a streaming input-quality/history contract, not a batch position-snap
contract. Existing OSRM/Valhalla/GraphHopper batch APIs do not expose equivalent
reception clocks, resets or trusted stream state. ORS pointwise snap and BRouter
routing likewise cannot express it. Mark these integrated interfaces UNSUPPORTED
per case, not bad engines or fabricated fails. OsmAnd/Organic Maps need app/native
lifecycle harnesses; four commercial services lack configured permitted access;
Waze has no established permitted automation. Retain all twelve external families
plus DMN with exact per-case reasons. Only DMN has a judged cohort in this stage;
its numerical score is conformance, not a competitive quality ranking. Do not
run heavyweight batch routers merely to substitute positions for lifecycle checks.

Execute `python -m benchmarks.gps_fault_batch --output results/gps002-DMN.json`.
The normal research CI runs this small deterministic batch and preserves its
per-event report. Map and oracle SHA-256 bind each report. No matcher tuning is
warranted unless a fault is reproduced. UK coverage remains unresolved, and no
physical tunnel navigation or device readiness is established by a no-fix gap.

GPS-002 completed: run 38816950211 at
`38933527cb80ff09e0c756bb8717fdd6fe2945e2`, DMN 16/16, no matcher policy
changes. See GPS_002_RESULTS.md and references/gps002-stream-batch-20261015.json.
Only DMN was judged; other current endpoints are unsupported or lack lifecycle
harness/access, with per-case reasons. Normal CI now gates this frozen batch.
Next bounded work should add other applicable self-hosted engines to ROUTE-001,
then frozen routing access/turn/disconnection and rerouting cases. Preserve the
UK ambiguity promotion block and the remaining app/native streaming harness work.

## ROUTE-001 additional reference execution batch

The `[route001-refs]` bounded workflow executes OSRM 5.27.1, Valhalla 3.9.1,
GraphHopper 11.1 and openrouteservice 10.1.0 sequentially (max-parallel 1), plus
DMN on the same frozen four cases. Fixture, oracle, tolerances and acceptance are
unchanged. Retain BRouter's earlier actual execution with its own run SHA rather
than claiming it was rerun. Geometry is requested explicitly: OSRM full GeoJSON,
Valhalla polyline6, GraphHopper unencoded calculated points, ORS directions GeoJSON.
The decoder is checked against a published polyline test vector and truncation
controls. No ETA/profile-cost ranking is inferred from these unique-path cases.
A scorer now rejects incomplete judged outcomes instead of assigning a score to
unsupported cases; invalid/incomplete engine execution remains unavailable.
After this expansion, freeze separate access/turn/recalculation expectations
before tuning, preserving UK unresolved matching evidence and promotion block.

ROUTE-001 expansion completed: run 38818121643 at
`4b5cc0a72c82c71bf26cf8ac5a643f2ebd7b6185`, OSRM/Valhalla/GraphHopper/ORS
and DMN each 4/4. Combined with BRouter's prior executed 4/4, six systems tie
10/10 on the unchanged four-case synthetic one-way contract. Seven external
families remain unranked with exact per-case reasons. No engine policy changed.
See ROUTE_001_RESULTS.md and references/route001-expanded-20261015.json plus
route001-expanded-scorecard-20261015.json. Do not rerun unchanged heavy engines.
Next bounded stage: freeze and execute routing access/turn/disconnection and
rerouting-context cases. These harder cases have not yet been executed; the
four-case tie does not clear them, and does not clear the UK coverage block.

## ROUTE-002 frozen legality/recalculation stage

**Later ROUTE-004 scorer correction (17 October 2026):** a recorded geometry
harness gap was reproduced: the old reverse-edge detector missed backward travel
split across multiple short in-corridor vertices. The prospective detector now
passes 5/5 frozen analytical controls, including forward, detour and incomplete
negative controls, at source `9da6f6737daa91e41238dde177f7dd93226cb2da`.
This is not a navigation-engine rerun and does not alter ROUTE-004's historical
six-engine verdicts. See `references/route004-detector-controls-20261017.json`.
The second recorded ROUTE-004 harness gap is also corrected prospectively:
allowed-direction output must now traverse the nominated edge corridor instead
of passing on matching endpoints alone. Its frozen forward/reverse/detour/
incomplete controls pass 5/5 at `3e53f725f9ec82a7e9a800c7ec9435d1ae7ebbc9`;
historical rankings remain unchanged. See
`references/route004-selected-edge-controls-20261017.json`.
A retained-evidence quality audit then checked every complete ROUTE-004 distance
and surfaced one ≥20% spread: `ROUTE-004-005-reverse` ranged from 170.8 m to
251.578 m across six systems. It remains unresolved rather than failed because
equivalent route geometry and an independent legal optimum were not retained.
No ranking or historical rescore was produced; see
`references/route004-quality-diagnostic-20261017.json`.

Eight hand-authored synthetic cases use a new explicit directed map and JSON
oracle: prohibited-turn detour, unrestricted fresh-origin control, motor_vehicle=no
shortcut bypass, disconnected destination, prohibited-access destination,
rerouting with an incoming prohibited turn, rerouting around a blocked link and
safe no-route when all legal detours are blocked. Expectations are analytical,
not independently surveyed/legal road truth. All declared legal simple path
variants are accepted: different provider turn costs must not become fake
legality failures. A road geometry must satisfy ROUTE-001's 2 m endpoint/path and
5 m length tolerances for one enumerated legal path. No-route requires an explicit
route-search refusal, never generic HTTP errors, missing maps or invented output.

Freeze `synthetic-route-002.xml` and `.json` before tuning. Five static cases are
shared by DMN, OSRM, Valhalla, GraphHopper, ORS and BRouter; execute all permitted
local engines sequentially (`[route002-refs]`, max-parallel 1). Rank only the five
fully judged shared cases, score `10 * passed / 5`, ties share rank. Preserve
all eight cases for every family. Three state cases use DMN incoming-edge or
arbitrary blocked-link state: existing external adapters cannot express the same
state and remain UNSUPPORTED for those cases, not failed. Seven unavailable
families remain unranked with per-case NOT_RUN reasons. An unresolved shared
case prevents ranking that engine on the full five-case cohort.

Use prior version-pinned engines/configuration families, the same i…10447 tokens truncated…         raise OSMImportError(f"way {way_id}: unsupported oneway value {oneway}")
        direction = -1 if oneway in ("-1", "reverse") else 1
        speed = _estimated_speed(tags.get("highway", ""), tags.get("maxspeed"))
        for i, (src, dst) in enumerate(zip(refs, refs[1:])):
            if src not in coordinates or dst not in coordinates:
                raise OSMImportError(f"way {way_id}: missing node coordinate")
            length = _haversine(coordinates[src], coordinates[dst])
            if length < 0.01:
                raise OSMImportError(f"way {way_id}: degenerate road segment")
            physical = _combine_access(barriers[src], barriers[dst])
            if direction == 1:
                actual = _combine_access(_road_access(tags, "forward"), physical)
                edges.append(RoadEdge(f"w:{way_id}:{i}:f", src, dst, length, speed, actual))
            if direction == -1 or oneway in ("", "no", "0", "false"):
                actual = _combine_access(_road_access(tags, "backward"), physical)
                edges.append(RoadEdge(f"w:{way_id}:{i}:r", dst, src, length, speed, actual))
    if not edges:
        raise OSMImportError("No motorcar graph edges extracted")
    # Directed manoeuvres at each via node, mapping way IDs to concrete edges.
    turns: set[tuple[str, str]] = set()
    outgoing: dict[str, list[RoadEdge]] = {}
    incoming: dict[tuple[str, str], list[RoadEdge]] = {}
    leaving: dict[tuple[str, str], list[RoadEdge]] = {}
    for edge in edges:
        outgoing.setdefault(edge.source, []).append(edge)
        way_id = edge.edge_id.split(":")[1]
        incoming.setdefault((way_id, edge.target), []).append(edge)
        leaving.setdefault((way_id, edge.source), []).append(edge)
    for relation in relations:
        tags = _tags(relation)
        if tags.get("type") != "restriction":
            continue
        _check_conditions(tags, f"relation {relation.get('id')}")
        if "motorcar" in {v.strip() for v in tags.get("except", "").replace(",", ";").split(";")}:
            continue
        # Alternative mode-specific restriction tags are not assumed to apply to cars.
        rule = tags.get("restriction:motorcar", tags.get("restriction:motor_vehicle",
                    tags.get("restriction", "")))
        if not rule:
            raise OSMImportError("Unrecognised restriction relation requires review")
        if not (rule.startswith("no_") or rule.startswith("only_")):
            raise OSMImportError(f"Unsupported turn restriction: {rule}")
        members = relation.findall("member")
        frm = [m.get("ref") for m in members if m.get("role") == "from" and m.get("type") == "way"]
        to = [m.get("ref") for m in members if m.get("role") == "to" and m.get("type") == "way"]
        via = [m.get("ref") for m in members if m.get("role") == "via" and m.get("type") == "node"]
        if len(frm) != 1 or len(to) != 1 or len(via) != 1 or len(members) != 3:
            raise OSMImportError("Only single via-node turn restrictions are supported")
        node = f"osm:{via[0]}"
        arrivals = incoming.get((frm[0], node), [])
        departures = leaving.get((to[0], node), [])
        if not arrivals or not departures:
            raise OSMImportError("Restriction references a missing/non-drivable manoeuvre")
        for arrival in arrivals:
            if rule.startswith("no_"):
                for departure in departures:
                    turns.add((arrival.edge_id, departure.edge_id))
            else:
                permitted = {departure.edge_id for departure in departures}
                for other in outgoing.get(node, []):
                    if other.edge_id not in permitted:
                        turns.add((arrival.edge_id, other.edge_id))
    graph = RoadGraph(coordinates.keys(), edges, turns)
    return ImportedMap(
        graph=graph,
        coordinates=coordinates,
        metadata={
            "source_sha256": sha256(raw).hexdigest(),
            "source": provenance.source,
            "snapshot": provenance.snapshot,
            "region": provenance.region,
            "attribution": provenance.attribution,
            "vertices": len(graph.vertices),
            "directed_edges": len(graph.edges),
            "prohibited_turn_pairs": len(graph.prohibited_turns),
            "limitations": "prototype-no-conditional-via-way-or-real-world-legality-claims",
        },
    )

### Category 1 access applicability review

Evidence-only continuation from c763fea: eight unjudged ways split into three
unspecified service-access, two destination-purpose and three private-authorization
cases. Existing DMN safely withholds 59 edges (21 unknown / 38 prohibited) under
no asserted permission; legality verdicts remain 12/0/0/8. Fresh Valhalla capture
includes filtered candidates and verifies stored geometry orientation against
OSM node order. No exhaustive turn-pair equivalence or ranking. Local 101/101
map-data and 595/595 full unit regressions pass. See
`DMN_CATEGORY_01_ACCESS_APPLICABILITY.md`; verify fresh GitHub artifacts for final
candidate counts and exact-SHA outcomes. No runtime or category advancement.

### Category 1 native reference interface

From 3c8e8d2, add a read-only exporter linked to installed Valhalla 3.9.1 and a
bounded source-segment car-access comparison. Installs reference build dependencies
without patching engine behaviour. Same frozen Manchester input and cohort;
record masks/local indexes/connectivity but do not infer full AutoCost legality.
109/109 Category 1 and 603/603 full unit methods pass locally; actual native
compile/enumeration requires GitHub. See `DMN_CATEGORY_01_NATIVE_REFERENCE.md`.

### Category 1 context-aware access correction

Owner approved permission/journey-purpose handling from aed44f6. Private and
destination access without applicable caller evidence becomes unknown, not a
blanket prohibition. Grants are exact-source/way scoped and destination bound;
unknown access is not assumed open. Nineteen new controls: 129/129 map-data and
623/623 full regression methods pass locally, plus 16/16 separately labelled
frozen-source policy scenarios. Fresh same-source native Valhalla/common binary
comparison required; hypothetical permission scenarios have no equivalent
competitor profile or legality ranking. See `DMN_CATEGORY_01_CONTEXT_ACCESS.md`.

### Category 1 actual profile trial

Owner requested a driver-access profile test after 3b5850d. Freeze 32 checks on
12 isolated real Manchester ways: 24 context-profile controls and eight binary
forward/reverse controls. Exercise unchanged Valhalla auto on the same derived
inputs; expected equivalent subset is 10, with 22 permission/purpose mappings
unsupported rather than scored as faults. Local 134/134 map-data and 628/628
regression methods pass; actual live profile outcomes await GitHub. See
`DMN_CATEGORY_01_PROFILE_TRIAL.md`. No runtime/category advancement.
