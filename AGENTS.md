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

## Resource-efficient execution

Minimize Codex tokens, tool calls, CI minutes, downloads, storage and repeated
computation while preserving correctness and auditability:

- Read the smallest relevant files/ranges and summarize retained evidence instead
  of repeatedly loading raw logs or large JSON reports.
- Batch independent read-only checks. Reuse already verified hashes, versions,
  maps, cases and successful artifacts when the requested contract is unchanged.
- Check active/queued jobs once before launch. Never start duplicate workflows.
- Run focused local tests first. Run the full affected suite once before upload;
  do not repeat unchanged green checks without new code, evidence or a failure.
- Use one baseline execution per frozen cohort. Confirmation runs require a
  concrete reproducibility risk, material nondeterminism or owner request.
- Keep heavyweight engines sequential, use the smallest representative real-map
  extract and case cohort that can expose the tested behavior, and set time,
  memory, retry and output limits.
- Cache/reuse legally obtained public data and prepared engine state when hashes
  prove identity. Do not redownload or rebuild merely to create another run.
- Store compact summaries plus hashes and links. Retain raw artifacts only when
  needed to reproduce a failure or substantiate a result; avoid duplicating large
  evidence in repository files, PR text and chat.
- Keep commentary and final reports concise: show the requested ranking, exact
  failures, timing scope and decision. Link detailed evidence instead of copying it.
- Stop after the owner review gate. Do not spend resources on fixes, retests,
  adapter expansion or the next cohort before authorization.

Efficiency never permits fewer required engines within an applicable baseline,
discarding failures, weaker acceptance, invented evidence, mixed timing scopes or
skipping a check needed to support the claimed result. Record saved/reused work
and any unavailable measurement so lower usage remains auditable.
