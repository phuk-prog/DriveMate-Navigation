# Owner decisions — DMN comparison and improvement programme

> **22 decision topics; questions 1, 2 and 3 recorded.** On 15 October the owner approved **more than ten references** and chose **option B for commercial providers: permitted free comparisons first; ask for approval before any paid test**. Listing a provider never authorises paid API usage, new accounts, data extraction, or otherwise prohibited access. The exact reference roster and remaining choices are open. Existing agreements appear below, so we don't ask them again. Ask these *one at a time in conversation* if that is easier; the numbered list remains reviewable in GitHub. Suggested defaults are **recommendations only**, not commitments.

## Already agreed (do not re-ask)

- DMN = DriveMate Navigation; no second standalone app.
- Maximise eventual **DriveMate app** quality by making the navigation engine the leading programme. Improve, replace, or rebuild supporting map/data/routing/software only when evidence justifies it, including downstream dependencies; never compromise solely to fit present app constraints.
- Use real UK road-map geometry as primary evidence and synthetic fault cases as secondary; test on GitHub, not the user's phone; never release an APK or modify app production during R&D.
- Keep research evidence and failures, compare engines honestly, avoid subscriptions/royalties/permission restrictions and personal traces in a public repository.
- Existing DriveMate navigation engine remains a control on the separate integration-testing branch, not DMN's engineering constraint.

## Questions (the recommendation follows the question, not vice versa)

**1. Minimum number of external references — OWNER DECISION PARTLY RECORDED (15 October 2026).** **At least ten; more than ten permitted.** Current review portfolio: 12 proposed families (the original ten, plus Google Maps and Waze). They are **proposed**, not all verified or runnable. Specific replacements/additions may still change after accessibility, rights and cost checks. OSRM CH/MLD remain one family. *No further question is needed about allowing over ten.*

**2. Commercial references — OWNER DECISION RECORDED (15 October 2026): B.** Use legal/permitted free comparison options first; **ask the owner before any paid test or paid service usage**. No spend, provider credentials, account connection, new subscription, restricted API access, or Waze automated collection is authorised by this choice. Reference systems that cannot be accessed under permitted conditions remain untested.

**3. Non-equivalent or unavailable engines — OWNER DECISION RECORDED (15 October 2026): A + C.** Keep unavailable or non-equivalently executable engines in the comparison inventory as **Not Tested** for the affected categories. When legally permitted, record their outputs separately as **observational / not directly comparable**, with source, date, limits and provenance. Do not give either class a numeric score or head-to-head rank, and do not automatically replace a reference.

**4. Which UK regions first?** A. Greater Manchester/Wigan and named difficult roundabouts first; B. balanced England/Scotland/Wales/Northern Ireland from day one; C. other order. *Recommended: A followed by structured nationwide held-out samples.*

**5. What vehicle profile must be correct first?** A. ordinary UK passenger car; B. car + van/caravan dimension and weight constraints immediately; C. all vehicle classes. *Recommended: A with explicit exceptions untested, then add vehicle variants.*

**6. Which car-routing policies matter most?** Pick and rank fastest legal, shortest legal, avoid motorways, avoid tolls/charges, low-emission zones, fuel efficiency, traffic, and multi-stop. *Recommended: safety and accurate fastest legal route first; others clearly separate.*

**7. How do we decide whether a turn is legally permitted?** A. Official legal orders/signage where available plus dated mapped evidence; B. OSM only; C. agreement among providers. *Recommended: A, with conflicts unresolved; never treat B or C as guaranteed on-road truth.*

**8. Should time-dependent rules be mandatory in early gates?** Include school streets, bus gates, timed turns, temporary closures, restricted vehicles and public-holiday restrictions? *Recommended: yes for published known restrictions, but separate permanent rules from live/uncertain closures.*

**9. How many real-road scenarios are required per category before a category can earn a rank?** E.g. 100, 250, 500 or adaptive coverage until difficult junction/road types are represented. *Recommended: coverage-stratified, minimum 100 meaningful judged cases per applicable major category, subject to available independent truth; report all unjudged.*

