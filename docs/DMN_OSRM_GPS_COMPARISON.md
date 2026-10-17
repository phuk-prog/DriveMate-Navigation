# First external live GPS comparison: DMN vs OSRM Match

This is an **execution harness**, not a claim of measured external accuracy until an opt-in GitHub Actions run completes. It reuses the existing pinned, local OSRM 5.27.1 Docker/MLD routing reference workflow and precisely the same public Greater Manchester OSM extract, without paid APIs or consumer-app automation.

For up to 12 deterministic neighboring road pairs from public OSM, generate four artificial GNSS fixes per case. Feed the identical four lat/lon/timestamp observations to the DMN single-fix matcher, temporal matcher and OSRM's official `/match/v1/driving/` endpoint on `127.0.0.1:5000`.

Record OSRM endpoint `Ok` / `NoMatch`, returned tracepoints, snapped position proximity to the *generating GPS geometry* and request latency **separately** from DMN exact generating-edge confidence and withholding. These are **not equivalent correctness metrics**: OSRM may snap 5 m from the input on a parallel carriageway or an illegal/incorrect road, whereas DMN returns its own edge ID. Their access profiles, graph segmentation, matching algorithms, API overhead, and heading handling differ. Do NOT produce an out-of-ten comparative GPS ranking from these results. The OSM source is not independently surveyed GPS or signed legal truth.

## Actual execution gates

The single explicit opt-in `[osrm-reference-smoke]` workflow builds the OSRM Docker container, checks its existing routing endpoint and then calls the Match endpoint. An unavailable binary, invalid response, incomplete API protocol or failed run means **NOT_EXECUTED/FAILED**, not success. The artifact contains aggregates only and deletes the downloaded PBF/XML on exit. Version, SHA and source geometry remain pinned. The stage does not touch `phuk-prog/DriveMate` production, release APKs or use personal histories.

Further provider adapters: Valhalla trace matching and GraphHopper map matching, then each of the other ten reference families only if its exposed interface, terms and identical scenario inputs permit a real comparison. Routing-only provider tests remain routing-only.

## Initial gate checks

[GitHub Actions run 38752700333](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38752700333) **passed the research unit and contract suite** including locally mocked OSRM Match adapter protocol tests. Fake responses explicitly report **zero actual external reference engines executed**. A separate opt-in run is required to start the **actual** local OSRM 5.27.1 container and send the same map-generated GPS sequence to the real Match API. An HTTP error or no matching data must be reported as such, not replaced with unit results.

## Verified live external GPS results

[Actual live OSRM Match run 38752861279](https://github.com/phuk-prog/DriveMate-Navigation/actions/runs/38752861279) passed **193 unit/contract tests** and sent **12 real UK OSM-derived four-fix simulated scenarios** to OSRM 5.27.1 local `/match`. All 12 returned Match `Ok` responses, but only **40/48** tracepoints snapped within 20m and **8/48 were unmatched**. DMN single-fix selected the generating directed edge 6/12 and the older DMN temporal matcher selected 8/12, no confident wrong-road assignments, with 6 and 4 withheld respectively. OSRM returned snapped positions, not directly comparable DMN edge IDs, so do not award winner score. The artifact `dmn-vs-osrm-match-public-uk` has the aggregate metrics. See [two-family comparison report](DMN_EXTERNAL_GPS_FIRST_TWO.md).
