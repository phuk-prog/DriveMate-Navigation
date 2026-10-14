# Bounded GPS road matching

Original local research implementation. GitHub, workflows and the Android app
are unchanged. No external map-matching code, device fixes or personal journeys
were imported. This stage connects synthetic raw fixes to the previously tested
trusted-road journey, rerouting, junction and roundabout engines.

## Behaviour

`gps.matching.Fix` carries geographic coordinates, UTC capture time, reported
horizontal accuracy, optional speed, bearing and bearing uncertainty. `Matcher`
indexes complete supplied directed geometry once in 50 m cells. Projection yields
millionth-road positions; it never identifies an exact lane. There is no planned
route attraction that could force a fix onto the intended road.

Only accepted fixes enter bounded road history. Accurate headings, or sufficiently
clear recent movement, disambiguate opposing directions. Small backwards noise
clamps progress. Hysteresis is confined to shared endpoints and stationary reverse
representations of the same segment; parallel roads retain explicit ambiguity.
Physical inaccessible and disconnected roads participate in ambiguity checks, so
filtering legality cannot falsely snap a forbidden observation onto another road.

Known directed-road access and static no/only/multi-road turn restrictions remain
enforced. Conditional transitions must be legal throughout the uncertain crossing
interval, including any minute boundary. Unknown access is allowed and flagged.
Missing lane hints neither close a road nor prevent matching.

`GpsJourney.observe(fix, receipt_epoch)` previews a match, passes accepted contiguous
progress to the journey, then commits matching history. Backend failures and
rejected fixes do not advance matching history. A rejected fix retains the explicitly
named `trusted_snapshot` but suppresses current guidance. `junctions(now)` and
`roundabouts(now)` require a current receipt clock and also suppress guidance after
three seconds without a fresh accepted fix. Arrival is withheld if the accuracy
interval straddles the destination. Terminal journeys do not continue advancing.

## Explicit prototype bounds

| Check | Policy |
| --- | --- |
| Capture age | At most 3 seconds; no future fixes |
| Reported accuracy | At most 35 m |
| Observed speed / motion bound | At most 80 m/s, with reported positional uncertainty allowance |
| Usable supplied heading | Speed at least 2 m/s; heading uncertainty at most 30 degrees |
| Heading compatibility | Within 60 degrees of directed geometry |
| Search radius | 8–30 m, based on reported accuracy |
| Ambiguity margin | At least 3 m, or half reported accuracy |
| Accepted-fix gap | At most 10 seconds; larger gaps require reacquisition |
| Geometry | Complete; below 80 degrees latitude; within 20 km of anchor; segments 0.01–2,000 m |
| Resource bounds | 30,000 roads; 200,000 index entries; 512 nearby candidates |

These are uncalibrated research policy thresholds, not measured device accuracy
or safety guarantees. The local planar geometry model is explicitly bounded.
Unsupported map geometry fails setup; it is not stored as a road prohibition.
Resource exhaustion is reported as incomplete evidence, not no legal road.

## Verified evidence

- 285 full-suite test methods passed, including 47 new GPS tests.
- 4,800 constructed-fraction oracle cases passed: four latitudes, twelve road
  angles, five fractions, five perpendicular errors, two accuracy values and both
  directions. The oracle uses fixture fractions, not another matcher implementation.
- Four complete GPS-to-roundabout journey replays passed: 54 matched observations
  and 46 deliberately rejected poor fixes. Original entry exit numbers remained
  stable, guidance cleared after exiting, and each journey arrived.
- Tests cover one-way rejection, known access/turn bans, unknown access, ambiguous
  parallel service roads, disconnected crossing geometry, stationary drift,
  backwards travel, 100/500 m jumps, stale and out-of-order input, GPS silence,
  bounded candidate exhaustion, timed crossing restrictions, atomic backend
  failure and uncertain destination arrival.
- Source compilation passed. Privacy scan and exact source hashes are recorded
  beside the full-suite log and synthetic evidence.

Evidence: `results/gps_full_suite.log`, `results/gps_expanded_validation.json`,
`results/gps_test_register.csv`, `results/gps_source_manifest.json`, and
`results/gps_source_privacy.json`. Projection cases and test methods are separate
counts; they must not be added together as a misleading test-method total.

No fresh external GPS matcher was run. Earlier actual GraphHopper routing and
junction comparisons remain historical evidence; they are not a competitor GPS
accuracy score or a live controller comparison. No winner or real-road readiness
claim is established by these synthetic tests.

## Remaining work

GPS loss and recovery is next: safe reacquisition after tunnels, long gaps and
skipped roads remains deliberately unsupported. Then instruction timing and wider
end-to-end scenarios. Exact destination-endpoint confirmation, road-level elevation
disambiguation, multi-fix probabilistic matching, realistic sensor error calibration,
external matcher comparison and device/real-road validation remain pending.
Static lane and conditional-routing limitations from earlier stages still apply.

## Reproduce

```sh
python3 -m unittest discover -s tests -p test_gps_matching.py -v
python3 -m unittest discover -s tests -v
python3 -m benchmarks.gps_validation
```

The expanded results in this checkpoint were exported from the full-suite run,
reusing its completed sweep and journey observations rather than repeating them.
