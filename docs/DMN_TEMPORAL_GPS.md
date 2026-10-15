# DMN temporal GPS matching experiment

This is the next isolated module after the initial single-fix GPS matcher.

The immutable temporal state keeps a set of plausible directed road edges. Each incoming GPS fix must pass the existing quality gate. A transition is allowed only if it remains on the same edge or proceeds along an explicit connected graph edge without a mapped prohibited turn. A unique supported continuation can resolve a formerly ambiguous position; two close same-direction roads remain ambiguous. Rejected speed spikes do not advance the state, and weak fixes reset confidence.

**Important limitations:** This is a deliberately conservative first *topology* experiment, not a production map matcher. It does not yet compute physically plausible traveled distance across multi-edge paths, independently verify legal UK traffic rules, or solve tunnels, stacked carriageways, slip-road transitions and full-drive GPS replays. It must never claim that one connected candidate means a physically reachable road without checking travel distance and elapsed time. Tests here use **synthetic GPS positions on a small artificial graph** as unit fixtures, not UK-road field evidence. Public UK replay, more realistic motion constraints, turn-restriction-aware transitions and competitor comparison remain outstanding. Continue to add discovered failure cases to the adaptive study.

A single-fix road matcher is retained as baseline. No production DriveMate changes or APK.
