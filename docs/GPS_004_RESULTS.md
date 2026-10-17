# GPS-004 adjacent-fragment directed-progress safety baseline

**Completed 16 October 2026.** This is a ten-case analytical synthetic software
contract. It is not surveyed GNSS, current UK road law, lane truth or evidence of
phone performance. Expectations were frozen in
`benchmarks/fixtures/synthetic-gps-004.json` before any matcher change. The
successful bounded run is [38918971210](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38918971210)
at `ef4d454972685759064907210cb14d4818e61b77`; artifact
[12053612238](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38918971210/artifacts/12053612238).
Oracle SHA-256: `9110a9e0df1502180813aa7fcc05c80a9a391a569938c7d54c86b38d0d6c4da8`.

## Exact baseline result

| DMN execution | Passed | Failed | Score | Status |
|---|---:|---:|---:|---|
| Authoritative conservative matcher | 9/10 | 1 | 9.0/10 | Judged analytical baseline |
| Isolated adjacent-fragment research matcher | 10/10 | 0 | 10.0/10 | Diagnostic only; cannot guide |

These are two configurations of DMN, not two engine families. The research
configuration does not alter authoritative output. No calculation-latency rank
was declared because this category judges exact stateful outcomes, not speed.

The ten controls cover forward adjacent progress, remaining before a fragment
boundary, same-edge backward movement, a mapped prohibited continuation, a
different-way competitor, stationary and heading-missing boundary fixes, weak
accuracy, reverse-directed forward progress and a sharp bend. Both modes safely
withheld same-edge backward movement, competing roads, stationary/headingless
ambiguity and the sharp bend; both rejected confidence from weak accuracy and
did not select the mapped prohibited continuation.

The only failure is `reverse_directed_progress`: after a trusted reverse-edge
anchor, authoritative DMN returns `AMBIGUOUS` at the adjacent reverse fragment;
the isolated matcher returns expected edge `w:1:0:r`. This is a coverage failure,
not a confident wrong-road result. No default behavior or threshold changed.

An initial sharp-bend setup placed its second fix clearly on only one segment,
so both matchers correctly returned that segment. It could not test ambiguity.
Before final baseline execution, the case was corrected to the exact junction
with a 45-degree heading; both modes then withheld as required. This setup
correction did not change matcher behavior.

## External-family execution audit

No external engine was scored. OSRM, Valhalla, GraphHopper, openrouteservice and
BRouter expose the integrated batch snap/directions interfaces, not this identical
stateful two-fix authoritative/shadow contract. OsmAnd and Organic Maps lack the
required executable native lifecycle harness. HERE, Mapbox, TomTom and Google
lack configured permitted same-contract access; Waze has no permitted automation.
Each is `UNSUPPORTED` or `NOT_RUN`, never a zero or inferred pass. Static routing
scores are not substituted for GPS lifecycle execution.

## Issue and review gate

A narrow proposed improvement is to let the authoritative temporal matcher treat
a high-quality, direction-consistent immediate reverse-ID fragment exactly like
the already isolated forward-ID fragment rule, while retaining the prohibited,
parallel-road, backward-progress, weak/stationary and sharp-bend controls. Before
any such behavioral change, the owner review gate applies. An approved change
must freshly rerun all ten cases, the full GPS safety suite, frozen GPS-003/UK40,
and every then-applicable external engine on a genuinely equivalent contract.
The UK default remains 17 correct / 0 confidently wrong / 23 withheld; the
research matcher remains 22 / 0 / 18. Promotion stays blocked.
