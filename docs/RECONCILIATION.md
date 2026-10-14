# Navigation-only reconciliation

Based on public main commit 05fc0a7f1f7f848b894a146c62835b871f6e09e2.
This local change connects the independent routing lab to DriveMate Navigation.
It does not touch the Android app, create an APK or import private app code.

Added navigation_core contains original static routing, multi-road restrictions,
vehicle limits, directed partial-road endpoints, portable implementation and a
trusted-road journey controller. engine/reconciled.py adapts the existing bounded
OSM importer graph into this core while retaining original edge/node identifiers.
Existing Dijkstra/A* implementations remain independently available as references.

Imported road access is preserved: allowed and unknown motorcar edges are enabled; confirmed
prohibitions remain blocked. Unknown access is reported in unverified_access_edges
for routes and journey snapshots, rather than silently presented as verified. Existing prohibited-turn pairs become no-turn
rules. Additional explicitly authored multi-road no/only rules can be supplied;
the XML importer still rejects via-way/conditional rules it cannot understand.
This bridge does not make that importer production-ready or restore missing map data.
Legacy imported graphs do not carry height/weight restrictions; those are not
invented. No bus access is inferred from a motorcar graph.

Costs are integer microseconds, rounded upward once per road. Each road gains less
than one microsecond from quantization; almost-equal route choices can differ from
the old floating-point algorithms. Return times disclose the quantized costs.
Graph/mapping snapshots are immutable; research router preparation and landmark
tables are reused. Same-road journey progress reuses its remaining plan and costs.
Portable requests currently launch a host process; persistent execution and mobile
resource measurements remain pending.

Run:
```
bash navigation_core/native/build.sh
python3 -m compileall -q engine navigation_core map_data benchmarks tools tests
python3 -m unittest discover -s tests -v
```
The amended CI definition adds this one host compilation before unit tests.
130 tests passed locally: legacy 82 + lab 40 + integration 8. The integration
checks connect imported fixtures to both backends, allow unknown access while retaining explicit bans and uncertainty metadata,
enforce multi-road inbound history, expose journey road names and verify preparation
reuse. No new CI run was triggered and no upload or commit is claimed.

Public data policy remains in force. Imported navigation components contain original
source and synthetic tests only. No GraphHopper executable, downloaded map, personal
route, app code or generated binary is committed by the reconciliation patch.
The project-wide distribution licence is still undecided.

Next: import and evaluate complex restrictions without weakening fail-closed behavior,
then build evidence-backed roundabout/lane instructions and positioning recovery.
Full comparative simulated drives require those executable components. Existing
external smoke measurements and the isolated synthetic GraphHopper checks are
separate from complete-app simulation and do not establish an overall winner.

Access policy changed on the user’s explicit instruction: absence of confirmed access information alone must not prohibit a road. Existing unknown-access test expectations and the synthetic golden route were revised for this behavior. Known prohibitions, blocked edges and illegal turn tests remain enforced. The importer still rejects unsupported conditional restrictions; unknown access is not a bypass for malformed/unsupported turn data.

The newer local stage supports clock-aware journeys; see TIMED_JOURNEY_STAGE.md.
