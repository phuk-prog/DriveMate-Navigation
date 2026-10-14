# GPS-01.01 — hard straight-road position-stability batch

Research-only GPS matching improvement. No changes to the Android DriveMate app, third-party navigation code, personal journeys or proprietary routes.

## Reproduced defect, then retested

- Before correction: 1,104 failures across 1,152 repeated stationary GPS-noise observations in the new independent synthetic sweep. Spurious along-road progress was possible with reported speed zero; some backward noise was rejected despite being inside measurement uncertainty.
- Correction: On the **same** road, when reported speed is at most 0.5 m/s and observed motion is within the combined stated horizontal uncertainty, preserve the previously trusted fractional position. Other road selection, legal transition checks, and nonzero-speed progress retain their earlier rules.
- Focused retest: 1,152/1,152 hard stationarity observations passed, plus all separate moving progress controls.
- Wider suite: 4,800/4,800 existing geometric GPS projection observations passed; all 4 complete synthetic roundabout GPS journeys passed; Python regression 394 tests passed (one existing skipped case may be present; see workflow logs). Privacy scan passed.
- Focused proof: [baseline failure](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38624553251), [passing correction and regressions](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38624814839).

## Limits

This is a synthetic position-stability improvement, not a comparison of live mobile GPS products. It does not prove device sensor quality, physically stopped status, real lane detection, GPS-recovery quality or competitor ranking. Real-world slow-creep/incorrect-speed telemetry must be verified before claiming production readiness. The new hard test fixtures are fixed synthetic straight roads at four latitudes, twelve bearings, three horizontal accuracy values and eight correlated sequential jitter observations, plus motion controls.

Do not combine synthetic case counts with test-method counts. Only test another category after a failing repro has been fixed, held-out test coverage assessed, and the wider regression set rechecked.
