# DriveMate Navigation research — instructions for every AI

## Read [REGISTER.md](REGISTER.md) first (owner, 2026-10-17)

Several AIs (Claude, Codex, others) work here. REGISTER.md is the one page to read
first: how to keep usage low, what is done (never repeat it), what is in progress
(leave it to its holder), what is pending (start at the top), and where to find
more, cheapest first. Open other files only if your task needs them. It is rebuilt
automatically on main from `work/` on every branch.

- Live view across branches: `python3 -m tools.work_status --fetch`; find a place: `where <topic>`.
- Claim: `start <ID> --title "..." --agent <you>`; record: `finish <ID> --summary --results --run
  --fingerprint "<test version>|<input hashes>|<revision>"`; queue follow-ups: `plan`.
- Commit and push `work/` and REGISTER.md with your work. Never personal data or private links
  (public repo). One AI per branch; merge, never force-push.

Most research work, and the full owner rules, are on branch
`codex/dmn-gps001-ranked-trial-20261015` (draft PR #4): read its AGENTS.md before
changing engine code or starting a test.
