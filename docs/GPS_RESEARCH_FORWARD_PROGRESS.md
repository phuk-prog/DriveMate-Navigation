# DMN — bounded directed-progress GPS experiment

Owner-approved research-only improvement in the existing opt-in adjacency
matcher. The default matcher and every other DMN navigation category remain
unchanged and available.

When the previous directed road is a fresh trusted anchor, the current fix is
moving with good accuracy and heading, and **only two** locally plausible
time-reachable fragments are present, DMN may prefer the **immediate forward
successor** if it is a continuous segment of the same mapped way/direction,
the mapped turn is permitted, the new segment clearly wins projection/heading,
the vehicle progressed beyond the combined uncertainty and the observation
lies at least 2 metres inside the successor. Any ambiguity about branching,
different road, prohibited turn, reversal, stale fix, stationary state or
heading quality retains the original fail-closed outcome.

The new logic runs **only with experimental_adjacent_fragment_equivalence=True**.
The default DMN route/matching/GPS guidance remains unchanged. The research
branch is not a production navigation engine. Synthetic unit controls are
analytical only and do not count as verified UK driving roads.

The existing 10-case GPS-004 baseline, 24-stream GPS-003 and 40 UK
map-derived trajectories are mandatory before/after gates. The historical
test oracle and earlier evidence must not be overwritten. Independent road
truth, additional real-UK geographic diversity, and applicable external engine
comparisons remain required before considering any default promotion.
