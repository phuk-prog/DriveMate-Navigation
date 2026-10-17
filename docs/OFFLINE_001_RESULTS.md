# OFFLINE-001: verified in-memory map activation and recovery

DMN passes **18/18 frozen package cases** in an actually isolated Linux network
namespace. The run makes12 map-store route requests and9 actual core calculations
(seven routes and two no-route refusals). All425 tests pass. This is research
Python package conformance, **not Android/native offline-navigation readiness**.

The new OfflineMapStore verifies manifest schema/format, exact byte length,
SHA256, source attribution and required node presence before activating a parsed
map. It publishes the new snapshot only after all checks succeed. Failed updates
preserve the previous map and routes; routes include the exact package digest so
old route IDs cannot silently be interpreted against a replacement map. No map,
missing node coverage and a known-node no-legal-route result are distinct errors.
No nearest-road relocation or online fallback is performed.

The expected edge paths come from previously frozen ROUTE-002/JUNCTION-001
invented maps. They are analytical controls, **not independently surveyed road
or legal truth**. Required anchors establish node presence, not regional coverage,
connectivity or physical/legal road correctness. SHA256 establishes consistency
against the caller-trusted manifest; it is not authentication, source authority
or map freshness. The wrapper accepts immutable bytes in memory and does not
install files, verify signatures, implement crash recovery or guarantee concurrent
updates. No production DriveMate code or APK was changed.

## Exact frozen results

| Case suffix | Required result | Verdict |
|---|---|---|
|no-active|NO_ACTIVE before any verified map|PASS|
|valid|ActivateA and return the declared turn-restricted route|PASS|
|checksum|Reject mismatch; leave no active map|PASS|
|truncated|Reject truncated bytes|PASS|
|length|Reject declared byte-length mismatch|PASS|
|schema-version|Reject unsupported schema2|PASS|
|format|Reject unknown format|PASS|
|provenance|Reject missing attribution|PASS|
|malformed|Reject malformed XML even with matching manifest hash|PASS|
|unsupported-condition|Reject unsupported conditional tags even with matching hash|PASS|
|bad-update-retains|Reject corrupt update; retainA and its exact route|PASS|
|valid-replacement|ReplaceA withB; route usesB's declared edges|PASS|
|disconnected|Known disconnected destination returns NO_ROUTE|PASS|
|prohibited-destination|Known prohibited-access destination returns NO_ROUTE|PASS|
|unknown-node|Absent destination returns NO_COVERAGE, not NO_ROUTE|PASS|
|recovery|A valid map activates/routes after a rejected malformed package|PASS|
|missing-required-coverage|Reject missing anchor; retainA and its route|PASS|
|oversize|Reject payload above100000-byte replay limit|PASS|

Case IDs use prefix`OFFLINE-001-`. A negative case passes by safely rejecting the
bad input or refusing the route; it does not fabricate a positive route. The
[executed report](../references/offline001-after-20261016.json) records every
expected/actual event status, checks, exact returned edges, lengths, package IDs,
rejection reasons and all variant payload/canonical-manifest hashes.

## Reproduced scoring fault and retest

The initial local scorer assigned rank1/10 despite absent isolation evidence.
A new negative control failed with observed rank1 versus expected unranked.
The [preserved first-scorer evidence](../references/offline001-first-scorer-20261016.json)
includes the original function, working-tree harness hash, actual local report
and base SHA. It is explicitly local evidence, not a claimed CI execution.

The fixed scorer requires actual isolation evidence before assigning the offline
score. An unisolated local execution now retains all18 case verdicts but has
rank=null and score=null. The same negative control passes, as does the subsequent
isolated CI cohort. No oracle, package case or acceptance threshold changed.
The pre-existing baseline had no activation wrapper, so its capability is
UNAVAILABLE, never an invented0/18 engine score.

Seven additional tests pass: isolation-score suppression; immutable active info;
caller manifest mutation cannot mutate the active snapshot; exact payload-limit
boundaries and invalid limits; strict schema/type/anchor validation and mutable
payload rejection; old routes retain original package identity after replacement;
and incomplete scorecard rejection. They include multiple adversarial subcases,
not blind holdouts. Existing GPS, routing, rerouting, junction and arrival
regressions also pass. No prior matcher/router acceptance was loosened.

## Isolation and reference coverage

