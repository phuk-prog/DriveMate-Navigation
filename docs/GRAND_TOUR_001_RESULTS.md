# GRAND-TOUR-001 and the full DMN re-run (17 October 2026)

Grand Tour: [run 39074389754](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39074389754),
revision `5fe8000`; harness `benchmarks/grand_tour.py`, frozen `config/grandtour-prepared.json`.
One 23 km drive, same start/finish for every engine (Piccadilly one-way street -> A62 -> M62 ->
main roads -> moor lane above Newhey), 3 wrong turns, an M62 jam (+30 min), average phone GPS
with 3 drop-outs. Times on one neutral UK speed table. Map-derived truth.

| Category | Best | DMN |
|---|---|---|
| Main route (time) | DMN 22.5 min (best possible 22.3) | 1st of 4 valid; BRouter/OsmAnd off target, openrouteservice illegal |
| Road rules, 5 answers each | 0 broken: DMN, OSRM, Valhalla, GraphHopper, BRouter, OsmAnd | joint 1st; openrouteservice 5/5 illegal (Milnrow Interchange, junction=circular driven against its direction) |
| New route after wrong turns | DMN 3/3, 1.005x best | 1st of 7 |
| Traffic jam re-plan | DMN 15.0 min (best 14.8) | joint 1st with BRouter; Valhalla stayed in the jam (44.7 min) |
| GPS, fewest wrong roads | DMN 0.06% wrong, 78.6% right | 1st; OSRM 95.9% right / 1.45% wrong; Valhalla 13% UNRESOLVED (matched only up to the first drop-out) |
| Route calculation time (one machine) | OSRM 3.5 ms | 7th: 2.9 s |
| DMN live drive | 3/3 wrong turns noticed (3, 20, 15 s), jam avoided, arrived at the destination, 13/14 calls on time | whole journey PASS; 0.33 ms per fix; 2.4 GB memory |

Fresh re-run of every DMN test after the owner-approved changes (all passed):
Run A [39074415847](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39074415847): no-car roads DMN 44,
GraphHopper 44, openrouteservice 44, Valhalla 42, OSRM 41, BRouter 41, OsmAnd 40; one-way DMN 48, OSRM 47,
Valhalla 47, GraphHopper 47, OsmAnd 47, BRouter 44, openrouteservice 44 (1 wrong way).
B1 [39074417072](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39074417072): DMN 57/57, turns 36/36, roundabouts 21/21.
B2 [39074418420](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39074418420): lanes DMN 35/35, limits 61/61.
Run C [39074389768](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39074389768): right road 78%, 0 wrong; arrival 72/72; whole drive 70/72.
Run D [39074419707](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/39074419707): closures DMN 24/24 (GraphHopper, Valhalla,
openrouteservice, BRouter also 24 after the line-reader fix); damaged maps DMN 18/18 (was 16/18); bad requests 12/12;
speed 18 ms HTTP (5th of 6).
Other engines' higher scores in A and D come from the harness fixes (long-line reader, start-up watch).

Proposed next (engines programme stage 1): faster DMN routing on big maps (2.9 s), compact map in memory
(2.4 GB), fast map loading (13 s), one late call; harness: Valhalla long-trace matching.