**10. How do you want the test scenarios split?** A. random real-road sample; B. designed difficult/junction cases; C. both with development vs secret/held-out sets. *Recommended: C, with rare legal and GPS edge cases oversampled.*

**11. How many repeated measurements for performance?** A. 10; B. 30; C. 100 warm requests per case, plus cold-start and p95/p99. *Recommended: B as default, scale up for close results; record host identity.*

**12. Should all available references (ten or more) face identical category checklists even if they cannot expose a feature?** A. yes, explicitly unsupported/not-tested; B. test only common functions and omit others. *Recommended: A for transparency; rank on matched judged coverage only.*

**13. How should competing navigation outputs be judged?** A. independently checked map/legal evidence first; B. most competitors agreeing; C. a manually signed reference answer. *Recommended: A with C where independently verified; disagreement is an investigation target, not truth.*

**14. Do you want a global ranking now or only category-specific rankings until we have complete evidence?** A. overall ranking regardless of missing categories; B. category ranks and an overall **unresolved** state until coverage is comparable. *Recommended: B.*

**15. What should outweigh route-computation speed?** Rank these: illegal directions, wrong-road GPS matching, wrong junction exit/lane, missed reroute, missed arrival, wrong ETA, response latency, memory/battery. *Recommended: legality and wrong-road/incorrect instruction as hard blockers; speed evaluated only after acceptable correctness.*

**16. What GPS-replay sources are allowed?** A. simulated GPS over real public roads plus synthetic fault injections; B. additionally use *properly licensed public non-personal* GPS examples; C. user-provided real drives stored privately under a separate future consent protocol. *Recommended: A, and B after provenance checks; not C by default.*

**17. What must happen when lane guidance or a roundabout exit is uncertain?** A. withhold specific claim and give safe direction-only guidance; B. choose most likely lane/exit; C. stop navigation entirely. *Recommended: A; count coverage loss as unresolved, never as passing guidance.*

**18. How strict is offline navigation?** A. entire UK offline operation on a phone; B. selected downloaded regions offline with online fallback; C. online first. *Recommended: B as an early engineering stage while keeping the longer-term UK-wide offline requirement visible.*

**19. Which dependent systems may the programme rebuild without another decision?** Options include OSM importer, routing graph, GPS matcher, map schema, map renderer, download/update system, instructions, voice, search and traffic. *Recommended: evaluate all; make reversible non-production changes only where evidence justifies them; ask on major architectural/licensing trade-offs.*

**20. How strictly must component ownership and distribution be controlled?** A. entirely independently authored engine; B. permissively licensed dependencies acceptable after audit; C. some reciprocal/share-alike compatible components if obligations explicitly accepted. *Recommended: A+B with explicit licence and ODbL data obligations; never assume an open-source label settles distribution rights.*

**21. At what point should we run DriveMate Android emulator tests?** A. after every small change; B. after each meaningful engine/dependency milestone and before promotion; C. only at end. *Recommended: B, with cheap component CI first and no overlapping costly builds.*

**22. What evidence is enough to promote or replace a DriveMate component?** A. works better on one sample; B. all applicable critical safety gates passed, broad held-out improvement without regressions, acceptable resources, licence review and rollback; C. one complete end-to-end emulator run. *Recommended: B; production still requires explicit authorization and mandatory app robot gates.*

## How to record decisions

Answer each with its number, option or wording. Mixed options are valid. The decision log should record: question number, answer, confirmation date, impacted benchmark schema/stage, and unresolved follow-up. **Until answered, don't turn recommendations into mandatory thresholds or represent a question as a settled owner requirement.** The minimum-count part of #1 is resolved (ten is a floor; twelve are proposed). The next substantive decision is **#4: which UK regions to test first**. No payable provider may be contacted simply because it is listed; Waze consumer content must not be programmatically collected without explicit legal permission.
