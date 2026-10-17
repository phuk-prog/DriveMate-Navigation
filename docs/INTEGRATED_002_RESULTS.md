# INTEGRATED-002: roundabout and GPS-confidence integration

DMN passes **3/3** synthetic engine-only integration cases at source
`c49c733`. The cohort combines the JUNCTION-001 graph, actual routing and
roundabout semantics with GPS quality, instruction gating and arrival gating.
It is not real-road, physical-GNSS, Android or app evidence.

| Case | Required integrated result | Verdict |
|---|---|---:|
| roundabout-exit-three | Exact legal path, third-exit maneuver, valid fix and `APPROACH` at the declared 50 m/10 m/s/5 s boundary | PASS |
| weak-gps-withholds | 60 m accuracy is `UNCERTAIN`; guidance and arrival remain withheld | PASS |
| stale-gps-rejected | 11-second-old fix is rejected; guidance is withheld and arrival is rejected | PASS |

The original oracle commit `c6e538b` omitted the distance/speed/lead inputs for
the first instruction. The first harness selected 60 m and DMN correctly returned
`WAIT`, producing **2/3**. That setup failure is preserved in
[`integrated002-first-setup-failure-20261017.json`](../references/integrated002-first-setup-failure-20261017.json).
The contract was completed with explicit 50 m, 10 m/s and five-second values;
the expected `APPROACH` outcome was not changed. This is harness setup recovery,
not a navigation-policy fix.

Final oracle SHA-256 is
`c2d132f9a502a93e306b734e687bf6c7bc4d4e74332b97c728f3cec7cbd9e30a`;
map SHA-256 is
`8b9d409865dd0b272456c2b99575c8dd29d3459602db7016377889b9b00ab465`.
[Exact final events](../references/integrated002-dmn-20261017.json) and the
[all-family interface audit](../references/integrated002-scorecard-20261017.json)
are retained.

DMN's isolated conformance score is 10/10. The twelve external families remain
unranked because their integrated interfaces cannot execute the same roundabout,
GPS-quality, live instruction and arrival-state contract. No mocked or historical
junction result is substituted. Single local whole-case timings are diagnostic
only; no speed ranking is assigned.

No DMN behavior changed. Multi-ring/spiral roundabouts, live GPS, voice timing,
lane choice, real UK legality and Android lifecycle remain unverified. The UK
17 correct / 0 confidently wrong / 23 withheld promotion block remains open.
