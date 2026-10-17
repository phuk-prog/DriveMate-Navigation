# DriveMate engines programme (owner-approved, 17 Oct 2026)

## Context
DMN showed the method works: build our own engine, freeze a test, run it against the free
alternatives on the same inputs, rank each category, approve improvements, re-test. The
owner wants the same for every part of DriveMate (own code wherever it can beat what
exists), with immersive navigation and rich map detail, ready for a possible Play Store
release. This plan lists every own engine to build, what it is tested against, and the
order to build them in, starting with DMN which is in progress.

## The method for every engine (same as DMN)
1. List the engine's jobs as numbered categories (like DMN's 21).
2. Freeze test cases on real UK data before any engine runs.
3. Run our engine and every applicable alternative on identical inputs (public research
   repo / GitHub Actions; app-code tests in the private repo; phone checks on the Pixel).
4. Rank each category separately; report the best engine and ours; issue list.
5. Owner approves improvements; implement; fresh re-run of everything affected.
Rules kept: no paid servers, no copying Google/TomTom/Apple data, credits for open data,
one test run when the owner asks, never force-push, private code stays private.

## Our engines (build order = logical dependency order)

| # | Our engine | Job | Tested against (yardsticks) |
|---|---|---|---|
| 1 | **DMN – Navigation** (in progress) | routes, road rules, rerouting, arrival, announcements' timing, route checking | OSRM, Valhalla, GraphHopper, openrouteservice, BRouter, OsmAnd |
| 2 | **DMG – GPS & position** | phone GPS filtering, "which road am I on", drop-outs, tunnels (Pixel dual-frequency GPS, motion sensors, car speed) | OSRM match, Valhalla Meili, GraphHopper map-matching, Barefoot, Kalman/particle filters, the app's GpsFilter/LocalRoadMatcher |
| 3 | **DMD – Map data** | weekly UK map build: roads, lanes, limits, signs, buildings+heights, house numbers, car parks, chargers, terrain | OSM raw, OpenMapTiles, Tilemaker, OS open data, Overture, Mapillary photos (accuracy check) |
| 4 | **DML – Lanes & junctions** | lane-level road model, which lanes to use, junction and roundabout layout | TomTom lanes, OSRM, OsmAnd, Valhalla; Mapillary photos as truth |
| 5 | **DMV – Voice & guidance** | UK Highway Code wording, timing by speed, landmarks, motorway exits, destination side | OSRM/Valhalla/OsmAnd instructions, Ferrostar; speech: Google TTS, Piper, eSpeak NG, RHVoice |
| 6 | **DMW – Warnings** | speed limits, cameras, average-speed zones, school zones, hazards on your route | OSM limits via GraphHopper/OsmAnd, TomTom limits, cameras file, OsmAnd warnings |
| 7 | **DMT – Traffic** | learned speeds from your drives, live feeds merged (TomTom, TfL, National Highways), closures, re-timing routes | TomTom traffic times, plain free feeds, no-traffic baseline |
| 8 | **DMS – Search** | offline and online places, postcodes, addresses, businesses, ranking | TomTom, Photon, Nominatim, postcodes.io, Pelias, OsmAnd/Organic Maps search |
| 9 | **DMR – Map drawing & immersive view** | own 3D "road ahead" view: lane-level road, 3D junction view with your lane, look-ahead camera, buildings, terrain; day/night style; overview map | MapLibre (current), Mapsforge, osmdroid, Tangram, OsmAnd/Organic Maps rendering; smoothness, battery, readability |
| 10 | **DMO – Offline maps & updates** | verified regional downloads, resumable, safe updates, rollback | OsmAnd/Organic Maps downloads; damaged-file and update tests (as run D) |
| 11 | **DMU – Driver screens & Android Auto** | at-a-glance screens, big buttons, safety rules, Android Auto | Google driver-distraction guidelines, OsmAnd/Organic Maps on Android Auto |
| 12 | **DMP – Platform** | settings, backup/restore, sign-in, privacy, battery/start-up, crash safety | DataStore vs Room/SQLite/files, Android Auto Backup; Play Store technical checks |

## Build order and why
1. **DMN** – finish now: report GRAND-TOUR-001 (run 39068256802); run the unit suite on the
   untested changes and fix; one push re-running every DMN test; then make DMN fast
   (spatial index for the matcher, 0.76 s/fix today; faster routing and map import) and
   add the planned test sets (long trips, more junctions/roundabouts/lanes/limits).
2. **DMG** – split DMN's GPS part into its own engine (everything else depends on knowing
   where the car is); add Pixel GNSS, sensors, car speed.
3. **DMD** – the map data all later engines read (lanes, signs, buildings, terrain).
4. **DML**, 5. **DMV**, 6. **DMW** – guidance quality, built on DMN + DMG + DMD.
7. **DMT** – traffic needs DMN routing and DMG speeds.
8. **DMS** – search, independent, can run in parallel with 4–7 if wanted.
9. **DMR** – immersive view needs DML lane model and DMD detail.
10. **DMO**, 11. **DMU**, 12. **DMP** – app-wide, then Play Store readiness (privacy policy,
    data-safety form, background location reason, "Data and licences" page, TomTom terms
    for a public app, target SDK, signed bundle, pre-launch report, closed test).
Each own engine is first written in the research repo (Python reference + frozen tests),
then in Kotlin for the phone with a parity test (same answers on every frozen case),
then put into the app behind a switch and compared on the emulator and the owner's Pixel.

## How it is checked
- Research engines: `python3 -m tools.category_test_runner --all`, the engine's GitHub
  workflow (pattern: `.github/workflows/grandtour.yml`, `runc.yml`, `rund.yml`), privacy
  guard before every push, results doc per test, `REGISTER.md` + `docs/HANDOVER.md`.
- Phone versions: parity test vs the Python reference, the app's
  `scripts/unified_preflight.py`, emulator robot drive, then Pixel/car (advisory).
