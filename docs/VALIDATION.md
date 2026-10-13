# Benchmark and validation protocol

## Four independent kinds of evidence

1. **Correctness oracle:** labelled synthetic fixtures and independently checked real-world junction permissions. Provider consensus is not an oracle.
2. **Equivalent routing inputs:** matching map version/hash, vehicle dimensions, legal restrictions, departure time, live traffic inputs and avoid/preferences; record all differences.
3. **Performance:** same hardware, repeatable warm/cold runs, route distance, p50/p95/p99 latency, memory, storage, battery, and reroute detection vs calculation time measured separately.
4. **Robustness:** GPS dropouts, parallel road ambiguity, tunnels, wrong turns, nested roundabouts, disconnected maps, offline transitions and version migrations.

## Initial comparison contract

`benchmarks/comparison.py` now rejects direct timing comparisons when graph SHA-256, profile SHA-256, scenario, device, environment, run temperature or evidence classification differ. It prints timings only, never safety or correctness results. Tests use **fabricated sample latency values** that are not observed speeds of any competitor.

For real benchmarks, first build a shared import pipeline and independently check the road topology. External providers with proprietary or different map versions must be explicitly marked **not directly comparable**. No external routing engines have been executed in this repository yet.

## Acceptance gates

- Never accept a known illegal turn, wrong-way route or unsupported lane/roundabout claim in a validated case.
- Learning may optimise estimated time and preference models but must not grant new road permissions.
- Each candidate change must pass fixture, property-style, integration, replay and regression gates appropriate to its risk.
- Report unresolved evidence as **unknown**, including unverified exits.
- Retain a clean rollback target, map version and evidence provenance for every accepted change.
- Real drives require consent, private storage, short retention and anonymised derived tests.

## Comparing the reference engines

All external engines listed in `benchmarks/reference-engines.json` are initially `not-integrated` or `access-and-terms-not-verified`; **do not report hypothetical scores as measured**. Providers using proprietary datasets or incompatible map snapshots may still be qualitative references but must not be presented as identical-data head-to-head results.

Do not query commercial services or download datasets without checking API terms, billing and redistribution rights. Never infer a legal junction movement from a competitor's suggested route alone.
