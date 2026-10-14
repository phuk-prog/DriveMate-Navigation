# Whole-drive simulations and ten reference targets

The candidate completed sixteen whole-drive simulations successfully. Actual
external execution was achieved against **one of ten external targets**, GraphHopper
11.1. The other nine were not executed and receive no score or failure judgement.
A ten-way whole-navigation ranking has not been established.

The saved registry contained nine external names. openrouteservice is an explicitly
provisional additional tenth target; it is not claimed to be the original missing
tenth from an earlier shortlist. DriveMate is the candidate, separate from all ten.

## Executed evidence

| Evidence | Result |
| --- | --- |
| Full current regression suite | 381 test methods passed |
| Whole candidate drives | 16 passed; 344 authored synthetic fix observations |
| Fresh actual GraphHopper node-route comparisons | 9 cases; both systems passed all 9 |
| Actual GraphHopper clean batch path comparisons | 4 traces; all matched the authored road sequences |
| Clean reference input | 92 raw synthetic fixes, including acquisition fixes |
| Reference executable | GraphHopper 11.1, checksum-verified isolated cached runtime |
| Dataset parity | Identical original synthetic OSM-format XML and its SHA-256 |
| Reference live recovery/audio/lane timing | Not executed; no claim of parity or superiority |

The nine route cases cover an urban two-turn route, replan from the wrong-turn
branch, a via-way turn prohibition requiring a detour, origin inside the via way,
reverse traversal of one-way roads with no route, and roundabout exits one to four.
Expected ways and exit ordinals were authored independently of either engine.
The four clean GPS traces cover urban travel, the legal wrong-turn detour, the
via-way-ban detour, and the fourth roundabout exit.

The reference receives full raw clean synthetic traces, including the acquisition
fixes that precede candidate confirmation. DriveMate handles them online with
reported bearing, speed and per-fix accuracy. GraphHopper receives an entire GPX
track and a global 3 m matching parameter. This is a comparison of resulting road
paths, not equivalent streaming algorithms, recovery strategies or timing. Actual
GraphHopper route and matching instruction responses are preserved, but no live
GraphHopper navigation controller or audio player was executed.

Route responses were reused from the first successful same-map actual run in this
task when the match protocol was changed from accepted-only points to full raw
traces. Four new full-trace matches were then executed. The older accepted-subset
comparison is retained with an explicit intermediate name and is not the final
protocol. Identical route queries were not repeated unnecessarily.

The first import attempt revealed a reference requirement that XML nodes precede
ways and ways precede relations. The fixture ordering was corrected and both
systems were rerun on the corrected identical dataset. That setup failure was not
counted as a routing or navigation failure.

## Ten-system execution matrix

| External reference | This task's result | Missing requirement / comparison limit |
| --- | --- | --- |
| GraphHopper 11.1 | Actual: 9 routes and 4 clean batch paths passed | Live GPS loss/recovery, lane assignment and voice timing not compared |
| Valhalla | Not executed | Service/container or Python binding and equivalent imported tiles |
| OSRM MLD | Not executed | Runtime/container and identical preprocessed map |
| OsmAnd | Not executed | Configured application/device replay and equivalent generated map pack |
| Organic Maps | Not executed | Configured application/device replay and equivalent generated map pack |
| BRouter | Not executed | Runtime, motorcar profile and equivalent RD5 dataset |
| HERE | Not executed | Authorised SDK adapter/access, device replay and verified dataset parity |
| Mapbox | Not executed | Authorised SDK adapter/access, device replay and verified dataset parity |
| TomTom | Not executed | Authorised SDK adapter/access, device replay and verified dataset parity |
| openrouteservice | Not executed; provisional tenth | Runtime/container and identical imported dataset |

Every target has the same requested dimensions: routing, known legality, reroute
path, GPS path matching, GPS loss/recovery, roundabout numbering, lane assignment
and instruction timing. Applicable interfaces differ: a routing service is not
automatically a full live navigation application. This difference must be declared
before treating a feature as tested or ranking it.

Local inventory confirmed no Docker/Podman, OSRM service, Valhalla service/Python
binding, BRouter command, Android device tooling, Maven or Gradle. Java was present
and the known GraphHopper runtime was restored and verified from the reusable cache.
No commercial API/SDK adapter or authorised credentials were supplied to this
benchmark. Documentation review does not substitute for any of these executions.

