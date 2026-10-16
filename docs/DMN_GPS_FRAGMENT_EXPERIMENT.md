# DMN GPS segment-equivalence research variant — approval batch

An **explicitly opt-in** experiment named `experimental_adjacent_fragment_equivalence=True` was added to `DirectedRoadMatcher`. **The default matcher is unchanged** and the earlier 8/24 GPS-003 and 17/40 UK40 failures remain open.

It filters one clearly worse same-way candidate only if: both fragments are physically adjacent on a directed road, their OSM way ID and direction agree, no mapped turn restriction is crossed, the two headings differ by at most 8 degrees, movement and heading are available, accuracy is 5 m or better, the winning candidate projects within that reported accuracy, and the competing fragment is separated by more than twice accuracy and more than 4 m relative to the winner. Any other plausible candidate remains independently judged. The 12 m normal ambiguity threshold is unchanged.

**Safety/validity note:** a confidence report from a GPS receiver does not establish ground truth. The option is not safe for production without independent real-road testing and adversarial counterexamples; it is experimental, not enabled in the navigation or Android app. New synthetic positive and fail-closed controls execute in the GPS category. After GitHub tests, separately inspect the unchanged pinned Manchester map and compare original vs experimental GPS-003/UK40 outcomes, especially confident wrong-edge selections. Do not change frozen acceptance or claim a competitive GPS ranking.

Full comparable competitor retesting is mandatory before promoting an approved behavioural modification; the default engine path remains unaffected.
