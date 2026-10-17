# Run C: simulated drives (categories 3, 4, 6, 12, 13, 16, 19, 20)

Result of record: [run 39062533167](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39062533167),
revision `3d93a47`, all seven engines freshly run after the owner-approved DMN matcher change;
same simulated traces for every engine (checked by hash). Before the change:
[run 39061348011](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39061348011) at `657fa65`.
Harness `benchmarks/run_c.py`; drives frozen in `config/runc-prepared.json`. Real OSM clips,
simulated GPS only (1 fix/s, 3 m noise); map-derived truth. Each category scored separately.

24 journeys (run D, 1–2 km), each driven normally, with a 25 s GPS dropout plus a 60 m jump
fix, and with a wrong turn onto a public road. DMN runs live, fix by fix; OSRM, Valhalla and
GraphHopper match the whole trace at once (batch); all engines route the journey and from a
frozen point on the wrong road. "DMN v2" = DMN with `same_road_pieces` and `route_aware_access`.

| Category | DMN before | DMN v2 | Others |
|---|---|---|---|
| 3 right / wrong road | 37% / 0.07% | **78% / 0%** | OSRM 96/1.2, Valhalla 85/1.0, GraphHopper 81/1.0 |
| 4 after dropout, first 30 s | 42% / 0.14% | **77% / 0.28%**, back in 3 s (worst 5) | OSRM 91/5.8, Valhalla 44/14, GraphHopper 39/2.1 |
| 6 valid routes / length vs shortest | 24, 1.00 | (same routing) | Valhalla 24, 1.05; OSRM 23, 1.05; others 9–14 |
| 12 wrong turns spotted, delay | 23/24, 8 s, 1 lost, 1 false | **24/24, 3 s, 0 lost, 0 false** | from the wrong road: DMN 24 shortest; Valhalla 24 (1.30x); OSRM 23 (1.16x) |
| 13 turn calls on time / never | 308 / 54 | **451 / 5** | n/a |
| 16 arrival correct | 9/72 | **60/72**, none early | n/a |
| 20 whole drive passed | 8/72 | **57/72** | n/a |
| 19 per fix, memory | 18 ms, 1.2 MB | 18 ms, 1.2 MB | n/a |

"Wrong road" excludes the next piece of the same road a few metres out (counted apart for every
engine). Other engines' off-target routes are partly a harness reading limit (see run D).

Issue register: 12 drives still end without "arrived" (car stopped on a two-way road: DMN
stays unsure when stopped); 2 drives had a wrong position with v2; 1 call after the turn.
Proposed: arrival when stopped close to the destination after on-route progress; review the
2 wrong positions; make v2 the default after owner approval (approved to implement later).
