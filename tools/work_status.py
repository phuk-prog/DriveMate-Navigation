"""Shared work register for every AI (Claude, Codex, others) working on this repository.

One small JSON file per piece of work in work/items/<ID>.json says what it is, its
state (next / in_progress / done / blocked), which AI and branch hold it, what was
found, where the results are and a fingerprint of the exact inputs it ran on.
`show` reads those files from this checkout AND every fetched remote branch, so an
AI on its own branch still sees what the others are doing.

    python3 -m tools.work_status                      # what is done, running, next
    python3 -m tools.work_status --fetch              # same, after git fetch
    python3 -m tools.work_status seen FINGERPRINT     # exit 1 if already done
    python3 -m tools.work_status start ID --title T --agent NAME
    python3 -m tools.work_status finish ID --summary S [--results F] [--run URL] [--fingerprint X]
    python3 -m tools.work_status plan ID --title T [--why W]
    python3 -m tools.work_status block ID --summary S

`start` refuses work another AI holds on another branch (updated in the last
STALE_HOURS) and work already done with the same fingerprint, so nothing is
repeated without a reason (use --reason to record a deliberate rerun).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "work" / "items"
STATES = ("in_progress", "blocked", "next", "done")
STALE_HOURS = 24


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    return done.stdout if done.returncode == 0 else ""


def _branch() -> str:
    return _git("rev-parse", "--abbrev-ref", "HEAD").strip() or "unknown"


def _local() -> dict[str, dict]:
    out = {}
    for path in sorted(ITEMS.glob("*.json")):
        item = json.loads(path.read_text())
        out[item["id"]] = {**item, "_seen_on": "this checkout"}
    return out


def _remote() -> list[dict]:
    found = []
    for ref in _git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin").split():
        if ref.endswith("/HEAD"):
            continue
        for name in _git("ls-tree", "--name-only", f"{ref}:work/items").split():
            if name.endswith(".json"):
                try:
                    found.append({**json.loads(_git("show", f"{ref}:work/items/{name}")), "_seen_on": ref})
                except json.JSONDecodeError:
                    continue
    return found


def collect() -> dict[str, dict]:
    """Newest version of every item across this checkout and all remote branches."""
    items = _local()
    for item in _remote():
        mine = items.get(item["id"])
        if mine is None or item.get("updated", "") > mine.get("updated", ""):
            items[item["id"]] = item
    return items


def _age_hours(item: dict) -> float:
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(item["updated"])).total_seconds() / 3600
    except (KeyError, ValueError):
        return float("inf")


def show(items: dict[str, dict]) -> str:
    lines = []
    for state in STATES:
        group = sorted((i for i in items.values() if i.get("state") == state),
                       key=lambda i: i.get("updated", ""), reverse=True)
        if not group:
            continue
        lines.append(state.upper().replace("_", " "))
        for i in group[:12] if state == "done" else group:
            who = f" [{i.get('agent', '?')} on {i.get('branch', '?')}, {i.get('updated', '?')[:16]}]"
            stale = " STALE: free to take over" if state == "in_progress" and _age_hours(i) > STALE_HOURS else ""
            lines.append(f"- {i['id']}: {i.get('title', '')}{who}{stale}")
            for key in ("summary", "why", "results"):
                if i.get(key):
                    lines.append(f"    {key}: {i[key]}")
    return "\n".join(lines) or "No work items yet."


def _write(item: dict) -> Path:
    ITEMS.mkdir(parents=True, exist_ok=True)
    path = ITEMS / f"{item['id']}.json"
    clean = {k: v for k, v in item.items() if not k.startswith("_")}
    path.write_text(json.dumps(clean, indent=1, sort_keys=True) + "\n")
    return path


def seen(items: dict[str, dict], fingerprint: str) -> dict | None:
    return next((i for i in items.values() if i.get("state") == "done" and fingerprint in i.get("fingerprints", [])),
                None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fetch", action="store_true", help="git fetch origin first")
    sub = parser.add_subparsers(dest="cmd")
    p = sub.add_parser("seen")
    p.add_argument("fingerprint")
    for name in ("start", "plan", "finish", "block"):
        p = sub.add_parser(name)
        p.add_argument("id")
        p.add_argument("--title")
        p.add_argument("--agent", default="unknown AI")
        p.add_argument("--summary")
        p.add_argument("--why")
        p.add_argument("--results")
        p.add_argument("--run", action="append", default=[])
        p.add_argument("--fingerprint", action="append", default=[])
        p.add_argument("--reason", help="why repeating work that is already done or held")
    args = parser.parse_args(argv)
    if args.fetch:
        subprocess.run(["git", "fetch", "-q", "origin"], cwd=ROOT)
    items = collect()
    if args.cmd in (None, "show"):
        print(show(items))
        return 0
    if args.cmd == "seen":
        hit = seen(items, args.fingerprint)
        print(f"ALREADY DONE in {hit['id']} ({hit.get('results') or hit.get('summary', '')})" if hit else "not done yet")
        return 1 if hit else 0
    old = items.get(args.id, {})
    item = {k: v for k, v in old.items() if not k.startswith("_")} or {"id": args.id, "created": _now()}
    branch = _branch()
    if args.cmd == "start":
        holder = old.get("state") == "in_progress" and old.get("branch") != branch and _age_hours(old) <= STALE_HOURS
        repeat = old.get("state") == "done" or any(seen(items, f) for f in args.fingerprint)
        if (holder or repeat) and not args.reason:
            why = (f"held by {old.get('agent')} on {old.get('branch')}" if holder else "already done")
            print(f"REFUSED: {args.id} is {why}. Pick other work, or pass --reason to record a deliberate rerun.")
            return 2
    state = {"start": "in_progress", "plan": "next", "finish": "done", "block": "blocked"}[args.cmd]
    item.update(state=state, updated=_now(), branch=branch,
                agent=args.agent if args.agent != "unknown AI" else item.get("agent", args.agent))
    for key in ("title", "summary", "why", "results", "reason"):
        if getattr(args, key):
            item[key] = getattr(args, key)
    item["runs"] = sorted(set(item.get("runs", [])) | set(args.run))
    item["fingerprints"] = sorted(set(item.get("fingerprints", [])) | set(args.fingerprint))
    item.setdefault("history", []).append(f"{item['updated']} {state} by {item['agent']} on {branch}")
    print(f"{args.id} -> {state}: {_write(item).name} (commit and push it so other AIs see it)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
