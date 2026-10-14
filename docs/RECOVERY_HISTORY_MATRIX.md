# Recovery across unobserved forks

This candidate-only matrix executes the research recovery controller on 64
synthetic fork scenarios: four coordinate layouts, four restriction/budget modes
and four elapsed times (6, 32, 300 and 301 seconds since the last trusted fix).
Two coordinate layouts are held out, giving 32 discovery and 32 holdout cases.
The topology is shared; held-out coordinates do not prove unseen-topology coverage.

The authored graph has exactly two acyclic directed paths from the last observed
road to the recovery road. An unseen past turn ban does not physically remove
either path. When one possible suffix prohibits the next turn, the controller must
retain the uncertainty and withhold guidance. A history budget of one cannot
justify publishing only one of the two possibilities. The 300-second bound is a
configured research limit, not a calibrated physical sensor guarantee.

Expected behaviours are authored from that topology and limit, independently of
the controller's route search: 12 recoveries with common guidance, 24 recoveries
with uncertain history and suppressed guidance, 12 refusals for incomplete history
enumeration, and 16 refusals beyond the recovery time limit. No silence or pending
confirmation may advance the trusted snapshot. Five corrupt-result judge controls
check that unsafe guidance, lost history, rejected-fix advancement and invented
history certainty are detected, including substitution of a branch without changing
the history count. These controls do not mutate a vendor binary.

The existing regression runner and category execution produce case-level evidence
under `history_matrix` in `results/gps_recovery_expanded.json`. Native execution is
required; source metadata and judge-control tests alone are not execution proof.
This matrix neither changes navigation behaviour nor ranks competitor controllers.
Real-device traces, uncertain lane geometry and recorded driving remain untested.
