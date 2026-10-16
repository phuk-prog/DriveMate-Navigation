# DriveMate Navigation research: owner-confirmed testing workflow

Read live PR/head and active/queued jobs before experiments. Do not assume the
workspace or scheduled head is current. Work only in this existing research
repository unless separately authorized; production DriveMate stays unchanged.

## Standing owner decision (2026-10-16)

Use one named frozen test at a time. Test DMN and every actually available,
applicable reference on identical inputs and a genuinely comparable output
contract. Use available engines now; report the exact executed count rather than
waiting for ten or pretending the minimum-ten objective is met. Original families
and access/interface reasons stay in a separate audit; unsupported engines do
not appear as zero-quality entries in the active ranking.

After each baseline, show the user:
- The test name, exact issues/cases tested and independent/analytical/map-derived
  oracle scope, versions/configurations, map/input/oracle hashes and run/CI links.
- A comparison table ranked highest to lowest, with ties and the transparent
  score10*passed/frozen judged cases; show per-case pass/fail/unresolved reasons.
- Raw measured calculation times in milliseconds where available. Separate
  cold/warm/setup/process/network scopes, medians,p95,sample count and errors.
  Rank speed only on equivalent valid workload/hardware/measurement scope.
  Journey estimates/maneuver durations are not calculation latency. Missing
  measurements are UNAVAILABLE, never invented.
- Verified faults versus ambiguous evidence, and proposed improvements as a
  separate item. Never declare a generic winner from unmatched cohorts.

STOP AFTER THE BASELINE FOR THE OWNER'S REVIEW. Do not tune DMN, implement
proposed improvements, change acceptance or begin the next trial until the owner
instructs continuation of that step. This explicit review choice supersedes the
earlier automatic improve/retest cycle. Authorized harness setup recovery may
continue before a baseline executes, preserving every failed attempt and inputs.
After an authorized improvement, rerun the same frozen cases, full affected safety
regressions and additional separately labelled cases; show a separate retest table.

Ask before material uncertainty or a proposed permanent workflow/scope change.
Do not silently switch from the requested comparable baseline to adapter expansion
or a different component. A DMN-only safety regression can be useful, but it is
not a competitive baseline or an engine ranking. Report that limitation plainly.

## Evidence and scope

Use real licensed maps for the requested road comparisons; only GPS observations
are simulated. Keep analytical invented-map unit controls separately labelled.
Source-map agreement and competitor consensus are not independent road/legal/GNSS
truth. Freeze expectations before tuning, retain failures and do not force matches.
UK40-case replay17correct/0confidentlywrong/23withheld and seven lost matches
remain unresolved; no promotion without safely resolving the readiness gates.

The method covers the whole app: rendering, map data, GPS/navigation, search,
storage/settings, networking, UI/startup/accessibility, lifecycle/offline,
privacy/security, builds/updates and resources. Use relevant alternatives for
non-navigation components, not arbitrary navigation engines. Private app inventory
and source remain private/outside this public repository. Test discovery is not
execution. No new standalone app, merge, release, APK, spending, paid provider,
credentials/signing changes, personal GPS, proprietary data, unauthorized scraping,
Waze automation, unsupported access or messages to other people.

Keep heavy references sequential and bounded; no duplicate jobs. Use routine
reversible research branches/draft PRs and nonforced SHA-checked writes. Preserve
progress in docs/DMN_NUMBERED_TRIALS.md and per-trial evidence. Missing tools are
unavailable, never passed. A green research CI or score is not live-app readiness.
