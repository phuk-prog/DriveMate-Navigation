# DMN real-map-first comparable routing research

The purpose is **selecting the best technology for the existing DriveMate
Android app**, not shipping a second standalone phone app.

### Fair shared public road routes

The primary benchmark runs compiled DMN native C++, GraphHopper, OSRM MLD,
OSRM CH and Valhalla on one identical dated UK OpenStreetMap XML extract
when their real services are available. Every engine gets the *same 16
source/destination pairs*: 8 original Wigan journeys plus 8 separate held-out
routes. The case IDs, cohort SHA-256, raw map SHA-256 and snapshot date must
match between the DMN simulated GPS replay and the separate-engine routing
benchmark. No synthetic map substitution is allowed.

Speed: 3 warmup calls + **20 measured route requests per case and engine**,
using the same local runner. Each route records validated responses out of 20,
route-level completion, failures, median/p95/p99 metrics. Rank only complete
service cohorts by **p95 warm local HTTP response time**, excluding startup.
The returned route geometry is checked for finite values, rough distance and
endpoint proximity, **not** independently verified legal manoeuvres. Different
car profiles and costing are explicitly marked.

DMN's research GPS journey replays **simulated, one-second-spaced positions
along those real public roads**. This is not a real recorded drive and does not
qualify the others as passed or failed: they did not run the same streaming
controller and voice-guidance tasks. A *full navigation ranking* must wait
for comparable observed legal-route, GPS and instruction evidence.

### Improvement and phone selection

1. Pin and validate real UK legal movements and lane/roundabout truth.
2. Compare executable equivalent trace interfaces against independent real
   geometry and identical fix streams; separate external batch map matching
   from DMN's streaming/recovery controller, which is not the same API.
3. Fix identified DMN wrong matches and ambiguous destination links.
4. Rerun all known faults, holdouts, regression and independently checked
   UK junction cases; record numerator/denominator and remaining failures.
5. Compare offline Android memory, battery, GPS sensors and audio/Bluetooth;
   check distribution and data/source licensing.
6. Recommend the best verified component for integration to the existing
   DriveMate phone app **only after explicit user approval**.

Legacy synthetic fixtures are retained only as cheaper safety regressions.
The full real-road speed workflow is the comparison job on this branch; the
smaller DMN GPS-only workflow is manual for now to prevent duplicate heavy
GitHub runs. All outputs are saved under ignored results/ and uploaded
as GitHub Actions artifacts.


## Count of remaining tests and issues

A live workstream register is now generated on every real UK routing comparison
run and embedded in `DMN_REAL_ROAD_SCORECARD.md` and
`dmn-real-road-comparison.json`. It counts **12 specific research, safety,
phone and licensing workstreams** by priority. A 100-route same-snapshot
benchmark with at least 10 measured HTTP responses per case on DMN,
GraphHopper and both OSRM configurations closes only the measurement
workstream DMN-12; it does not close legal-turn, GPS, lane, phone or audio work.

Route-testing goal: **100 real UK routes**, with **10 measured requests per
route per engine**, on identical real public-road map data. The original 8
cases and the remaining held-out routes are all retained. The same chosen
100 route endpoints also undergo DMN simulated-GPS replay so candidate and
routing benchmarks share an exact cohort hash. No comparator gets a
fictitious full-journey GPS score. The report shows route scenarios
completed/target/remaining, engine request pass/total, GPS journey
unresolved cases separately from workstream backlog and a real
p95 latency rank for complete engine cohorts only.

The distinct open workstreams are **not** the same number as individual
GPS junction holds or unverified full journeys, and never collapse to
zero merely because all regression methods passed.


### Correction to real-route geometry validation

The first 100-route attempt (run 38699306204) returned 980/1000 valid HTTP
route responses on each of five configured engines. All five rejected the
same two endpoint pairs (heldout-064 and heldout-066) solely because the
test harness demanded a returned polyline of at least 100 m, even when
a valid shortest road path was shorter than the 250-m graph walk that
selected the pair. This was a **test benchmark defect**, not five
independent route failures.

The new validator still checks finite geometry, endpoint proximity and
a non-degenerate path, but uses a necessary lower bound based on the
actual endpoint separation, allowing known snap tolerance. A route
cannot become valid just by lowering a fixed target threshold; the
response must be compatible with the physical endpoints. The baseline
100 case IDs remain unchanged so the retest is directly comparable.

The report now distinguishes routes **attempted** from routes
**fully validated across required comparator engines**, and lists both
numbers next to the remaining open workstream count.


## 15 October 2026: algorithm/compiler internal speed experiment

The existing 100-route real-map head-to-head ranked DMN native HTTP
endpoint response at p95 0.818 ms, while **native C++ computation alone**
recorded p95 0.0393 ms. These independent percentiles are not additive:
HTTP+IPC/validation/JSON overhead is the likely next significant speed
opportunity, but it must be measured and cannot be credited as if the
C++ algorithm were slower.

Before any source/legality optimisation, the *original authored C++ router*
is now benchmarked unchanged under -O2 and -O3 for Dijkstra, A* and ALT
search, each with exactly **100 same real UK routes x 10 repeats**.
The six variants must return the same route cost, and their selected
paths are independently checked for continuous legal graph movements.
Results are separated from cross-engine HTTP latency, Android performance
and real-world UK legal-turn ground truth.

Future phone design should evaluate a **single in-process C++/JNI routing
interface with low marshalling overhead** rather than carry over the Python
HTTP/subprocess research adapter. This is an architectural performance
candidate, not approval to integrate into the actual Android app. Test
JNI call/memory/power effects on real Android hardware with exact legal
route parity before changing production code.


## Native C++ compiler improvement adopted for DMN research

GitHub run 38700923509 executed 6,000 algorithm-only queries: three search
modes, two compiler settings, 100 real Wigan routes, ten repetitions each.
All paths had identical legal-graph costs and passed the tested correctness
contracts. p95 timings were 0.023284 ms for O3 ALT and 0.034295 ms for
O2 ALT, approximately 32 percent lower native-core p95 in this same-run test.

The native research build now defaults to portable O3. CI compiles a
separate unmodified O2 binary for continued fair A/B tests. Neither the
production Android app nor its compiler flags are touched.

This measured improvement covers core computations only. It does NOT
establish equivalent whole-app performance, ARM mobile battery use,
full UK map-scale performance, or independent current UK turn legality.
All 11 previously open workstreams remain open until separately verified.
