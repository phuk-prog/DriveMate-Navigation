# REF-006: additional runnable engine on a real UK map

Actual Itinero source built and calculated all three frozen public-map routes.
All3/3 route-output/endpoint checks pass, repeated on identical case bytes.
This adds a sixth actually executed external routing family across retained
historical scopes. It is **not** a ten-engine shared real-map GPS cohort, an
independent one-way-law judgement or a GPS-signal-quality test.

| Case | Returned vertices | Start error m | End error m | Output/endpoint result |
|---|---:|---:|---:|---|
|REF-006-001|4|0.050|0.189|PASS|
|REF-006-002|3|1.044|0.169|PASS|
|REF-006-003|3|0.169|1.044|PASS|

Cases2/3 reverse the same public pair; do not count them as different surveyed
roads. Complete finite nonzero geometry and each exact endpoint within5m are
required. No failed case was discarded or tolerance changed. The underlying
road map is real licensed OSM. Endpoints are deterministic non-personal samples,
selected before engine execution; no invented road network or personal traces
are used. Three successful calculations do not measure live map matching,
low-signal recovery, legal-turn correctness or app/device readiness. Those
categories remain unexecuted/unresolved here. No quality score/rank is assigned.

## Executions and the verified setup correction

Initial run38863763043 at626cee45397a77a88905174e7fa39d21c42f1b98 stopped before
engine execution. The harness mistakenly applied the previously recorded XML
subset fingerprint to the full downloaded PBF archive. Earlier code explicitly
records sha256(raw XML), proving the scope error. This is a harness provenance
fault, not an Itinero failure or a failed map judgement. Its failure is retained
in ref006-first-setup-failure-20261016.json with zero engine/case executions.

Corrected run[38864046561](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38864046561)
at9c45c8417917f5d2eb51c1dbb68b0a0923fc7637, job116852666638, built the real engine
and passed3/3. It checks the known hash on the correct XML subset and records the
archive separately. The later confirmation pins both archive and XML hashes.

Confirmation[38864551063](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38864551063)
atd38540e66aa175264e4534800a7d66a39ca47223, job116854270053, again passes3/3.
Request-manifest SHA256 remains exactly
`b4348997ca109fb873c265179f1edb7d4aa0772bad26b5198ad207deea02f87d`.
No engine policy, expected case or5m tolerance changed to fix setup.

## Reproducible inputs and engine configuration

- Real source: Geofabrik Greater Manchester260901, original OSM contributors/ODbL.
- Full source archive SHA256:`b7188b22501b878fddba6e06a90bb44ce6c2d721333e0ca57e10a1a82b568807`.
- Stripped XML SHA256:`b3a883ae9b7c85072d24afeee7a1079aea00c22264516a0e1e71d49221ad27d5`, identical to the retained prior UK replay map.
- Shared clipped PBF SHA256:`0c695874255033cc8f6ed658422afc2d9e11b00443eea584b72206de39567adc`.
- Bbox:-2.270000,53.350000,-2.260000,53.360000; complete ways include some nodes beyond the clipping box. No nodes are manufactured.
- Selection: first three existing deterministic public_uk_probe._scenarios pairs, before the Itinero run. Selection is map-derived, not an independent surveyed route truth oracle.
- Itinero source SHA:`b8a004a831d353565572c7ba41b5a40c29d79360`; Apache2.0, source package metadata1.6.0-pre037, compiled assembly1.0.0.0; car/uncontracted.
- SDK10.0.401; adapter targetsnet8.0. Exact12 resolved NuGet package versions and8 compiled DLL hashes are retained in ref006-itinero-confirmation-20261016.json. No floating or consumer-service engine version is invented.

Full source/version/endpoint/case evidence is in
[initial success](../references/ref006-itinero-real-map-20261016.json) and
[confirmation](../references/ref006-itinero-confirmation-20261016.json). The workflow
uses an ephemeral public source checkout and ignored map/build data, cleans them
up, and uploads only result/metadata artifacts. No production DriveMate source,
APK, credentials, paid provider calls or release were used.

## What comes next

Keep building actual applicable replacements toward ten; unsupported engines do
not appear in the active comparison or get zero scores. Preserve them only in
an exclusion audit. A GPS/lifecycle category may need different engine adapters
than this static routing CLI. Do not count this adapter as having passed those
categories or insert a common DMN controller and call it ten native engines.

The next real-map cases must freeze source-backed expected facts and controlled
GPS schedules before tuning. DMN runs independently against that oracle; other
engines run separately on byte-identical inputs. For one-way legality, supplied
map tags establish a map-contract expectation; dated authority/signage evidence
is needed for an independent real-world legality claim. National Highways records
must be checked for their actual coverage/time/meaning, not used as generic truth.

See DMN_EXPANDED_VALIDATION.md for the updated eight logical batches, expansion
limits, source policy and improvement register. See DMN_APP_READINESS.md and
[readiness inventory](../references/dmn-app-readiness-20261016.json) for the current
NOT_READY_FOR_LIVE_NAVIGATION decision. The UK17/0/23 coverage tradeoff remains
unresolved; app integration, native/emulator proof, ten-engine real-map cohort
and independently justified real-road cases are not complete. Green CI validates
the research code; it is not an app-adoption decision.
