# Category 1 v3 — targeted source restriction diagnosis and graph metadata

Owner authorization: investigate Manchester ways 155729945 and 246124643;
extend working Valhalla candidate metadata adapter to directed edge/access and
restriction metadata. Not authorised: changing importer/runtime navigation,
scoring unsupported pair-level restrictions, or Category 2.

Frozen input: archived from run 38945058272, artifact 12065915414.
**Never refetch the six-area OSM snapshots for this diagnostic retest.**

## Data facts to test, not prejudge
- Inspect relation 7844443 from King Street way 155729945 via node
  9446154282 to Cross Street way 1334549231. The source marks
  vehicle:backward=no on King Street; Cross Street way 1334549231 is
  one-way towards the via node. The importer may accept a prohibited
  reverse edge when isolated, while relation import fails conservatively.
- Inspect relation 7844440 (no_u_turn on Cross Street 246124643)
  and relation 7844441 (no_straight_on to 1334549231) separately.
  Any shape-inapplicable movement must be labelled source-context
  ambiguity, not a lawful-turn PASS or a confirmed DMN unsafe routing.
- The source truth is OSM-derived, not independently verified UK signage.

## Valhalla applicability gate
Valhalla's verbose /locate supplies sampled directed edge attributes
including edge.forward, edge.access.car, edge_id, end_node,
start_restriction/end_restriction masks. Bounded 4-point requests use the
same frozen map. For each way, publish visible directional candidate facts
and explicit source disagreements separately. Mere candidate coverage does
not prove exhaustive edge import, same graph segmentation, lawful turn pair
restrictions or legally correct routing. Turn masks/complex flags are not
from-edge/to-edge forbidden-pair lists. Therefore full graph ranking stays
NOT_COMPARABLE unless a truly equivalent pair-level adapter exists.

Source agreement and comparisons may be scored only over matching
**observed** direction-access facts, with unknowns and access ambiguity
visible and independent road-law status unverified. Never score an absent
snapping candidate as a missing graph edge.

Keep original v1/v2/v3 evidence, failures and safety gates. No app work.
After the run, report, then stop for the owner.

## Follow-up on first extended adapter run

The initial adapter classified 13 candidate edges on `motor_vehicle=destination`
and `access=private` roads as suspected contradictions because it expected
`edge.access.car=false`. This comparison is INVALID: those tags express a
purpose-/permission-dependent rule, while Valhalla's car access bit is not a
complete authorization oracle. The historical artifact and its initial labels
remain preserved. The revised adapter reports these candidates as
`POLICY_CONTEXT_NOT_BINARY`, and records `destination_only` and `not_thru`
where exposed. It reruns over identical frozen v3 source and does not claim
Valhalla correctness or DMN navigation improvement based on a score adjustment.
