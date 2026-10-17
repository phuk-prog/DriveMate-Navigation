# DMN GPS — three additional real UK road extracts

The matched public OSM source is the **same historical 2026-09-01 pinned
Greater Manchester archive**, reused in one GitHub Actions job and SHA-256
verified before use. This region comparison selects actual mapped roads
from **Salford, Stockport and Oldham**, each with separate per-case
source-map matching and backward-progress results for authoritative DMN and
the opt-in research matcher. Cases are drawn from multiple independently
identified OSM ways and include same-way and cross-way transitions.

These are **real OSM map geometry** tests, not synthetic road networks.
However their generating map edge is only a *provisional reference*:
current signage/road law, actual GNSS error and surveyed vehicle truth
remain unverified. Any confidently wrong generating-edge choice from the
research matcher fails the diagnostic, without hiding failures. The usual
GPS-003, GPS-004, UK40 and 21-category tests continue unchanged; neither
matcher is disabled or promoted.
