# DriveMate navigation stress-testing register

**Separate research repository only. Production DriveMate Android code is untouched.** The programme is test-first: reproduce failure, make narrowly scoped correction, rerun the focused category, the complete regression suite and compatible reference engines. Never treat a synthetic pass as proof of physical-road safety.

This register contains **36 categories and 216 named challenge types**. It is a **planned test inventory**, **not 216 executed tests**. The five executed stress sweeps in `benchmarks/navigation_adversarial.py` and `benchmarks/navigation_adversarial_routes.py` generate independent candidate scenarios and save real outcomes in `results/navigation_adversarial/report.json`.

## Rules

1. Every case has independently authored geometry, ground truth, legal-turn expectation and a reproducible deterministic seed or replay identifier.
2. Category runs combine normal, difficult, extreme and conflicting faults, retaining per-case outcomes rather than hiding failures in averages.
3. Distinguish **pass, fail, unsupported, uncertain, unavailable and not tested**; never silently mark an unsupported lane or ambiguous GPS position as correct.
4. Treat safety/legality as hard gates; rank latency and resource use only for comparable valid results.
5. Use genuinely equivalent test geometry and inputs for outside engines. APIs do not automatically represent their entire consumer navigator.
6. Document map version, profile, road restrictions, engine build, hardware and evidence provenance for any competitor comparison.
7. Keep new held-out scenarios that are not used for optimisation. Validate against them before declaring an improvement.
8. Physical GPS accuracy, spiral lane continuity, voice delivery, battery, real congestion and commercial app ranking need verified external evidence; none is implied by the synthetic tests.

## Detailed category matrix

| ID | Category | Six distinct challenges | State |
|---|---|---|---|
| GPS01 | Straight-road positioning | Bias; along-track jitter; cross-track drift; high speed; slow creep; false speed zero | partial |
| GPS02 | Corners and bends | Hairpins; S bends; curve entry; curve exit; heading lag; corner GPS jumps | pending |
| GPS03 | Parallel or layered roads | Slip lanes; service roads; motorway parallel; dual carriageway; bridge overlap; stacked tunnel | pending |
| GPS04 | GPS interruption | 3s; 10s; 30s; 60s; 120s; 300s | pending |
| GPS05 | GPS sensor faults | Inaccurate heading; wrong speed; stale fix; future fix; bad accuracy; out-of-order time | partial |
| GPS06 | GPS reacquisition | Same road; skipped road; wrong direction; missing history; multiple candidates; unreachable island | partial |
| RTE01 | Route minimum-cost oracle | Directed graph; nonuniform speeds; 100 random graphs; dijkstra; A-star; ALT | partial |
| RTE02 | Legal route selection | One-way; only-turn; no-left-turn; no-right-turn; multi-road ban; no-U-turn | pending |
| RTE03 | Time-dependent routing | Rush-hour bans; school hours; weekend restrictions; minute-boundary crossing; expiry; time-zone rules | pending |
| RTE04 | Route topology | Dead end; loop; isolated region; missing link; parallel links; grade separation | pending |
| RTE05 | Quality and alternatives | Time versus distance; rural shortcut; congestion; unneeded turns; route preferences; detour stability | pending |
| RTE06 | Large routing workloads | 10k roads; 100k roads; million roads; cold cache; warm cache; concurrent requests | pending |
| JNC01 | Ordinary junctions | T junction; crossroads; Y fork; staggered; offset approach; closely successive turns | pending |
| JNC02 | Multi-arm junctions | Five arm; six arm; seven arm; eight arm; nine arm; twelve arm | partial |
| JNC03 | Complex interchanges | Cloverleaf; collector road; motorway fork; lane drop; short weave; braided slip | pending |
| JNC04 | Turn legality | Banned entry; banned U-turn; time restriction; access unknown; only-turn; turn after via-way | partial |
| JNC05 | Road-level separation | Overpass; underpass; stacked interchange; false graph connection; service level; tunnel entrance | pending |
| RND01 | Mini roundabouts | Three arm; four arm; double mini; tight radius; offset entry; adjacent exit | pending |
| RND02 | Simple clockwise rings | First exit; last exit; three-arm ring; twelve-arm ring; varying radius; different arrival bearings | partial |
| RND03 | Multi-lane rings | Two lanes; three lanes; four lanes; multi-lane exit; lane drop; lane gain | pending |
| RND04 | Spiral marked rings | Concentric spiral; partial spiral; full spiral; forced lane continuation; lane-specific exit; unknown marking | pending |
| RND05 | Signalised and bypass rings | Traffic lights; multiple stop lines; bypass slip; connected circles; motorway entry; segregated exit | pending |
| RND06 | Ambiguous roundabout evidence | Non-simple topology; missing entry; unknown exit; repeated lap; missed exit; unverified lane | partial |
| LAN01 | Lane evidence | Left arrow; right arrow; shared arrow; missing tag; conflicting tags; unknown lane count | pending |
| LAN02 | Lane continuity | Stay-in-lane link; mandatory change; lane split; lane merge; weaving; solid line | pending |
| LAN03 | Unsafe lane claims | Ambiguous fork; unverified connectivity; stale lane data; bus lane; missing geometry; false exact-lane GPS | pending |
| RR01 | Wrong-turn recognition | Missed left; missed right; wrong fork; early turn; motorway missed exit; roundabout wrong exit | pending |
| RR02 | Reroute correctness | Legal recovery; avoid U-turn; no-route response; route rejoin; detour; stale destination | pending |
| RR03 | Reroute performance | Detection latency; computation latency; usable guidance latency; false reroute; oscillation; stress burst | pending |
| RR04 | Combined wrong turns | Tunnel plus missed exit; bad GPS plus closure; three missed turns; low-speed ambiguity; motorway diversion; repeated replan | pending |
| INS01 | Instruction correctness | Keep versus turn; exit numbering; lane wording; cancel old text; missing road name; duplicate suppression | pending |
| INS02 | Instruction timing | 10 mph; 30 mph; 70 mph; stopped traffic; two rapid turns; GPS blackout | pending |
| END01 | Full journey replays | Urban; rural; motorway; mixed; interconnected circles; offline | pending |
| END02 | Arrivals and recovery | Correct arrival; wrong-side arrival; parallel destination; restart; outage before arrival; stale arrival | pending |
| SYS01 | Device and runtime reliability | CPU; memory; battery; cold start; background navigation; thermal throttling | pending |
| SYS02 | Data and security resilience | Map update; stale road closure; corrupt cache; region seam; privacy; interrupted download | pending |

## Current evidence and next coverage

The first batch exercises **100 generated directed route networks (300 algorithm-mode route executions); 325 numbered roundabout routes across 3–12 segment rings and five radii; 50 unsafe non-simple ring checks; 195 allowed and 30 banned multi-arm junction movements; 1,008 corrupted GPS observations plus 1,008 healthy-fix controls; and 72 interrupted GPS recovery journeys**. These are synthetic measurements, and only the listed subtypes have coverage.

All other rows and unimplemented subtypes stay pending. The immediate next work is realistic marked spiral and double roundabout geometry with independent lawful lane oracles, multi-fault whole-drive replays, expanded cyclic graph restrictions, and equivalent competitor engine traces. Production APK or consumer-app conclusions are outside this first batch.
