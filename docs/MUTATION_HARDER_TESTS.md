# Next harder navigation validation stage

The previous seven-configuration scorecard tied on nine tiny synthetic routes. This stage introduces two **new candidate-only** evidence categories; it **does not inflate cross-engine scores**.

## Harder, explicitly verifiable route tests

- Eight **64-node asymmetric directed road graphs**, precommitted seed list, including disconnections, only/no multi-edge turn restrictions, vehicle-height restrictions and turn-cost patterns.
- Ten origin/destination/history/vehicle combinations per graph; three independent DriveMate search modes. **240 actual route executions**, with independently calculated minimum-cost or unreachable ground truth and path legality checks. Fresh held-out data must be added for future model improvements because once exposed these become known regression cases.

## Mutation-sensitivity gate

Seven intentionally damaged routing requests/data snapshots must be **detected** by the benchmark:
1. Disregard multi-edge via-way prohibition.
2. Disregard an only-turn restriction.
3. Ignore bridge height limitation.
4. Ignore vehicle weight limitation.
5. Lose turning penalty.
6. Fabricate a wrong-way road connection.
7. Discard the incoming-edge history needed to prevent a prohibited movement.

Each injected mutation is a controlled self-test, **not** an observed DriveMate production failure. The scorecard labels them `Deliberately injected safety faults detected`, and a missed mutation is a **benchmark validator** failure, not automatically a navigation bug.

## Completion requirement

Run the new mutation gate on a research branch and in the main research category comparison CI; all injected faults must be detected, all original baseline routes correct and all 240 holdout search executions legal and optimal. The main 7-engine head-to-head must remain fully green. Production `phuk-prog/DriveMate` is unaffected.

## Limits

No claim of real-device GPS accuracy, verified spiral lane mapping, traffic awareness or head-to-head complex UK junction superiority. Those require equivalent independently verifiable roads and traces for each rival.
