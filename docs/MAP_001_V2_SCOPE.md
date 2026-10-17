# MAP-001 v2 — context and access retest

Owner-approved **Category 1 only**, no navigation behaviour changes. The
first 120 cases remain recorded as MAP-001 v1. A new v2 run selects 20 real
OpenStreetMap ways in each of the same six UK area boxes. It freezes each
source response hash before evaluating. **The API source may have changed
between v1 and v2**, so the scores are not a paired same-input performance
improvement.

New: retain related from/to ways and via nodes in the source graph; include
outgoing source ways for only-turn restrictions; independently derive directed
edge access values from motorcar/access tags and barriers; compare applicable
mapped forbidden-turn pairs, directions and endpoints. Unsupported
conditional rules are **SAFE_WITHHELD**, not awarded green route legality.
Incomplete restrictions or missing source context remain NOT_JUDGED and must
not be counted as valid or incorrect DMN navigation.

The prior MAP-001 graph adapter audit remains outstanding. Internal graph
fidelity cannot be inferred from competitor route-return success; compare
only separately labelled public route-behaviour proxies when executable.
No Android app or other test category is started.
