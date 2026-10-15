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