## Complete-drive cases

Each case ran the actual local importer, prepared routing core, GPS matcher,
recovery controller, junction/roundabout guidance and instruction scheduler through
observed arrival. The register and logs preserve per-observation states and event
acknowledgements. Fault names describe authored synthetic injections, not measured
real-world sensor physics or validated named places.

| Drive | Outcome |
| --- | --- |
| Urban clean | Pass |
| Urban tunnel | Pass |
| Urban repeated bad fixes | Pass |
| Stopped lights | Pass |
| Impossible GPS jump | Pass |
| Parallel disconnected road | Pass |
| Delayed queued-event delivery | Pass |
| Scheduler restart | Pass |
| Skipped-road recovery | Pass |
| Legal wrong turn and reroute | Pass |
| Via-way ban requiring detour | Pass |
| Roundabout exit 1 | Pass |
| Roundabout exit 2 | Pass |
| Roundabout exit 3 | Pass |
| Roundabout exit 4 | Pass |
| Roundabout GPS loss with unknown entry | Pass; original ordinal withheld after recovery |

Arrival in candidate drives uses an 80% position on the destination road, passed
with sufficient positional evidence. Node-to-node reference routing uses the full
road endpoint. Only road-sequence semantics are compared between those scopes;
candidate arrival behaviour is not scored against reference node arrival.

Known restrictions remain enforced. Unknown access or missing lane data is not a
road closure. All existing hard-case sweeps passed again in regression: 4,800 GPS
projection cases, 1,536 recovery cases, 216 independent history-oracle cases and
2,304 adversarial instruction streams. Those are separate parameterized counts,
not additional test methods or ten-system external results.

## Artifacts and reproduction

Current evidence:

- `results/whole_drive/drivemate.json`: sixteen executed drives, raw synthetic
  input, state transitions and events.
- `results/whole_drive/drive_register.csv`: per-drive pass/fail table.
- `results/whole_drive/reference/comparison.json`: final actual reference result.
- `results/whole_drive/reference/`: original dataset, configuration, runtime info,
  raw route/match responses, synthetic track XML and server log.
- `results/whole_drive/ten_system_matrix.json` and `.csv`: all ten targeted scopes,
  provisioning gaps and unscored statuses.
- `results/simulation_full_suite.log`, `results/simulation_source_manifest.json`
  and `results/simulation_source_privacy.json`: full regression and source integrity.

```sh
python3 -m benchmarks.whole_drive
python3 -m benchmarks.whole_drive_reference --jar /path/to/checksum-verified-cache.jar
python3 -m benchmarks.ten_system_matrix
python3 -m unittest discover -s tests -v
```

No reference engine source/binary is incorporated into the distributable candidate
archive. GitHub, Android, workflows and APKs remain unchanged. No real-road, audio,
device, battery or whole-app speed winner is inferred from this evidence.

## Official sources reviewed for targeted interfaces

- [Valhalla documentation](https://valhalla.github.io/valhalla/)
- [OSRM HTTP service documentation](https://project-osrm.org/docs/v26.6.1/http)
- [GraphHopper](https://github.com/graphhopper/graphhopper) and pinned 11.1
  `MapMatchingResource` API contract (blob `203235ac289cc3d17efcb366c92f5fe2fecc0a17`)
- [OsmAnd build documentation](https://osmand.net/docs/technical/build-osmand/)
- [Organic Maps repository](https://github.com/organicmaps/organicmaps)
- [BRouter repository](https://github.com/abrensch/brouter)
- [HERE navigation](https://docs.here.com/here-sdk/docs/android-navigation)
- [Mapbox Navigation SDK](https://docs.mapbox.com/android/navigation/guides/)
- [TomTom simulation provider](https://docs.tomtom.com/navigation/android/guides/advanced/simulation-location-provider)
- [openrouteservice backend documentation](https://giscience.github.io/openrouteservice/)

These sources guide adapter/provisioning work; their advertised capabilities do
not become pass results. The next external comparison work is to provision the
missing isolated runtimes/SDK harnesses and establish map/profile/interface parity.