CI invokes the real parser/router under`sudo unshare --net`; no engine response
or network result is mocked. Kernel evidence reports a distinct network namespace
and zero IPv4 or non-loopback IPv6 default routes. The command explicitly requires
isolation and fails if it cannot be demonstrated. The local workspace cannot
supply equivalent namespace evidence; its offline score is therefore unassigned.
The namespace constrains this replay's network access; it does not establish
phone offline storage, service lifecycle or native-library behavior.

Only DMN executes this18-case package protocol. Its10/10 is conformance, **not a
comparative engine ranking**. Score=`10*passes/18`, assigned only to a complete
judged cohort with demonstrated network isolation. All12 external families plus
DMN, all18 cases and exact unsupported/not-run reasons remain in the
[scorecard](../references/offline001-scorecard-20261016.json).

OSRM, Valhalla, GraphHopper, openrouteservice and BRouter are UNSUPPORTED through
the current static directions adapters for this specific DMN manifest/activation/
node-ID error contract. Their own native file formats and package lifecycles need
separate adapters and cases; these results do not assess their offline quality.
No static route request was substituted for package activation. Last executed
static configurations remain OSRM5.27.1 car.lua/MLD, Valhalla3.9.1 auto,
GraphHopper11.1 car/CH, ORS10.1.0 driving-car/fastest and BRouter1.7.10 car-vario,
as pinned and hashed in JUNCTION-001. None is claimed executed for OFFLINE-001.

OsmAnd/Organic Maps are NOT_RUN without executable app/native package harnesses.
HERE/Mapbox/TomTom/Google Maps are NOT_RUN without configured permitted access
and an equivalent offline package harness. Waze is NOT_RUN without an established
permitted automated offline interface. Missing tests/access are not passes or
zero-quality scores. No provider spending, credentials, proprietary maps, personal
traces or unsupported automation were used. A genuine common native offline
routing comparison remains unexecuted; this wrapper test cannot replace it.

## Provenance and continuation

- Inspected baseline:`669a76f0ce70c2e54ddbc15cca451d21ecfedb47`.
- Oracle freeze:`2d7885db99d3588d26cea3243ffa7c756c74b5b1`, before implementation.
- Executed implementation/fix:`1fb644870e0b5886ef63a9750f1ef1e6afa652a4`.
- CI:[38859329753](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38859329753), job116837785614, success;425 tests and18/18 isolated cases.
- MapA SHA256:`c2f908d9d0904e6aeb70cfd87c4b36d9af4871d5dd2da215dd37b55e076501cb`.
- MapB SHA256:`8b9d409865dd0b272456c2b99575c8dd29d3459602db7016377889b9b00ab465`.
- Oracle SHA256:`5a826150c996fa36f9f953431541feb4314db72f7d7b67dc94615085699c28c3`.
- Component SHA256:`bc0b97b78e1dac0dbeb60fc9b3047258e2159b7aae788cdcdb7b096f54d50b93`.
- Harness SHA256:`2fe23a09fcdc03bcdac4c526ca91b747f14e67892973341a89a384be0461f80b`.

[Availability baseline](../references/offline001-before-20261016.json), first
scorer, executed after report and scorecard are permanent repository evidence.
Normal CI now runs and retains the isolated replay. Local reproduction without
namespace proof:`python -m benchmarks.offline_integrity_trial --output results/offline001-DMN.json`.
Add`--require-isolated-network` under a genuinely isolated namespace for the CI
acceptance; unavailable isolation must fail, not be overridden with a fake flag.
Local compile/privacy/whitespace checks and full tests pass. Canonical
`scripts/unified_preflight.py` remains absent/unavailable, never passed.

Rollback removes the new research wrapper, harness/tests and CI gate; rejected
updates already preserve the prior in-memory snapshot. Disk install/crash safety,
package authenticity/freshness, Android/native route execution and lifecycle
remain unverified. Next bounded work: freeze and execute resource measurements
for applicable reproducible cohorts, keeping setup cost separate from requests;
then integration/native offline evidence. Do not repeat unchanged heavyweight
reference or UK diagnostic runs without new evidence. The UK seven-candidate
tradeoff remains unresolved at17 correct/0 confident wrong/23 withheld and still
blocks promotion; the diagnostic evidence was re-read and preserved.
