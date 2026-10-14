# Instruction generation and timing

Original local navigation research. Android, GitHub, workflows and APKs are
unchanged. This stage generates testable display/speech events; it does not play
audio, call a speech provider, change Bluetooth behaviour or establish device or
real-road readiness. Earlier actual GraphHopper routing/junction comparisons are
historical and do not score this instruction scheduler against another system.

## Implemented behaviour

`guidance.timing.Planner` reads the consensus GPS/recovery route and computes
remaining distance along supplied directed geometry. It converts verified
junction directions into instruction targets, handles simple roundabout entry
and exit separately, and skips ordinary shape segments. Internal roundabout
tangents never become guessed turns or lane instructions. Unknown first manoeuvres
block later speech rather than letting the scheduler skip to the next junction.

Only current routing and guidance shared by the retained history variants can
produce events. Roundabout ordinals require the existing verified entry/exit
context. Unknown or disputed entry numbers remain withheld; a known planned exit
can still receive a generic instruction without an invented ordinal. Complex
roundabout topologies remain unsupported. Missing or unverified lane hints do not
close roads or block an otherwise known direction. Indicated lanes are evidence
metadata, never exact vehicle-lane identification or spoken lane-change commands.

`InstructionScheduler` offers prepare, approach and action phases based on distance
and reported speed. Close successive manoeuvres are linked in advance. Immediate
phase text stays focused on the first junction. Remaining metres are internal;
one formatter creates UK yards/miles text used identically for display and pending
speech. A zero-distance formatter result is zero yards; near-mile rounding is
explicitly tested.

## Delivery contract

1. Feed the original `RecoveringGpsJourney` with fixes and receipt time.
2. Call `scheduler.poll(now)` to obtain the current instruction and optional
   pending event. Repeated peeks are idempotent.
3. Immediately before starting delivery, call
   `scheduler.acknowledge(event.event_id, now)`. Deliver only if it returns true.
   An adapter must not play an old event merely because it was once returned.

Acknowledgement re-evaluates the current route, GPS freshness, text and timing.
Expired, changed, stale or already consumed identifiers fail. Queues clear on
GPS loss, bad fixes, uncertainty, no route, changed manoeuvres, changed distance
wording and passed turns. Later phases cannot replay an earlier delivered phase.
A new observed visit to the same junction has a distinct occurrence. Reroutes
cancel the old instruction and generate the current route's target.

Checkpoints preserve bounded delivered-stage state for one explicit trip key,
with schema/value checks. Pending speech is never restored. Checkpoints contain
bounded instruction state and road identifiers, not raw fixes or coordinate
records; they are returned to the caller and never automatically written or
uploaded. An eventual app must treat this navigation state as private. Arrival
has a once-only, freshness-checked event and shared display text.

## Explicit research policy

| Policy | Setting |
| --- | --- |
| Preparation distance | 20 seconds at reported speed, bounded to 100–800 m |
| Approach distance | 8 seconds, bounded to 35–300 m |
| Action distance | 3 seconds, bounded to 12–100 m |
| Reported speed below 2 m/s | Distant preparation only |
| Unknown speed | Use 80 m/s bound to assess speech feasibility; withhold unsafe speech |
| Close following manoeuvre | Gap at most 35 m or six seconds at reported speed |
| Forecast uncertainty allowance | Reported accuracy plus speed times fix age |
| Speech completion allowance | 2 seconds, plus 1.5 seconds for a linked manoeuvre |
| Event expiry | Before lower-bound arrival minus speech allowance, and within 3-second GPS freshness |
| Route instruction bound | 512 remaining road segments |
| State size | One active target, three delivered phases, one queued event |

These thresholds and speech allowances are not calibrated sensor accuracy or
measured speech duration guarantees. Late approaches with insufficient completion
time produce no catch-up speech. A position interval straddling the junction
suppresses the instruction. The actual audio adapter must still cancel active
speech when appropriate; speech that has already played cannot be withdrawn by
this event engine.

## Verified evidence

| Evidence | Result |
| --- | --- |
| Full regression suite | 376 test methods passed |
| New instruction test methods | 42 passed |
| Adversarial instruction streams | 2,304 cases; zero failures |
| Stream frames checked | 17,856 |
| Accepted synthetic delivery acknowledgements | 4,096 |
| Full roundabout instruction replay with GPS loss | Verified entry, unknown recovered ordinal withheld, observed arrival passed |
| Existing GPS projection sweep | 4,800 cases passed in full regression |
| Existing harder recovery sweep | 1,536 cases passed in full regression |
| Existing independent physical-history oracle | 216 cases passed in full regression |
| Source compilation | Passed |

The new sweep varies two latitudes, eight speed values, three successive-turn
gaps, four fault patterns, three delivery/restart modes, lane evidence and access
uncertainty. It uses the actual local matcher/recovery/journey/scheduler code.
Its outcome checks include freshness, consensus, current route target, once-only
delivery, phase order, cancellation during faults and clearing passed turns.
Expected turn direction comes from authored fixture topology. Some reported speed
values intentionally disagree with synthetic progress to test conservative fallback;
this is not a validated vehicle/sensor physics simulator.

Targeted cases also exercise actual wrong-turn rerouting, no-route cancellation,
legal versus prohibited U-turns, repeat visits to the same junction, checkpoint
corruption, unknown speed, lane fallback, near-mile rounding, delayed arrival,
timing windows and suppression of an unverified first manoeuvre. One explicitly
stubbed unit test injects unknown manoeuvre metadata; it is not an external engine
or real drive comparison.

Evidence: `results/instruction_full_suite.log`,
`results/instruction_expanded_validation.json`, `results/instruction_test_register.csv`,
`results/instruction_source_manifest.json`, `results/instruction_source_privacy.json`.
Parameterized cases and test methods are separate counts. Expanded evidence was
exported from the full-suite run without repeating the same benchmark afterward.

## Remaining work

The three core GPS simulation prerequisites are now implemented in bounded form:
matching, loss/recovery and instruction timing. Broader whole-drive scenario checks
can proceed now. Real location datasets, realistic sensor error calibration, exact
destination-endpoint confirmation, complex junctions/roundabouts, traffic and
offline behaviour remain separate work. Audio/TTS completion and cancellation,
Android lifecycle, Bluetooth and on-device/real-road validation are still pending.
No competitor winner, synthetic speed ranking or road safety guarantee is inferred.

```sh
python3 -m unittest discover -s tests -p test_instruction_timing.py -v
python3 -m unittest discover -s tests -v
python3 -m benchmarks.instruction_validation
```
